# RPM spec para vigia-deployments (VigiaOS)
# Buildado via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)
#
# NOTA: o pacote/binario se chama vigia-deployments (= [project].name e script
# do pyproject). O diretorio-fonte e' deployments-manager; o modulo Python e'
# vigia_deployments (dai o dist-info vigia_deployments-*.dist-info, underscore).

%global pkg_name vigia-deployments
%global mod_name vigia_deployments

Name:           %{pkg_name}
Version:        0.1.2
Release:        1%{?dist}
Summary:        Gerenciador de deployments rpm-ostree (boot snapshots)
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
Requires:       rpm-ostree

%description
GUI GTK4 pra gerenciar os deployments do rpm-ostree — os snapshots que aparecem
no menu do GRUB ao bootar. Rollback, pin/unpin, labels + notas multilinha
(LGPD/audit), cleanup integrado (rpm-ostree cleanup -p -r -m) e alerta de /boot
cheio. Operacoes privilegiadas via pkexec.

Faz parte do VigiaOS — toolkit de seguranca para Fedora Atomic
(Silverblue, Kinoite, Bluefin, Bazzite, Aurora).

Comando: vigia-deployments

%prep
%autosetup -n VigiaOS-%{version}

%build
cd tools/deployments-manager
%{__python3} -m pip wheel --no-deps --wheel-dir=../../dist .

%install
cd tools/deployments-manager
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
%doc tools/deployments-manager/README.md
%{_bindir}/vigia-deployments
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
* Sun May 31 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.2-1
- Alinha versao do spec com a tool (auditoria 100%): 0.1.1 -> 0.1.2.

* Thu May 29 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.1-1
- Initial release in COPR
