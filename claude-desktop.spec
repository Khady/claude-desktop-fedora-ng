%global debug_package %{nil}
%global __strip /bin/true
# Keep upstream shebangs byte-for-byte; /bin/sh is valid on Fedora.
%global __brp_mangle_shebangs %{nil}

%{!?claude_version:%global claude_version 3.1623.0}
%{!?deb_file:%global deb_file claude-desktop_%{claude_version}_amd64.deb}

Name:           claude-desktop
Version:        %{claude_version}
Release:        1%{?dist}
Summary:        Desktop application for Claude.ai
License:        LicenseRef-Proprietary
URL:            https://claude.ai
Source0:        %{deb_file}
ExclusiveArch:  x86_64 aarch64

# Commands and D-Bus services are not discovered by RPM's ELF dependency
# generator. The remaining native-library dependencies are generated from the
# bundled ELF files automatically.
Requires:       socat
Requires:       xdg-desktop-portal
Requires:       (xdg-desktop-portal-gtk or xdg-desktop-portal-gnome or xdg-desktop-portal-kde)
Requires:       xdg-utils

# These match the weak dependencies in Anthropic's Debian package. DNF installs
# weak dependencies by default, while minimal installations can omit them.
Recommends:     bubblewrap
Recommends:     gnome-keyring
Recommends:     libayatana-appindicator-gtk3
Recommends:     openssh-clients
Recommends:     virtiofsd

# The GNOME Shell search provider is a GJS script started over D-Bus.
Recommends:     gjs

%ifarch x86_64
Recommends:     edk2-ovmf
Recommends:     qemu-system-x86-core
%endif

%ifarch aarch64
Recommends:     edk2-aarch64
Recommends:     qemu-system-aarch64-core
%endif

%description
Claude Desktop repackaged from Anthropic's official Debian package for Fedora.
The application payload is not modified.

%prep

%build

%install
mkdir -p %{buildroot}
ar p %{SOURCE0} data.tar.xz | tar -xJf - -C %{buildroot}

# Debian lintian metadata and maintainer scripts are not part of data.tar.xz's
# application runtime. The lintian override has no consumer on Fedora.
rm -rf %{buildroot}%{_datadir}/lintian

# Chromium validates this exact owner/mode when it needs its setuid sandbox.
# Fedora normally uses unprivileged user namespaces, but retaining Anthropic's
# fallback matches the upstream package.
chmod 4755 %{buildroot}/usr/lib/claude-desktop/chrome-sandbox

# Upstream's postinst copies these desktop integration files out of the
# payload at install time. Ship them as package-owned files instead; Fedora's
# shared-mime-info file trigger refreshes the MIME database. Older releases
# lack some of them, so the file list is built from what this payload ships.
resources=%{buildroot}/usr/lib/claude-desktop/resources
: > integration.files

if [ -d "$resources/gnome-search-provider" ]; then
    install -Dpm 0644 \
        "$resources/gnome-search-provider/com.anthropic.Claude.search-provider.ini" \
        %{buildroot}%{_datadir}/gnome-shell/search-providers/com.anthropic.Claude.search-provider.ini
    install -Dpm 0644 \
        "$resources/gnome-search-provider/com.anthropic.Claude.SearchProvider.service" \
        %{buildroot}%{_datadir}/dbus-1/services/com.anthropic.Claude.SearchProvider.service
    echo %{_datadir}/gnome-shell/search-providers/com.anthropic.Claude.search-provider.ini >> integration.files
    echo %{_datadir}/dbus-1/services/com.anthropic.Claude.SearchProvider.service >> integration.files
fi

if [ -f "$resources/linux-mime/com.anthropic.Claude.xml" ]; then
    install -Dpm 0644 "$resources/linux-mime/com.anthropic.Claude.xml" \
        %{buildroot}%{_datadir}/mime/packages/com.anthropic.Claude.xml
    echo %{_datadir}/mime/packages/com.anthropic.Claude.xml >> integration.files
fi

if [ -x "$resources/bin/ccd" ]; then
    ln -s ../lib/claude-desktop/resources/bin/ccd %{buildroot}%{_bindir}/ccd
    echo %{_bindir}/ccd >> integration.files
fi

%files -f integration.files
%defattr(-,root,root,-)
%{_bindir}/claude-desktop
/usr/lib/claude-desktop/
%{_datadir}/applications/com.anthropic.Claude.desktop
%{_datadir}/icons/hicolor/*/apps/claude-desktop.png
%doc %{_datadir}/doc/claude-desktop/copyright

%changelog
* Wed Oct 21 2026 claude-desktop-fedora-ng contributors - 3.1623.0-1
- Install the GNOME search provider, MIME types and ccd launcher that
  upstream's postinst sets up.
- Recommend bubblewrap, openssh-clients and gjs, matching upstream.
- Require any GTK, GNOME or KDE portal backend, matching upstream.
- Stop rewriting upstream shebangs.

* Tue Jul 28 2026 claude-desktop-fedora-ng contributors - 1.24012.9-1
- Repackage Anthropic's official Linux application for Fedora.
