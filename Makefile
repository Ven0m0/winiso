# =============================================================================
# Debloated Windows 11 ISO Builder
# =============================================================================
# Targets:
#   make deps           - Install system dependencies
#   make build          - Build debloated ISO (Pro for Workstations preferred)
#   make build-pro      - Build with Pro edition only
#   make build-nano     - Extreme debloating (NANO mode)
#   make build-pause    - Build and pause for Windows servicing stage
#   make clean          - Remove build artifacts
#   make help           - Show this help
# =============================================================================

.PHONY: all deps build build-pro build-nano build-pause clean help validate download validate-xml validate-reg validate-debloat sign

# Default target
all: build

# Install system dependencies
deps:
	@echo "Installing dependencies..."
	chmod +x scripts/setup_env.py
	./scripts/setup_env.py

# Validate prerequisites
validate:
	@echo "Validating prerequisites..."
	chmod +x scripts/validate_prereqs.py
	./scripts/validate_prereqs.py

# Validate all XML config files: well-formedness, UTF-8-no-BOM, and that
# config/autounattend.xml (a symlink) resolves to the canonical ventoy/answer copy
validate-xml:
	@echo "Validating XML config files..."
	chmod +x scripts/validate_xml.py
	./scripts/validate_xml.py

# Validate .reg headers, including .reg content embedded in autounattend.xml
validate-reg:
	@echo "Validating registry files..."
	chmod +x scripts/validate_reg_files.py
	./scripts/validate_reg_files.py

# Validate debloat glob patterns (syntax, duplicates, keep-list collisions)
validate-debloat:
	@echo "Validating debloat patterns..."
	chmod +x scripts/validate_debloat.py
	./scripts/validate_debloat.py

# Download UUP files from uupdump.net
download:
	@echo "Downloading UUP files..."
	chmod +x scripts/download_uup.py
	./scripts/download_uup.py

# Build debloated ISO (default: Pro for Workstations, fallback Pro)
build:
	@echo "Building debloated Windows 11 ISO..."
	chmod +x scripts/build.py
	./scripts/build.py

# Build with Pro edition specifically
build-pro:
	@echo "Building Windows 11 Pro ISO..."
	chmod +x scripts/build.py
	TARGET_EDITION=Professional FALLBACK_EDITION=Professional ./scripts/build.py

# Build with Nano mode (extreme debloating)
build-nano:
	@echo "Building with Nano-style extreme debloating..."
	chmod +x scripts/build.py
	NANO=1 ./scripts/build.py

# Build and pause for Windows servicing stage
# Use this when you want to run DISM cleanup, 8.3 stripping, etc. on Windows
build-pause:
	@echo "Building with Windows servicing pause..."
	@echo "When paused, copy ISODIR/sources/install.wim to a Windows machine"
	@echo "and run scripts/windows_service.cmd against it."
	chmod +x scripts/build.py
	PAUSE_FOR_WINDOWS_STAGE=1 ./scripts/build.py

# Sign an ISO with SHA256/SHA512 checksums (and optionally GPG)
# Usage: make sign ISO=output/Win11.iso [GPG=1 KEY=maintainer@example.com]
sign:
	@if [[ -z "$(ISO)" ]]; then \
		echo "Usage: make sign ISO=path/to/file.iso [GPG=1 KEY=gpg-key-id]"; \
		exit 1; \
	fi
	chmod +x scripts/sign_iso.py
	@if [[ "$(GPG)" == "1" ]]; then \
		./scripts/sign_iso.py --gpg --key "$(KEY)" "$(ISO)"; \
	else \
		./scripts/sign_iso.py "$(ISO)"; \
	fi

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf scripts/ISODIR
	rm -f scripts/*.iso
	rm -f output/*.iso
	@echo "Clean complete."

# Show help
help:
	@echo "Debloated Windows 11 ISO Builder"
	@echo ""
	@echo "Usage:"
	@echo "  make deps        - Install system dependencies (run once)"
	@echo "  make download    - Download UUP files from uupdump.net"
	@echo "  make validate    - Validate prerequisites before building"
	@echo "  make build       - Build debloated ISO"
	@echo "  make build-pro   - Build with Windows 11 Pro only"
	@echo "  make build-nano  - Build with extreme debloating (NANO mode)"
	@echo "  make build-pause - Pause for Windows servicing stage"
	@echo "  make sign        - Sign an ISO with checksums (GPG optional)"
	@echo "  make clean       - Remove all build artifacts"
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Run 'make deps' to install required tools"
	@echo "  2. Run 'make download' to get UUP files (or download manually)"
	@echo "  3. (Optional) Edit config/autounattend.xml"
	@echo "  4. (Optional) Edit config/debloat_list.txt"
	@echo "  5. Run 'make validate-debloat' to check debloat patterns"
	@echo "  6. Run 'make validate' to check everything is ready"
	@echo ""
	@echo "Environment Variables:"
	@echo "  TARGET_EDITION       - Preferred edition (default: ProfessionalWorkstation)"
	@echo "  FALLBACK_EDITION     - Fallback if target not found (default: Professional)"
	@echo "  PROFILE              - Named profile from config/profiles.json (sets edition)"
	@echo "  PAUSE_FOR_WINDOWS_STAGE - Set to 1 to pause for DISM servicing"
	@echo "  NANO                 - Set to 1 for extreme debloating"
