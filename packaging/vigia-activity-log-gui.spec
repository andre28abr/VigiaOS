# RPM spec para vigia-activity-log-gui (VigiaOS)
# Buildado via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)
#
# NOTA: o pacote RPM se chama vigia-activity-log-gui (pareia com o core Rust
# vigia-activity-log), mas o [project].name / binario do pyproject e' vigia-log-gui
# (modulo vigia_log_gui). Por isso proj_name != pkg_name: o pip install usa
# proj_name e o dist-info usa mod_name (vigia_log_gui-*.dist-info).

%global pkg_name vigia-activity-log-gui
%global proj_name vigia-log-gui
%global mod_name vigia_log_gui

Name:           %{pkg_name}
Version:        0.1.0
Release:        1%{?dist}
Summary:        Frontend GTK4 do Vigia Activity Log (parser Rust)
License:        Apache-2.0
URL:            https://github.com/andre28abr/VigiaOS
Source0:        %{url}/archive/v%{version}.tar.gz#/VigiaOS-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-pip
BuildRequires:  desktop-file-utils

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       hicolor-icon-theme
Requires:       vigia-common
Requires:       vigia-activity-log

%description
GUI Python do parser Rust vigia-log. Consolida audit.log, systemd journal e fail2ban.log numa unica linha do tempo, detecta correlations cross-source, classifica por severidade.

Faz parte do VigiaOS — toolkit de seguranca para Fedora Atomic
(Silverblue, Kinoite, Bluefin, Bazzite, Aurora).

Comando: vigia-log-gui

%prep
%autosetup -n VigiaOS-%{version}

%build
cd tools/activity-log-gui
%{__python3} -m pip wheel --no-deps --wheel-dir=../../dist .

%install
cd tools/activity-log-gui
%{__python3} -m pip install --root=%{buildroot} --prefix=/usr \
    --no-deps --no-index --find-links=../../dist %{proj_name}

# Desktop entry + icon
install -Dpm 0644 data/br.com.vigia.*.desktop \
    %{buildroot}%{_datadir}/applications/
install -Dpm 0644 data/br.com.vigia.*.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/

desktop-file-validate %{buildroot}%{_datadir}/applications/br.com.vigia.*.desktop

%files
%license LICENSE
%doc tools/activity-log-gui/README.md
%{_bindir}/vigia-log-gui
%{python3_sitelib}/%{mod_name}/
%{python3_sitelib}/%{mod_name}-*.dist-info/
%{_datadir}/applications/br.com.vigia.*.desktop
%{_datadir}/icons/hicolor/scalable/apps/br.com.vigia.*.svg

%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
/usr/bin/update-desktop-database &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    /usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :
fi
/usr/bin/update-desktop-database &>/dev/null || :

%posttrans
/usr/bin/gtk-update-icon-cache %{_datadir}/icons/hicolor &>/dev/null || :

%changelog
* Mon May 26 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.0-1
- Initial release in COPR
