# RPM spec para vigia-suite (metapackage)
# Instala TODAS as ferramentas da Vigia Suite numa unica operacao.
# Sem code/files proprios — apenas Requires.

%global pkg_name vigia-suite

Name:           %{pkg_name}
Version:        0.1.0
Release:        1%{?dist}
Summary:        Suite completa de seguranca para Fedora Atomic (metapackage)
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
Requires:       vigia-vpn >= 0.1.1
Requires:       vigia-dns >= 0.1.0

# Defesa & hardening
Requires:       vigia-selinux >= 0.2.0
Requires:       vigia-firewall >= 0.1.0
Requires:       vigia-hardening >= 0.1.2
Requires:       vigia-integrity >= 0.1.3
Requires:       vigia-capabilities >= 0.1.0
Requires:       vigia-antivirus >= 0.1.1
Requires:       vigia-netscan >= 0.1.0
Requires:       vigia-firmware >= 0.1.0
Requires:       vigia-hash-tools >= 0.1.1

# Relatorios
Requires:       vigia-reports >= 0.1.1

# Catalogo (entidade especial — instalavel mas opcional)
Requires:       vigia-installer >= 0.1.0

%description
Vigia Suite — metapackage que instala TODAS as 18 ferramentas
de seguranca e monitoramento da Vigia Suite numa unica operacao.

Apos instalacao, abra "Vigia Hub" no menu GNOME para acessar todas
as ferramentas embarcadas em uma unica janela.

Categorias:
- Monitoramento: Dashboard, Activity Log, Network Monitor
- Privacidade:   Privacy Controls, VPN Manager, DNS Manager
- Defesa:        SELinux, Firewall, Hardening Checks, File Integrity,
                 Capabilities Inspector, Antivirus, Network Scanner,
                 Firmware Analyzer, Hash Tools
- Relatorios:    Reports (PDF/HTML LGPD)
- Catalogo:      Tool Installer (~30 ferramentas extras)

Compatibilidade: Fedora Silverblue, Kinoite, Bluefin, Bazzite, Aurora.

%prep
# Metapackage — nada para preparar.

%build
# Metapackage — nada para buildar.

%install
# Metapackage — nada para instalar.

%files
# Metapackage — sem arquivos.

%changelog
* Mon May 26 2026 André Augusto Azarias de Souza <andre@vigia.local> - 0.1.0-1
- Metapackage v0.1.0 incluindo as 18 tools da Vigia Suite
