# Autounattend.xml Configuration Guide

`config/autounattend.xml` is the answer file that automates Windows installation. It is a symlink to the canonical `ventoy/answer/autounattend.xml`; edit the canonical file (the same file is used for Ventoy). The file must be UTF-8 without a BOM. `custom_convert.sh` copies it into the ISO root.

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
- **Scripted windowsPE pass**: there is no `<DiskConfiguration>` or `<ImageInstall>`. A chain of `RunSynchronousCommand` entries writes `X:\pe.cmd` in WinPE, which checks the target disk, runs `diskpart`, lists the images with `dism /Get-WimInfo`, prompts for the image index, runs `dism /Apply-Image` and `bcdboot`, then copies the answer file to `Windows\Panther\unattend.xml` so the specialize and oobeSystem passes use it. A deliberate `pause` guards the disk wipe, and `assert.vbs` refuses disks under 100 GiB or with existing partitions
- **Setup requirement bypasses**: TPM, Secure Boot, RAM, CPU and network (`BypassNRO`) bypass values are written by `.reg` content embedded in the file
- **First logon**: `FirstLogon.ps1` runs from `C:\Windows\Setup\Scripts`; `config/oem/SetupComplete.cmd` (CRLF) is injected through `$OEM$` and runs on first boot
- **No `ProductKey`**: never add a real or unverified key to this file
- **Local account**: the shipped file defines one local administrator with a base64-encoded password (`PlainText` false). That is encoding, not encryption; change the account name and password before sharing an ISO

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
4. Replace `ventoy/answer/autounattend.xml` with your custom version (not the `config/autounattend.xml` symlink; overwriting the symlink breaks the sync check in `make validate-xml`)

A generator file replaces the scripted windowsPE pass described above. Make sure the result still partitions the disk and applies the image, and drop any `ProductKey` element the generator adds.

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
# Every *.xml file: well-formed, UTF-8 without BOM, and config/autounattend.xml
# still resolves to ventoy/answer/autounattend.xml (uses xmllint if installed,
# otherwise stdlib ElementTree)
make validate-xml

# .reg content embedded in the answer file (and standalone .reg files)
make validate-reg

# Direct syntax check
xmllint --noout config/autounattend.xml
```

`make validate` (and the pre-build check in `make build`) also runs `xmllint --noout` on the file when `xmllint` is installed, and only warns when it is missing.

## Testing

After building your ISO:

0. On a Windows host with Hyper-V, `mise run test-iso` (`scripts/Test-IsoBoot.ps1`) automates the steps below; see `docs/hyperv-testing.md`
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
- Product keys (this repo's file ships none; keep it that way)
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
