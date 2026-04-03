# Autounattend.xml Configuration Guide

`config/autounattend.xml` is the answer file that automates Windows installation.

## What is autounattend.xml?

`autounattend.xml` is an answer file that automates the Windows installation process. When placed in the root of the installation media, it:
- Skips interactive setup prompts (language, region, keyboard)
- Bypasses OOBE (Out of Box Experience)
- Configures privacy settings automatically
- Sets up local user accounts
- Applies initial Windows configuration

## Current Configuration

The included `autounattend.xml` is configured with:
- **Skip Microsoft Account**: Creates local administrator account
- **Minimal Telemetry**: Sets data collection to minimum (Security level)
- **Privacy Optimized**: Disables location, diagnostics, tailored experiences
- **OOBE Bypass**: Skips most first-boot prompts
- **Keep Essential Services**: Defender, Windows Update, Microsoft Store remain functional

## Customizing autounattend.xml

### Option 1: Use Schneegans Generator (Recommended)

To create a custom autounattend.xml:

1. Visit https://schneegans.de/windows/unattend-generator/
2. Configure your preferences:
   - **Account**: Local account (recommended) or Microsoft account
   - **Privacy**: Minimal telemetry, disable diagnostics
   - **Network**: Skip network setup or configure
   - **Apps**: Keep Windows Update, Defender, Store
3. Download the generated XML
4. Replace `config/autounattend.xml` with your custom version

### Option 2: Manual Editing

You can manually edit the existing XML file. Key sections:

#### User Account Configuration
```xml
<UserAccounts>
    <LocalAccounts>
        <LocalAccount>
            <Name>Admin</Name>
            <Password>YourPasswordHere</Password>
        </LocalAccount>
    </LocalAccounts>
</UserAccounts>
```

#### Privacy & Telemetry Settings
```xml
<settings pass="oobeSystem">
    <component name="Microsoft-Windows-Shell-Setup">
        <OOBE>
            <ProtectYourPC>3</ProtectYourPC>  <!-- 1=Enable, 3=Disable -->
            <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
        </OOBE>
    </component>
</settings>
```

#### Region & Language
```xml
<settings pass="windowsPE">
    <component name="Microsoft-Windows-International-Core-WinPE">
        <SetupUILanguage>
            <UILanguage>en-US</UILanguage>
        </SetupUILanguage>
        <InputLocale>en-US</InputLocale>
        <SystemLocale>en-US</SystemLocale>
        <UILanguage>en-US</UILanguage>
        <UserLocale>en-US</UserLocale>
    </component>
</settings>
```

## Important Settings Explained

### ProtectYourPC Values
- `1` = Recommended settings (more telemetry)
- `2` = Express settings (moderate telemetry)
- `3` = Custom settings (minimal telemetry) **← Current setting**

### Password Security
**WARNING:** Storing passwords in autounattend.xml is a security risk!

Options:
1. **Leave blank**: Windows will prompt for password during first login
2. **Use placeholder**: Change password immediately after installation
3. **Encrypt the XML**: Use Windows SIM (System Image Manager) to encrypt sensitive sections

### Domain Join
If deploying to domain-joined machines, add:
```xml
<Identification>
    <Credentials>
        <Domain>YOURDOMAIN</Domain>
        <Username>domain\admin</Username>
        <Password>password</Password>
    </Credentials>
    <JoinDomain>YOURDOMAIN.local</JoinDomain>
</Identification>
```

## Validation

Before building your ISO, validate the XML:

```bash
# Check XML syntax
xmllint --noout config/autounattend.xml

# If xmllint is not installed
make validate  # Will check basic XML validity
```

## Testing

After building your ISO:

1. Boot the ISO in a VM (VirtualBox/VMware/QEMU)
2. Verify autounattend is applied:
   - Installation proceeds without prompts
   - Region/language are auto-selected
   - Local account is created
   - OOBE is skipped
3. Check for errors: `C:\Windows\Panther\setuperr.log`

## Troubleshooting

### Autounattend not applied
- Ensure XML is in ISO root (not in sources/)
- Check XML syntax with `xmllint`
- Review `C:\Windows\Panther\setupact.log` for errors
- Verify UEFI/BIOS compatibility settings

### Installation still prompts for settings
- Check ProtectYourPC value is set to 3
- Verify OOBE settings are configured
- Ensure HideEULAPage and HideWirelessSetupInOOBE are true

### Wrong language/region
- Update International-Core-WinPE settings
- Ensure UILanguage, InputLocale, SystemLocale match

## Security Considerations

**IMPORTANT**: autounattend.xml may contain sensitive information:
- User account passwords
- Domain credentials
- Product keys
- Network configurations

**Best Practices**:
- Never commit autounattend.xml with real passwords to version control
- Use placeholder passwords and change immediately after deployment
- Encrypt sensitive sections with Windows SIM
- Restrict access to the ISO/installation media
- Consider using MDT/SCCM for enterprise deployments

## Additional Resources

- [Microsoft Docs: Unattended Windows Setup Reference](https://docs.microsoft.com/en-us/windows-hardware/customize/desktop/unattend/)
- [Schneegans Unattend Generator](https://schneegans.de/windows/unattend-generator/)
- [Windows SIM (System Image Manager)](https://docs.microsoft.com/en-us/windows-hardware/get-started/adk-install)
- [Answer File Examples](https://github.com/topics/unattend)

## Example Configurations

### Minimal Unattended Setup
For users who want minimal automation (just skip prompts):
- Local account with blank password
- Skip privacy prompts
- Auto-accept EULA
- Skip wireless setup

### Enterprise Deployment
For domain-joined workstations:
- Domain join configuration
- Network settings pre-configured
- No local admin account (use domain admin)
- Group Policy applies immediately

### Privacy-Focused Setup
For maximum privacy:
- Telemetry set to Security (minimum)
- Disable all diagnostics and feedback
- Disable location services
- Disable advertising ID
- Local account only (no Microsoft account)

The included `autounattend.xml` follows the **Privacy-Focused Setup** model.
