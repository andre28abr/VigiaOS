# RPM spec para vigia-suite (metapackage)
# Instala TODAS as ferramentas do VigiaOS numa unica operacao.
# Sem code/files proprios — apenas Requires.

%global pkg_name vigia-suite

Name:           %{pkg_name}
Version:        0.2.0
Release:        1%{?dist}
Summary:        Suite completa de seguranca para Fedora Workstation (metapackage)
License:        Apache-2.0
URL:            https://github.com/andre28abr/VigiaOS
Source0:        %{url}/archive/v%{version}.tar.gz#/VigiaOS-%{version}.tar.gz

BuildArch:      noarch

# Lib compartilhada
Requires:       vigia-common >= 0.1.0

# Launcher + dashboard (entradas principais)
Requires:       vigia-hub >= 0.5.0
Requires:       vigia-dashboard >= 0.2.0

# Monitoramento
Requires:       vigia-activity-log >= 0.7.0
Requires:       vigia-activity-log-gui >= 0.1.0
Requires:       vigia-netmon >= 0.1.0

# Privacidade
Requires:       vigia-privacy >= 0.3.0
Requires:       vigia-dns >= 0.1.0

# Defesa & hardening
Requires:       vigia-selinux >= 0.2.0
Requires:       vigia-firewall >= 0.1.0
Requires:       vigia-hardening >= 0.1.2
Requires:       vigia-integrity >= 0.1.3
Requires:       vigia-caps >= 0.1.0
Requires:       vigia-antivirus >= 0.1.1
Requires:       vigia-rootkit >= 0.2.0

# Relatorios
Requires:       vigia-reports >= 0.1.1

# Catalogo (entidade especial — instalavel mas opcional)
Requires:       vigia-installer >= 0.1.0

%description
VigiaOS — metapackage que instala o Vigia Hub + as 13 ferramentas de
seguranca/monitoramento + o Tool Installer (15 apps no total) numa
unica operacao.

Apos instalacao, abra "Vigia Hub" no menu GNOME para acessar todas
as ferramentas embarcadas em uma unica janela.

Categorias:
- Monitoramento: Dashboard, Activity Log, Network Monitor
- Privacidade:   Privacy Controls, DNS Manager
- Defesa:        SELinux, Firewall, Hardening Checks, File Integrity,
                 Capabilities Inspector, Rootkit Scanner, Antivirus
- Relatorios:    Reports (PDF/HTML LGPD)
- Catalogo:      Tool Installer (16 pacotes curados + extensoes)

Compatibilidade: Fedora Workstation 40+.

%prep
# Metapackage — nada para preparar.

%build
# Metapackage — nada para buildar.

%install
# Metapackage — nada para instalar.

%files
# Metapackage — sem arquivos.

%changelog
* Thu May 29 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.2.0-1
- Remove tools descontinuadas (VPN, Network Scanner, Firmware, Hash Tools)
- Renomeia vigia-capabilities -> vigia-caps
- Adiciona vigia-rootkit
- Metapackage agora cobre as 14 ferramentas + Instalador

* Mon May 26 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.0-1
- Metapackage v0.1.0 incluindo as 18 tools do VigiaOS
