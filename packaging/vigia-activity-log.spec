# RPM spec para Vigia Activity Log
# Buildado via COPR (https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/)
# Source: https://github.com/andre28abr/VigiaOS

%global crate_name vigia-activity-log
%global bin_name   vigia-log

Name:           %{crate_name}
Version:        0.7.0
Release:        1%{?dist}
Summary:        Parser de logs do Linux com narrativa human-readable (Vigia Suite)
License:        Apache-2.0
URL:            https://github.com/andre28abr/VigiaOS
Source0:        %{url}/archive/v%{version}.tar.gz#/VigiaOS-%{version}.tar.gz

BuildRequires:  rust >= 1.75
BuildRequires:  cargo

# Roda em qualquer arch que tenha Rust stable (aarch64 e x86_64 cobertos).
ExclusiveArch:  %{rust_arches}

%description
Vigia Activity Log faz parte da Vigia Suite — toolkit de seguranca
para Fedora Atomic. Le /var/log/audit/audit.log, systemd journal e
/var/log/fail2ban.log, sintetiza eventos em narrativas human-readable
em portugues, detecta correlations cross-source (ex: fail2ban burst,
kernel OOM, SELinux denial burst, SSH login suspeito), classifica
cada evento por severidade (rotineiro/interessante/suspeito), e
oferece TUI interativa com filtros, busca e live tail mode.

Comando: vigia-log

%prep
%autosetup -n VigiaOS-%{version}/tools/activity-log

%build
# COPR builders tipicamente tem rede; build cargo normal funciona.
# --locked garante usar exatamente o Cargo.lock commitado.
cargo build --release --locked

%install
install -Dpm 0755 target/release/%{bin_name} %{buildroot}%{_bindir}/%{bin_name}
install -Dpm 0644 README.md %{buildroot}%{_docdir}/%{name}/README.md

%files
%license LICENSE
%doc README.md
%{_bindir}/%{bin_name}

%changelog
* Thu May 22 2026 Andre Augusto Azarias de Souza <andre@example.com> - 0.7.0-1
- Initial COPR release.
- Multi-source: audit, journald, fail2ban.
- Correlator com 4 patterns (fail2ban_burst, oom_kill, selinux_burst, suspicious_ssh_login).
- Classificador per-evento com filtro --min-severity.
- Live tail mode (-f) com polling 2s.
- TUI Ratatui com paleta zinc + emerald.
