# Vigia Suite — Empacotamento RPM (COPR)

Este diretório contém os **spec files RPM** para distribuir a Vigia
Suite via COPR (Cool Other Package Repo, do Fedora).

## Estado

- **20 spec files** no total (`vigia-common` + 18 tools + metapackage `vigia-suite`)
- `Makefile` com targets para SRPM, RPM local e push COPR
- **COPR ainda não foi ativado** — requer setup manual (instruções abaixo)

## Para o usuário final (instalar)

> ⚠️ **Repo COPR ainda não foi ativado.** Os comandos abaixo só
> funcionam APÓS o setup manual descrito mais adiante (criar conta,
> projeto, fazer build). Por enquanto, instale via
> `pip install --user -e .` — ver [README principal](../README.md).

Quando o COPR estiver publicado, em Silverblue/Kinoite/Bluefin/etc.:

```bash
# 1. Habilita o repo (substitui $(rpm -E %fedora) pela versao detectada)
sudo wget -O /etc/yum.repos.d/_copr_andre28abr-vigia.repo \
    "https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/repo/fedora-$(rpm -E %fedora)/andre28abr-vigia-fedora-$(rpm -E %fedora).repo"

# 2. Instala a suite completa (metapackage com as 18 tools)
sudo rpm-ostree install vigia-suite
sudo systemctl reboot

# OU instala tools individuais
sudo rpm-ostree install vigia-dashboard vigia-antivirus
sudo systemctl reboot
```

Em Fedora não-atomic (Workstation, KDE Plasma, etc.):

```bash
sudo dnf copr enable andre28abr/vigia
sudo dnf install vigia-suite
```

> **Nota sobre rpm-ostree**: ao contrário do `dnf`, o `rpm-ostree`
> NÃO tem subcomando `copr`. Para habilitar repos COPR em Silverblue
> você precisa baixar o `.repo` direto (método acima) — ou instalar
> `dnf` overlay primeiro (`sudo rpm-ostree install dnf && reboot`)
> e usar `sudo dnf copr enable ...`.

## Lista de specs

| Pacote | Versão | Tipo |
|---|---|---|
| `vigia-suite` | 0.1.0 | **metapackage** (instala tudo) |
| `vigia-common` | 0.1.0 | lib interna (dep de todas) |
| `vigia-activity-log` | 0.7.0 | core Rust |
| `vigia-activity-log-gui` | 0.1.0 | frontend Python |
| `vigia-hub` | 0.5.0 | launcher mestre |
| `vigia-dashboard` | 0.2.0 | sistema em tempo real |
| `vigia-privacy` | 0.3.0 | 13 toggles |
| `vigia-selinux` | 0.2.0 | SELinux GUI |
| `vigia-firewall` | 0.1.0 | firewalld GUI |
| `vigia-netmon` | 0.1.0 | conexões TCP/UDP |
| `vigia-hardening` | 0.1.2 | Lynis |
| `vigia-reports` | 0.1.1 | PDF LGPD |
| `vigia-integrity` | 0.1.3 | AIDE |
| `vigia-installer` | 0.1.0 | catálogo tools |
| `vigia-vpn` | 0.1.1 | WireGuard |
| `vigia-dns` | 0.1.0 | systemd-resolved |
| `vigia-capabilities` | 0.1.0 | getcap |
| `vigia-antivirus` | 0.1.1 | ClamAV |
| `vigia-netscan` | 0.1.0 | nmap |
| `vigia-firmware` | 0.1.0 | binwalk |
| `vigia-hash-tools` | 0.1.1 | hash + baseline |

## Para o mantenedor (build + submit ao COPR)

### Setup inicial (uma vez)

```bash
make copr-setup    # imprime instruções
```

**Resumo**:
1. Criar conta em https://copr.fedorainfracloud.org/
2. Criar projeto `vigia` (chroots: fedora-40/41/42 x86_64/aarch64)
3. Instalar `copr-cli` (`sudo rpm-ostree install copr-cli`)
4. Configurar token em `~/.config/copr` (chmod 0600)

### Build local + sanity check

```bash
cd VigiaOS/packaging

# Gerar todos os SRPMs (sem submeter)
make srpm-all

# Ou apenas 1 pacote
make srpm-vigia-dashboard

# Build local via mock (precisa mock instalado)
make rpm-all

# Output em:
#   dist/rpmbuild/SOURCES/VigiaOS-0.1.0.tar.gz
#   dist/rpmbuild/SRPMS/*.src.rpm
#   dist/rpms/*.rpm  (se rpm-all)
```

### Submit ao COPR

```bash
# Todos os pacotes:
make copr-push

# Pacote individual:
make copr-push-vigia-dashboard
```

### Webhook SCM (auto-rebuild)

No COPR, project settings → **Builds from SCM**:
- **Source type**: Git
- **Clone URL**: `https://github.com/andre28abr/VigiaOS`
- **Branch**: `main`
- **Subdirectory**: `packaging`
- **Build method**: rpkg

Apos isso, a cada `git push origin main` o COPR rebuilda
automaticamente os pacotes que mudaram.

### Bump de versão

1. Bump em `tools/<X>/pyproject.toml` (Python) ou `Cargo.toml` (Rust)
2. Bump em `tools/<X>/src/vigia_<X>/__init__.py` (`__version__`)
3. Atualizar `Version:` no spec correspondente em `packaging/`
4. Adicionar entry em `%changelog`
5. Bump em `packaging/vigia-suite.spec` (versão mínima no Requires)
6. Tag: `git tag v0.X.Y && git push origin v0.X.Y`
7. COPR rebuilda (se webhook configurado)

## Estrutura

```
packaging/
├── README.md                       # este arquivo
├── Makefile                        # build automation
│
├── vigia-suite.spec                # metapackage (Requires: tudo)
├── vigia-common.spec               # lib interna
├── vigia-activity-log.spec         # core Rust (pre-existente)
│
├── vigia-activity-log-gui.spec     # GUI Python
├── vigia-hub.spec
├── vigia-dashboard.spec
├── vigia-privacy.spec
├── vigia-selinux.spec
├── vigia-firewall.spec
├── vigia-netmon.spec
├── vigia-hardening.spec
├── vigia-reports.spec
├── vigia-integrity.spec
├── vigia-installer.spec
├── vigia-vpn.spec
├── vigia-dns.spec
├── vigia-capabilities.spec
├── vigia-antivirus.spec
├── vigia-netscan.spec
├── vigia-firmware.spec
├── vigia-hash-tools.spec
│
├── vigia-log.desktop               # pre-existente (Activity Log core)
└── vigia-log.svg                   # pre-existente
```

## Próximos passos

- [ ] Criar conta no COPR
- [ ] Criar projeto `andre28abr/vigia`
- [ ] Selecionar chroots
- [ ] Instalar copr-cli + configurar token
- [ ] `make copr-push` inicial
- [ ] Configurar webhook SCM
- [ ] Testar instalação em VM limpa de Silverblue
- [ ] AppStream metadata em `data/<app-id>.appdata.xml`
  (para integração com GNOME Software)
- [ ] Submeter Activity Log para Fedora Workstation Software

## Detalhes técnicos

### Specs Python (17 tools)

Padrão comum:
- `BuildArch: noarch` — sem código nativo
- `BuildRequires`: python3-devel + setuptools + wheel + pip
- Build via `pip wheel --no-deps`
- Install via `pip install --root --no-deps --no-index`
- Files: `%{python3_sitelib}/<mod>/`, `.desktop`, `.svg`, `/usr/bin/vigia-X`
- `desktop-file-validate` no install
- `%post`/`%postun`/`%posttrans` para `gtk-update-icon-cache` +
  `update-desktop-database`

### Activity Log core (Rust)

Spec separado (`vigia-activity-log.spec`) porque é Rust.
`BuildArch` = `%{rust_arches}` (aarch64 + x86_64).

### Metapackage `vigia-suite`

Sem `%files`, apenas `Requires:` listando todos os 19 pacotes.
Garante versão mínima de cada. Útil para "instalar tudo de uma vez".

### Dependências entre pacotes

`vigia-common` é dependência de **todas** as outras tools Python.

`vigia-activity-log-gui` depende de `vigia-activity-log` (Rust core).

Pacotes que wrappam tools upstream declaram esses como `Requires`:
- `vigia-selinux` → `policycoreutils-python-utils`, `setools-console`, `audit`
- `vigia-antivirus` → `clamav`, `clamav-update`
- `vigia-vpn` → `wireguard-tools`
- `vigia-integrity` → `aide`
- etc.

### LGPD / sandbox

Nenhum spec instala ou abre serviço de rede automaticamente. Tudo
opt-in pelo user via interfaces das tools. Permissões `0600` em
reports são aplicadas pelos backends (não pelos specs).

## Verificação de assinatura (futuro)

Quando assinatura RPM for habilitada no COPR:

```bash
rpm --import https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/pubkey.gpg
rpm --checksig vigia-*.rpm
```
