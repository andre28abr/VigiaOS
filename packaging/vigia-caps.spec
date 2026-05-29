# RPM spec para vigia-caps (VigiaOS)
# Buildado via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)
#
# NOTA: o pacote se chama vigia-caps (igual ao [project].name do pyproject e
# ao binario), NAO vigia-capabilities. O diretorio-fonte e' capabilities-inspector.

%global pkg_name vigia-caps
%global mod_name vigia_caps

Name:           %{pkg_name}
Version:        0.1.0
Release:        1%{?dist}
Summary:        Auditoria de Linux capabilities via getcap
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
Requires:       libcap

%description
Audita binarios com Linux capabilities (alternativa granular ao SUID). Catalogo de 41 capabilities pt-BR (11 ALTO + 17 MEDIO + 13 BAIXO). Read-only em v0.1; modificacao via UI em v0.2.

Faz parte do VigiaOS — toolkit de seguranca para Fedora Atomic
(Silverblue, Kinoite, Bluefin, Bazzite, Aurora).

Comando: vigia-caps

%prep
%autosetup -n VigiaOS-%{version}

%build
cd tools/capabilities-inspector
%{__python3} -m pip wheel --no-deps --wheel-dir=../../dist .

%install
cd tools/capabilities-inspector
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
%doc tools/capabilities-inspector/README.md
%{_bindir}/vigia-caps
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
