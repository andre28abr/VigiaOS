# RPM spec para vigia-antivirus (VigiaOS)
# Buildado via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)

%global pkg_name vigia-antivirus
%global mod_name vigia_antivirus

Name:           %{pkg_name}
Version:        0.1.4
Release:        1%{?dist}
Summary:        Antivirus on-demand via ClamAV (substitui clamtk)
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
Requires:       clamav
Requires:       clamav-update

%description
Antivirus on-demand para Linux desktop usando engine ClamAV. Streaming de findings, update via freshclam, banner de estado, reports em ~/.local/share/vigia-antivirus/ mode 0600.

Faz parte do VigiaOS — toolkit de seguranca para Fedora Atomic
(Silverblue, Kinoite, Bluefin, Bazzite, Aurora).

Comando: vigia-antivirus

%prep
%autosetup -n VigiaOS-%{version}

%build
cd tools/antivirus
%{__python3} -m pip wheel --no-deps --wheel-dir=../../dist .

%install
cd tools/antivirus
%{__python3} -m pip install --root=%{buildroot} --prefix=/usr \
    --no-deps --no-index --find-links=../../dist %{pkg_name}

# Desktop entry + icon
install -Dpm 0644 data/br.com.vigia.*.desktop \
    %{buildroot}%{_datadir}/applications/
install -Dpm 0644 data/br.com.vigia.*.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/

desktop-file-validate %{buildroot}%{_datadir}/applications/br.com.vigia.*.desktop

%files
%license LICENSE
%doc tools/antivirus/README.md
%{_bindir}/vigia-antivirus
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
* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.4-1
- Fix: idade da base agora vem do mtime dos arquivos .cvd/.cld (era do
  strptime locale-dependent no `clamscan --version`, que quebrava em pt-BR
  e mostrava 'idade desconhecida' mesmo com a base atualizada).

* Sun May 31 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.3-1
- Alinha versao do spec com a tool (auditoria 100%): 0.1.1 -> 0.1.3.

* Mon May 26 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.1-1
- Initial release in COPR
