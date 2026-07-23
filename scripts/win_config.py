"""Configuration for apply_image_settings.py. Adjust these values for your environment."""

# Path to oscdimg.exe (Windows ADK - Deployment Tools). None = auto-search common locations.
OSCDIMG_PATH: str | None = None

# Default mount directory
DEFAULT_MOUNT_DIR = r"C:\Mount"

# Install.wim index to use (1 = Pro, 2 = Home, etc.)
INSTALL_WIM_INDEX = 1

# Boot.wim indexes to process (only index 1 exists in standard Windows 11 ISOs)
BOOT_WIM_INDEXES = [1]

# ISO Volume Label
VOLUME_LABEL = "WIN11"

# Temporary extraction directory (auto-cleaned)
TEMP_EXTRACT_DIR = r"C:\Temp\ISO_Extract"
