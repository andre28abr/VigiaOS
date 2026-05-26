# Makefile para empacotamento RPM da Vigia Suite
#
# Targets principais:
#   help              Lista targets
#   tarball           Gera source tarball local
#   srpm-all          Cria SRPMs (Source RPMs) para todos os pacotes
#   rpm-all           Build local de RPMs (precisa mock)
#   srpm-<pkg>        SRPM de um pacote especifico (ex: 'srpm-vigia-dashboard')
#   copr-push         Submete todos os SRPMs para COPR (precisa copr-cli)
#   copr-push-<pkg>   Submete 1 pacote especifico
#   copr-setup        Imprime instrucoes de setup COPR
#   install-desktop   Instala .desktop + icon do Activity Log no HOME
#   clean             Remove dist/

VERSION         ?= 0.1.0
COPR_PROJECT    ?= andre28abr/vigia
TARBALL         := VigiaOS-$(VERSION).tar.gz
DIST_DIR        := dist
TOPDIR          := $(CURDIR)/$(DIST_DIR)/rpmbuild
SRPM_DIR        := $(TOPDIR)/SRPMS
SOURCES_DIR     := $(TOPDIR)/SOURCES
SPECS_DIR       := $(TOPDIR)/SPECS

# Lista de specs (todos os *.spec em packaging/)
SPECS := $(wildcard *.spec)
PACKAGES := $(SPECS:.spec=)

# ====================================================================
# Help
# ====================================================================

.PHONY: help
help:
	@echo "Vigia Suite RPM packaging (v$(VERSION))"
	@echo ""
	@echo "Comum:"
	@echo "  make tarball           - gera dist/rpmbuild/SOURCES/VigiaOS-$(VERSION).tar.gz"
	@echo "  make srpm-all          - gera SRPMs para todos os $(words $(PACKAGES)) specs"
	@echo "  make srpm-vigia-X      - SRPM de pacote especifico"
	@echo "  make copr-push         - submete todos SRPMs ao COPR ($(COPR_PROJECT))"
	@echo "  make copr-setup        - instrucoes de setup inicial"
	@echo "  make clean             - limpa $(DIST_DIR)/"
	@echo ""
	@echo "Pacotes ($(words $(PACKAGES))): $(PACKAGES)"

# ====================================================================
# Tarball — gerado uma vez via git archive
# ====================================================================

$(SOURCES_DIR)/$(TARBALL):
	@mkdir -p $(SOURCES_DIR)
	@echo "==> Gerando tarball $(TARBALL)..."
	cd .. && git archive --format=tar.gz \
		--prefix=VigiaOS-$(VERSION)/ \
		-o "packaging/$(SOURCES_DIR)/$(TARBALL)" HEAD
	@ls -lh $(SOURCES_DIR)/$(TARBALL)

.PHONY: tarball
tarball: $(SOURCES_DIR)/$(TARBALL)

# ====================================================================
# SRPMs — 1 por pacote
# ====================================================================

.PHONY: srpm-all
srpm-all: tarball
	@mkdir -p $(SRPM_DIR) $(SPECS_DIR)
	@cp *.spec $(SPECS_DIR)/
	@for spec in $(SPECS); do \
		echo "==> SRPM $$spec..."; \
		rpmbuild -bs $$spec \
			--define "_topdir $(TOPDIR)" \
			--define "_sourcedir $(SOURCES_DIR)" \
			--define "_srcrpmdir $(SRPM_DIR)" \
			--define "_specdir $(SPECS_DIR)" || exit 1; \
	done
	@echo ""
	@echo "==> SRPMs gerados:"
	@ls -lh $(SRPM_DIR)/

# Per-pacote: 'make srpm-vigia-dashboard'
srpm-%: tarball
	@mkdir -p $(SRPM_DIR) $(SPECS_DIR)
	@cp $*.spec $(SPECS_DIR)/
	rpmbuild -bs $*.spec \
		--define "_topdir $(TOPDIR)" \
		--define "_sourcedir $(SOURCES_DIR)" \
		--define "_srcrpmdir $(SRPM_DIR)"

# ====================================================================
# RPMs locais (precisa mock)
# ====================================================================

.PHONY: rpm-all
rpm-all: srpm-all
	@echo "==> Buildando RPMs via mock..."
	@mkdir -p $(DIST_DIR)/rpms
	@for srpm in $(SRPM_DIR)/*.src.rpm; do \
		echo "  mock $$srpm"; \
		mock --resultdir=$(DIST_DIR)/rpms/ $$srpm || exit 1; \
	done

# ====================================================================
# COPR submission
# ====================================================================

.PHONY: copr-push
copr-push: srpm-all
	@echo "==> Submetendo SRPMs para COPR ($(COPR_PROJECT))..."
	@command -v copr-cli >/dev/null 2>&1 || { \
		echo "ERRO: copr-cli nao instalado. Rode 'make copr-setup'."; exit 1; }
	@test -f ~/.config/copr || { \
		echo "ERRO: token COPR nao configurado em ~/.config/copr"; exit 1; }
	@for srpm in $(SRPM_DIR)/*.src.rpm; do \
		echo "  copr-cli build $(COPR_PROJECT) $$srpm"; \
		copr-cli build $(COPR_PROJECT) $$srpm; \
	done

copr-push-%: srpm-%
	copr-cli build $(COPR_PROJECT) $(SRPM_DIR)/$*-*.src.rpm

# ====================================================================
# Setup COPR (uma vez)
# ====================================================================

.PHONY: copr-setup
copr-setup:
	@echo "Setup COPR:"
	@echo ""
	@echo "1. Acesse: https://copr.fedorainfracloud.org/"
	@echo "2. Login (FedoraID ou GitHub OAuth)"
	@echo "3. Crie projeto 'vigia':"
	@echo "   - URL: https://copr.fedorainfracloud.org/coprs/add"
	@echo "   - Nome: vigia"
	@echo "   - Chroots:"
	@echo "     * fedora-40-x86_64, fedora-40-aarch64"
	@echo "     * fedora-41-x86_64, fedora-41-aarch64"
	@echo "     * fedora-42-x86_64, fedora-42-aarch64"
	@echo "4. Instale copr-cli:"
	@echo "   sudo rpm-ostree install copr-cli && sudo systemctl reboot"
	@echo "5. Baixe token em https://copr.fedorainfracloud.org/api/"
	@echo "   Cole conteudo em ~/.config/copr (chmod 0600)"
	@echo ""
	@echo "Depois rode: make copr-push"

# ====================================================================
# Helpers locais (sem COPR)
# ====================================================================

.PHONY: install-desktop
install-desktop:
	@echo "==> Instalando entry GNOME no HOME do user"
	install -Dm 0644 vigia-log.desktop $(HOME)/.local/share/applications/vigia-log.desktop
	install -Dm 0644 vigia-log.svg     $(HOME)/.local/share/icons/hicolor/scalable/apps/vigia-log.svg
	-update-desktop-database $(HOME)/.local/share/applications 2>/dev/null
	-gtk-update-icon-cache $(HOME)/.local/share/icons/hicolor 2>/dev/null
	@echo "OK"

.PHONY: uninstall-desktop
uninstall-desktop:
	rm -f $(HOME)/.local/share/applications/vigia-log.desktop
	rm -f $(HOME)/.local/share/icons/hicolor/scalable/apps/vigia-log.svg

.PHONY: test-deps
test-deps:
	@echo "Dependencias de build:"
	@which rpmbuild && echo "  rpmbuild: OK" || echo "  rpmbuild: FALTA (sudo dnf install rpm-build)"
	@which cargo && echo "  cargo:    OK" || echo "  cargo:    FALTA (sudo dnf install cargo)"
	@which rustc && echo "  rustc:    OK" || echo "  rustc:    FALTA (sudo dnf install rust)"
	@which copr-cli && echo "  copr-cli: OK" || echo "  copr-cli: FALTA (sudo dnf install copr-cli)"
	@which mock && echo "  mock:     OK" || echo "  mock:     FALTA (sudo dnf install mock)"

# ====================================================================
# Limpeza
# ====================================================================

.PHONY: clean
clean:
	rm -rf $(DIST_DIR)
