# RPM spec para vigia-hub (VigiaOS)
# Buildado via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)

%global pkg_name vigia-hub
%global mod_name vigia_hub

Name:           %{pkg_name}
Version:        0.8.1
Release:        1%{?dist}
Summary:        Launcher mestre do VigiaOS (3 paineis, embedded mode)
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

%description
Vigia Hub e' o launcher mestre do VigiaOS. Apresenta 18+ ferramentas em layout master-detail-content (3 paineis): nav lateral fina com icones + sidebar categorizada (Monitoramento, Privacidade, Defesa, Relatorios) + content embedded.

Tools sao embarcadas diretamente no painel direito (single-window) quando disponiveis; fallback para subprocess se nao embeddable.

Faz parte do VigiaOS — toolkit de seguranca para Fedora Atomic
(Silverblue, Kinoite, Bluefin, Bazzite, Aurora).

Comando: vigia-hub

%prep
%autosetup -n VigiaOS-%{version}

%build
cd tools/vigia-hub
%{__python3} -m pip wheel --no-deps --wheel-dir=../../dist .

%install
cd tools/vigia-hub
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
%doc tools/vigia-hub/README.md
%{_bindir}/vigia-hub
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
* Tue Jun 02 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.8.1-1
- Aviso de update sai do icone do Instalador e vira um sininho no rodape do
  rail (bolinha vermelha + popover listando as notificacoes). Mesmo padrao no
  Blue/Red via shell.

* Tue Jun 02 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.8.0-1
- Checagem de atualizacoes em segundo plano ao iniciar: badge discreto no icone
  do Instalador quando ha update (sistema ou suite). Toggle em Config > Aplicacao
  ('Verificar atualizacoes ao iniciar', default ligado). Read-only, sem root.

* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.7.6-1
- Icone limpo (olho, sem wordmark gravado) + reposicionamento: VigiaHub = produto, VigiaOS = ecossistema.

* Mon Jun 01 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.7.5-1
- Aba Sobre (Config): cartao do Autor (bio + links LinkedIn/GitHub) +
  resumo do Vigia Hub. Links abrem no navegador via launch_default_for_uri.

* Sun May 31 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.7.4-1
- Alinha a versao do spec com a tool (0.5.0 -> 0.7.4).

* Mon May 26 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.5.0-1
- Initial release in COPR
