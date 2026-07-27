@echo off
winget install -h --accept-package-agreements --accept-source-agreements --disable-interactivity --nowarn --force Git.Git 7zip.7zip astral-sh.uv Python.Python.3.14 Microsoft.PowerShell Microsoft.WindowsTerminal jdx.mise GitHub.cli Oven-sh.Bun Microsoft.DirectX sinelaw.fresh-editor OpenJS.NodeJS TechPowerUp.NVCleanstall GlennDelahoy.SnappyDriverInstallerOrigin Rustlang.Rustup Mozilla.sccache topgrade-rs.topgrade Devolutions.UniGetUI Microsoft.VisualStudio.BuildTools VSCodium.VSCodium PrismLauncher.PrismLauncher ImputNet.Helium Gyan.FFmpeg.Essentials EpicGames.EpicGamesLauncher Valve.Steam SteelSeries.GG abbodi1406.vcredist aria2.aria2 >> "%TEMP%\Apps.log" 2>&1
powercfg /h off >NUL 2>&1
fsutil behavior set disable8dot3 1 >NUL 2>&1
fsutil behavior set disablecompression 0 >NUL 2>&1
Dism /Online /Cleanup-Image /StartComponentCleanup
powercfg /S 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
