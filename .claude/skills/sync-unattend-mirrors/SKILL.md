---
name: sync-unattend-mirrors
description: Check config/unattend-generator/*.cmd/*.ps1/*.reg against the generator-URL comment embedded at the top of ventoy/answer/autounattend.xml, and reconcile any drift. Use when the autounattend.xml has been regenerated from schneegans.de/windows/unattend-generator/, or when the user asks to sync the unattend mirrors.
disable-model-invocation: true
---

# Sync unattend-generator mirrors

`ventoy/answer/autounattend.xml` (canonical; `config/autounattend.xml` is a
symlink to it) embeds its full generator query string as a URL-encoded HTML
comment on line 3. `config/unattend-generator/` keeps human-readable copies
of the script parameters from that URL:

| URL param | Mirror file |
|---|---|
| `SystemScript1` (Ps1) | `config/unattend-generator/system.ps1` |
| `FirstLogonScript0` (Cmd) | `config/unattend-generator/after-logon.cmd` |
| Registry bypass/tweak params (`SystemScript2`, `FirstLogonScript2`, Reg-type) | `config/unattend-generator/apply.reg` |

## Steps

1. Extract line 3 of `ventoy/answer/autounattend.xml` and URL-decode it:
   ```bash
   python3 -c "
   import re, urllib.parse
   with open('ventoy/answer/autounattend.xml', encoding='utf-8') as f:
       for line in f:
           if 'schneegans.de' in line:
               url = re.search(r'https://schneegans\.de[^\"\x27>]*', line).group(0)
               break
   qs = urllib.parse.parse_qs(url.split('?', 1)[1])
   for k in sorted(qs):
       if k.startswith(('SystemScript', 'FirstLogonScript')):
           print(f'--- {k} ---')
           print(urllib.parse.unquote(qs[k][0]).replace('\r\n', '\n'))
   "
   ```
2. Compare each decoded script body against its mirror file (`system.ps1`,
   `after-logon.cmd`, `apply.reg`). Whitespace/line-ending differences from
   URL-decoding are expected — compare content, not bytes.
3. If they've drifted (the answer file was regenerated with new params, or a
   mirror file was hand-edited without updating the source), tell the user
   which direction the drift went before changing anything:
   - Answer file has new/changed script content → update the mirror file to
     match, and note the change in the mirror file only if the mirror already
     carries commentary (do not add commentary the generator itself doesn't
     produce).
   - Mirror file was edited but the answer file wasn't → the edit needs to be
     re-applied through the generator UI and the resulting URL/XML pasted back
     into `ventoy/answer/autounattend.xml`; this skill cannot safely
     re-encode a script back into the generator's query-string format.
4. Never touch `AppLockerMode`, `PEMode`, disk/partition, or account-password
   params while doing this — those aren't mirrored anywhere and are out of
   scope for this skill.
5. After reconciling, remind the user to re-run `make validate-xml` (checks
   the `config/autounattend.xml` symlink stays in sync with
   `ventoy/answer/autounattend.xml`, plus UTF-8/no-BOM).
