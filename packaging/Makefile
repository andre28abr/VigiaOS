# Makefile para empacotamento local da Vigia Suite.
# Usado para sanity-check antes de submeter ao COPR.

VERSION  := $(shell grep '^version' ../tools/activity-log/Cargo.toml | head -1 | cut -d'"' -f2)
ARCH     := $(shell uname -m)
TOPDIR   := $(CURDIR)/rpmbuild

.PHONY: help srpm rpm clean tarball test-deps

help:
	@echo "Vigia Suite packaging (version: $(VERSION), arch: $(ARCH))"
	@echo ""
	@echo "Targets:"
	@echo "  make tarball   - cria source tarball local (substitui o do GitHub release)"
	@echo "  make srpm      - build SRPM (a partir do tarball local)"
	@echo "  make rpm       - build RPM completo (precisa de rpmbuild + rust)"
	@echo "  make clean     - limpa rpmbuild/"
	@echo ""

tarball:
	@echo "==> Gerando tarball v$(VERSION)..."
	@mkdir -p $(TOPDIR)/SOURCES
	@cd ../.. && tar czf "Vigia SO/packaging/$(TOPDIR)/SOURCES/VigiaOS-$(VERSION).tar.gz" \
	    --exclude='Vigia SO/.git' \
	    --exclude='Vigia SO/.claude' \
	    --exclude='Vigia SO/tools/activity-log/target' \
	    --transform 's|^Vigia SO|VigiaOS-$(VERSION)|' \
	    "Vigia SO/"
	@ls -lh $(TOPDIR)/SOURCES/

srpm: tarball
	@mkdir -p $(TOPDIR)/SPECS $(TOPDIR)/SRPMS
	@cp vigia-activity-log.spec $(TOPDIR)/SPECS/
	rpmbuild -bs $(TOPDIR)/SPECS/vigia-activity-log.spec \
	    --define "_topdir $(TOPDIR)"
	@ls -lh $(TOPDIR)/SRPMS/

rpm: tarball
	@mkdir -p $(TOPDIR)/SPECS $(TOPDIR)/RPMS
	@cp vigia-activity-log.spec $(TOPDIR)/SPECS/
	rpmbuild -bb $(TOPDIR)/SPECS/vigia-activity-log.spec \
	    --define "_topdir $(TOPDIR)"
	@find $(TOPDIR)/RPMS -name '*.rpm' -exec ls -lh {} \;

clean:
	rm -rf $(TOPDIR)

test-deps:
	@echo "Verificando dependencias de build:"
	@which rpmbuild && echo "  rpmbuild: OK" || echo "  rpmbuild: FALTA (sudo dnf install rpm-build)"
	@which cargo && echo "  cargo:    OK" || echo "  cargo:    FALTA (sudo dnf install cargo)"
	@which rustc && echo "  rustc:    OK" || echo "  rustc:    FALTA (sudo dnf install rust)"
