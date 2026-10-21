# Claude Desktop for Fedora

This project repackages Anthropic's official Claude Desktop Linux `.deb` as an
RPM for Fedora. It does not modify the application, rebuild Electron, or use
files from the Windows release.

Anthropic currently supports Ubuntu 22.04+ and Debian 12+. Fedora and RHEL are
not officially supported yet:
<https://code.claude.com/docs/en/desktop-linux>

## Build

Install the small set of packaging tools:

```bash
sudo dnf install rpm-build curl binutils tar
```

Build the latest package published in Anthropic's APT repository:

```bash
./build-fedora.sh
```

Or build a package already downloaded locally:

```bash
./build-fedora.sh --deb ~/Downloads/claude-desktop_3.1623.0_amd64.deb
```

The RPM is written to `dist/`. Building does not require root and does not
change the host system.

## Install

```bash
sudo dnf install ./dist/claude-desktop-*.rpm
```

Launch `Claude` from the application menu or run `claude-desktop`.

Remove it with:

```bash
sudo dnf remove claude-desktop
```

## What the package does

- Copies the official application payload to the same paths used upstream.
- Translates Debian package metadata into RPM metadata.
- Lets RPM derive native shared-library dependencies from the shipped ELF
  binaries.
- Declares Fedora packages needed for portals, credential storage, tray
  integration, and the optional Cowork VM.
- Preserves Chromium's upstream setuid sandbox fallback.
- Installs the GNOME Shell search provider, the `.mcpb`/`.dxt`/`.skill` MIME
  types and, when the release ships it, the `ccd` launcher as package-owned
  files instead of copying them from a post-install script as upstream does.
- Omits Debian-only APT registration, unattended-upgrades, lintian, and
  AppArmor integration.

Fedora already provides the Cowork components at paths recognized by Claude:

- `/usr/bin/qemu-system-x86_64`
- `/usr/libexec/virtiofsd`
- `/usr/share/OVMF/OVMF_CODE.fd`

No Fedora-specific binary patches or compatibility symlinks are currently
needed.

## Updating

`./build-fedora.sh` reads Anthropic's current APT package index, downloads the
newest package for the host architecture, and verifies its SHA-256 checksum.
Run it again whenever Anthropic publishes a new release.

Claude Desktop does not self-update on Linux. An RPM installed from this
project must be rebuilt and installed again to update it.

## Architectures

The packaging supports `x86_64` and `aarch64`, matching Anthropic's published
Linux architectures. Each RPM must be built on the matching host architecture.

## Licensing

The packaging files in this repository are MIT licensed. Claude Desktop is
proprietary software distributed by Anthropic and is not covered by this
repository's license.
