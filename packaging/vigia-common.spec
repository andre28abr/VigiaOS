# RPM spec para vigia-common (lib interna compartilhada)
# Buildada via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)

%global pkg_name vigia-common
%global mod_name vigia_common

Name:           %{pkg_name}
Version:        0.2.3
Release:        1%{?dist}
Summary:        Helpers compartilhados entre as ferramentas do VigiaOS
License:        Apache-2.0
URL:            https://github.com/andre28abr/VigiaOS
Source0:        %{url}/archive/v%{version}.tar.gz#/VigiaOS-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-pip

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita

%description
Vigia Common e' a biblioteca interna do VigiaOS. Centraliza
helpers de UI (make_clamp, show_error/info, file picker, copy
to clipboard), o conversor markdown → Pango, e helpers de badges
para a sub-bar de WRAPPED_PACKAGES.

Sem GUI, sem entry point — biblioteca-base que as outras tools
da suite importam. Instale apenas se for instalar outras tools
Vigia (sao deps deste pacote).

%prep
%autosetup -n VigiaOS-%{version}

%build
cd tools/vigia-common
%{__python3} -m pip wheel --no-deps --wheel-dir=../../dist .

%install
cd tools/vigia-common
%{__python3} -m pip install --root=%{buildroot} --prefix=/usr \
    --no-deps --no-index --find-links=../../dist %{pkg_name}

%files
%license LICENSE
%doc tools/vigia-common/README.md
%{python3_sitelib}/%{mod_name}/
%{python3_sitelib}/%{mod_name}-*.dist-info/

%changelog
* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.3-1
- Novo: vigia_common.shell — casca de produto reutilizavel (rail + sidebar +
  conteudo) usada pelos esqueletos VigiaRed e VigiaBlue.

* Sun May 31 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.2-1
- Alinha versao do spec com a tool (auditoria 100%): 0.2.1 -> 0.2.2.

* Sun May 31 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.1-1
- Alinha a versao do spec com a tool (0.1.0 -> 0.2.1).

* Mon May 26 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.0-1
- Initial release: helpers compartilhados extraidos de 16 tools
