%global debug_package %{nil}
%global __strip /bin/true

%{!?claude_version:%global claude_version 1.24012.9}
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
Requires:       xdg-utils

# These match the weak dependencies in Anthropic's Debian package. DNF installs
# weak dependencies by default, while minimal installations can omit them.
Recommends:     gnome-keyring
Recommends:     libayatana-appindicator-gtk3
Recommends:     virtiofsd
Recommends:     xdg-desktop-portal-gtk

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

%files
%defattr(-,root,root,-)
%{_bindir}/claude-desktop
/usr/lib/claude-desktop/
%{_datadir}/applications/com.anthropic.Claude.desktop
%{_datadir}/icons/hicolor/*/apps/claude-desktop.png
%doc %{_datadir}/doc/claude-desktop/copyright

%changelog
* Tue Jul 28 2026 claude-desktop-fedora-ng contributors - 1.24012.9-1
- Repackage Anthropic's official Linux application for Fedora.
