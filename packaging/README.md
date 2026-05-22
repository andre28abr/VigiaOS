# Empacotamento RPM via COPR

Esta pasta contem o spec file e instrucoes para empacotar a **Vigia Suite**
como RPMs distribuiveis via [Fedora COPR](https://copr.fedorainfracloud.org/).

## Para o usuario final (instalar)

Quando o COPR estiver publicado, em qualquer Fedora Atomic (Silverblue / Kinoite / Bluefin / etc.):

```bash
# Habilitar o repo
sudo curl -L -o /etc/yum.repos.d/_copr_andre28abr-vigia.repo \
    https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/repo/fedora-44/andre28abr-vigia-fedora-44.repo

# Layerar pelo rpm-ostree (Atomic)
rpm-ostree install vigia-activity-log
systemctl reboot
```

Em Fedora normal (nao-atomic) basta `sudo dnf install vigia-activity-log`.

## Para quem fez build local (sem COPR ainda)

Apos `cargo build --release && sudo install ... /usr/local/bin/`, voce
pode adicionar a entry "Vigia Activity Log" no menu do GNOME (no seu user)
sem precisar de COPR ou root:

```bash
cd ~/dev/VigiaOS/packaging
make install-desktop
```

Isso copia o `.desktop` e o icone SVG para `~/.local/share/`. Procure por
"Vigia" no GNOME Activities (Super tecla). Para remover:

```bash
make uninstall-desktop
```

## Para o mantenedor (build local e submit ao COPR)

### Pre-requisitos

- conta no [copr.fedorainfracloud.org](https://copr.fedorainfracloud.org/)
- `copr-cli` instalado (`sudo dnf install copr-cli`)
- token configurado em `~/.config/copr` (gerado em copr → Settings → API)

### Setup inicial do projeto COPR (one-shot)

```bash
copr-cli create andre28abr/vigia \
    --chroot fedora-44-aarch64 \
    --chroot fedora-44-x86_64 \
    --description "Vigia Suite — security toolkit para Fedora Atomic"
```

### Build de uma versao

1. **Tag e push do repo principal** (com versao em Cargo.toml ja bumped):
   ```bash
   git tag v0.7.0
   git push origin v0.7.0
   ```
   Isso cria automaticamente um tarball acessivel em
   `https://github.com/andre28abr/VigiaOS/archive/v0.7.0/VigiaOS-0.7.0.tar.gz`.

2. **Build local opcional** (sanity check com mock):
   ```bash
   cd packaging
   # Gera SRPM
   rpmbuild -bs vigia-activity-log.spec \
       --define "_sourcedir $PWD" \
       --define "_srcrpmdir $PWD" \
       --define "_topdir $PWD/rpmbuild"
   # Testa build
   mock -r fedora-44-aarch64 rpmbuild/*.src.rpm
   ```

3. **Submit ao COPR**:
   ```bash
   copr-cli build andre28abr/vigia rpmbuild/*.src.rpm
   ```

   Ou (preferido) use o SCM method da web UI:
   - Project Settings → Packages → New Package
   - Source Type: SCM
   - Clone URL: `https://github.com/andre28abr/VigiaOS`
   - Spec File: `packaging/vigia-activity-log.spec`
   - Webhook: rebuilda automatico a cada push em main

### Bump de versao

1. Atualizar `Version:` no spec file
2. Atualizar `[package].version` em `tools/activity-log/Cargo.toml`
3. Adicionar entry ao `%changelog`
4. Tag novo: `git tag v0.8.0 && git push origin v0.8.0`
5. COPR rebuilda automatico (se webhook configurado)

## Verificacao de assinatura

(Se assinatura RPM for habilitada no COPR — opcional para v1)

```bash
# Importar chave publica do COPR project
rpm --import https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/pubkey.gpg

# Verificar antes de instalar
rpm --checksig vigia-activity-log-*.rpm
```
