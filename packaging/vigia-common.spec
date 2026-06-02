# RPM spec para vigia-common (lib interna compartilhada)
# Buildada via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)

%global pkg_name vigia-common
%global mod_name vigia_common

Name:           %{pkg_name}
Version:        0.2.15
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
* Tue Jun 02 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.15-1
- shell: instalador dos produtos no mesmo padrao visual do Catalogo do Hub —
  badge de status como prefixo (PRONTO/FALTA), sem o icone colorido do modulo.

* Tue Jun 02 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.14-1
- shell: pagina 'Sobre' dos produtos (Blue/Red) com a bio completa do autor
  (paridade com o Vigia Hub) — descricao longa + linha nome/avatar.

* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.8-1
- shell: janela dos produtos (Blue/Red) no mesmo tamanho do Hub (1340x820).

* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.7-1
- shell: campo Module.impl (carrega build_content() real do modulo) e fix
  da navegacao da sidebar (row-selected em vez de row-activated).

* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.5-1
- shell: branding do produto no rail menor (caption-heading) + header
  'Ferramentas' na coluna do meio — alinhando com o Vigia Hub.

* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.4-1
- shell: carrega icone colorido do modulo via arquivo (padrao Hub) com
  fallback pro icon-name do tema.

* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.3-1
- Novo: vigia_common.shell — casca de produto reutilizavel (rail + sidebar +
  conteudo) usada pelos esqueletos VigiaRed e VigiaBlue.

* Sun May 31 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.2-1
- Alinha versao do spec com a tool (auditoria 100%): 0.2.1 -> 0.2.2.

* Sun May 31 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.1-1
- Alinha a versao do spec com a tool (0.1.0 -> 0.2.1).

* Mon May 26 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.0-1
- Initial release: helpers compartilhados extraidos de 16 tools
