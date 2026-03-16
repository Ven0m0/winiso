# =============================================================================
# Debloated Windows 11 ISO Builder
# =============================================================================
# Targets:
#   make deps           - Install system dependencies
#   make build          - Build debloated ISO (Pro for Workstations preferred)
#   make build-pro      - Build with Pro edition only
#   make build-pause    - Build and pause for Windows servicing stage
#   make clean          - Remove build artifacts
#   make help           - Show this help
# =============================================================================

.PHONY: all deps build build-pro build-pause clean help validate download

# Default target
all: build

# Install system dependencies
deps:
	@echo "Installing dependencies..."
	./scripts/setup_env.sh

# Validate prerequisites
validate:
	@echo "Validating prerequisites..."
	chmod +x scripts/*.sh
	./scripts/validate_prereqs.sh

# Download UUP files from uupdump.net
download:
	@echo "Downloading UUP files..."
	chmod +x scripts/download_uup.py
	./scripts/download_uup.py

# Build debloated ISO (default: Pro for Workstations, fallback Pro)
build:
	@echo "Building debloated Windows 11 ISO..."
	chmod +x scripts/*.sh
	./scripts/build.sh

# Build with Pro edition specifically
build-pro:
	@echo "Building Windows 11 Pro ISO..."
	chmod +x scripts/*.sh
	TARGET_EDITION=Professional FALLBACK_EDITION=Professional ./scripts/build.sh

# Build and pause for Windows servicing stage
# Use this when you want to run DISM cleanup, 8.3 stripping, etc. on Windows
build-pause:
	@echo "Building with Windows servicing pause..."
	@echo "When paused, copy ISODIR/sources/install.wim to a Windows machine"
	@echo "and run scripts/windows_service.cmd against it."
	chmod +x scripts/*.sh
	PAUSE_FOR_WINDOWS_STAGE=1 ./scripts/build.sh

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
	@echo "  make build-pause - Pause for Windows servicing stage"
	@echo "  make clean       - Remove all build artifacts"
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Run 'make deps' to install required tools"
	@echo "  2. Run 'make download' to get UUP files (or download manually)"
	@echo "  3. (Optional) Edit config/autounattend.xml"
	@echo "  4. (Optional) Edit config/debloat_list.txt"
	@echo "  5. Run 'make validate' to check everything is ready"
	@echo ""
	@echo "Environment Variables:"
	@echo "  TARGET_EDITION       - Preferred edition (default: ProfessionalWorkstation)"
	@echo "  FALLBACK_EDITION     - Fallback if target not found (default: Professional)"
	@echo "  PAUSE_FOR_WINDOWS_STAGE - Set to 1 to pause for DISM servicing"
