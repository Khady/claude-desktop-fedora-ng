#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly PACKAGE_BASE_URL="https://downloads.claude.ai/claude-desktop/apt/stable"

deb_path=""
output_dir="$SCRIPT_DIR/dist"
keep_build=false

usage() {
    cat <<'EOF'
Usage: ./build-fedora.sh [OPTIONS]

Build an RPM from Anthropic's official Claude Desktop Debian package.

Options:
  --deb PATH       Use an existing .deb instead of downloading the latest one
  --output DIR     Write the RPM to DIR (default: ./dist)
  --keep-build     Keep the rpmbuild working directory
  -h, --help       Show this help

The build itself does not require root. Install the result with:
  sudo dnf install ./dist/claude-desktop-*.rpm
EOF
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

while (($#)); do
    case "$1" in
        --deb)
            (($# >= 2)) || die "--deb requires a path"
            deb_path="$2"
            shift 2
            ;;
        --output)
            (($# >= 2)) || die "--output requires a directory"
            output_dir="$2"
            shift 2
            ;;
        --keep-build)
            keep_build=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1"
            ;;
    esac
done

for command_name in ar awk cp curl mkdir mktemp readlink rpm rpmbuild sha256sum sort tar; do
    command -v "$command_name" >/dev/null ||
        die "missing build command '$command_name'"
done

case "$(uname -m)" in
    x86_64)
        deb_arch="amd64"
        rpm_arch="x86_64"
        ;;
    aarch64)
        deb_arch="arm64"
        rpm_arch="aarch64"
        ;;
    *)
        die "unsupported architecture: $(uname -m)"
        ;;
esac

work_dir="$(mktemp -d "$SCRIPT_DIR/build.XXXXXXXX")"
cleanup() {
    if [[ "$keep_build" == true ]]; then
        printf 'Build directory retained at %s\n' "$work_dir"
    else
        rm -rf -- "$work_dir"
    fi
}
trap cleanup EXIT

top_dir="$work_dir/rpmbuild"
mkdir -p "$top_dir"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

if [[ -z "$deb_path" ]]; then
    packages_url="$PACKAGE_BASE_URL/dists/stable/main/binary-$deb_arch/Packages"
    packages_file="$work_dir/Packages"
    printf 'Reading Anthropic package index...\n'
    curl --fail --location --silent --show-error \
        "$packages_url" --output "$packages_file"

    package_record="$(
        awk '
            BEGIN { RS = ""; FS = "\n" }
            {
                package = version = filename = checksum = ""
                for (i = 1; i <= NF; i++) {
                    if ($i ~ /^Package: /)  package = substr($i, 10)
                    if ($i ~ /^Version: /)  version = substr($i, 10)
                    if ($i ~ /^Filename: /) filename = substr($i, 11)
                    if ($i ~ /^SHA256: /)   checksum = substr($i, 9)
                }
                if (package == "claude-desktop" && version && filename && checksum)
                    print version "\t" filename "\t" checksum
            }
        ' "$packages_file" | sort -t $'\t' -k1,1V | tail -n 1
    )"
    [[ -n "$package_record" ]] ||
        die "no claude-desktop package found in $packages_url"

    IFS=$'\t' read -r index_version index_filename index_checksum \
        <<<"$package_record"
    deb_path="$work_dir/$(basename -- "$index_filename")"
    printf 'Downloading Claude Desktop %s (%s)...\n' "$index_version" "$deb_arch"
    curl --fail --location --show-error \
        "$PACKAGE_BASE_URL/$index_filename" --output "$deb_path"
    printf '%s  %s\n' "$index_checksum" "$deb_path" | sha256sum --check --status ||
        die "download checksum does not match Anthropic's package index"
else
    deb_path="$(readlink -f -- "$deb_path")"
    [[ -f "$deb_path" ]] || die "Debian package not found: $deb_path"
fi

deb_member="$(ar t "$deb_path" | awk '/^control\.tar\./ { print; exit }')"
[[ -n "$deb_member" ]] || die "not a Debian package: $deb_path"
case "$deb_member" in
    *.xz)
        control="$(ar p "$deb_path" "$deb_member" | tar -xJOf - ./control)"
        ;;
    *.gz)
        control="$(ar p "$deb_path" "$deb_member" | tar -xzOf - ./control)"
        ;;
    *.bz2)
        control="$(ar p "$deb_path" "$deb_member" | tar -xjOf - ./control)"
        ;;
    *.zst)
        control="$(ar p "$deb_path" "$deb_member" | tar --zstd -xOf - ./control)"
        ;;
    *)
        die "unsupported Debian control archive compression: $deb_member"
        ;;
esac

package_name="$(awk -F ': *' '$1 == "Package" { print $2; exit }' <<<"$control")"
version="$(awk -F ': *' '$1 == "Version" { print $2; exit }' <<<"$control")"
package_arch="$(awk -F ': *' '$1 == "Architecture" { print $2; exit }' <<<"$control")"

[[ "$package_name" == "claude-desktop" ]] ||
    die "expected package claude-desktop, found '$package_name'"
[[ "$package_arch" == "$deb_arch" ]] ||
    die "package architecture '$package_arch' does not match host '$deb_arch'"
[[ "$version" =~ ^[0-9][0-9A-Za-z._+~]*$ ]] ||
    die "unsupported package version: $version"

deb_file="$(basename -- "$deb_path")"
cp --reflink=auto -- "$deb_path" "$top_dir/SOURCES/$deb_file"
cp -- "$SCRIPT_DIR/claude-desktop.spec" "$top_dir/SPECS/"

printf 'Building claude-desktop %s for %s...\n' "$version" "$rpm_arch"
rpmbuild -bb \
    --define "_topdir $top_dir" \
    --define "claude_version $version" \
    --define "deb_file $deb_file" \
    "$top_dir/SPECS/claude-desktop.spec"

rpm_path="$(
    find "$top_dir/RPMS/$rpm_arch" -maxdepth 1 -type f \
        -name "claude-desktop-$version-*.rpm" -print -quit
)"
[[ -n "$rpm_path" ]] || die "rpmbuild completed but no RPM was produced"

mkdir -p -- "$output_dir"
final_path="$output_dir/$(basename -- "$rpm_path")"
cp -- "$rpm_path" "$final_path"

rpm -K "$final_path"
rpm -qpl "$final_path" |
    awk '$0 == "/usr/bin/claude-desktop" { found = 1 }
         END { exit !found }' ||
    die "RPM does not contain the command-line launcher"
rpm -qplv "$final_path" |
    awk '$NF == "/usr/lib/claude-desktop/chrome-sandbox" && $1 == "-rwsr-xr-x" { found = 1 }
         END { exit !found }' ||
    die "RPM does not preserve the Chromium sandbox mode"

printf '\nBuilt successfully:\n%s\n' "$final_path"
printf '\nInstall with:\nsudo dnf install %q\n' "$final_path"
