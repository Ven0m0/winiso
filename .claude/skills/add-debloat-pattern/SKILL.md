---
name: add-debloat-pattern
description: Add a new bloatware glob pattern to config/debloat_list.txt safely — checks it doesn't collide with the AppX keep-list before adding it, and places it under the right category comment. Use when the user wants to debloat an additional Windows app/package, or says "add X to the debloat list".
disable-model-invocation: true
---

# Add a debloat pattern

Adds one or more glob patterns to `config/debloat_list.txt` without risking a
collision with the AppX keep-list defined in AGENTS.md (`*Store*`, `*WebView*`,
`*VCLibs*`, `*UI.Xaml*`, `*Defender*`, `*DesktopAppInstaller*`).

## Steps

1. Ask the user for the exact AppX package family name (or glob) to remove if
   not already given. Prefer the narrowest pattern that matches — avoid broad
   wildcards that could catch unrelated packages.
2. Check the pattern against the keep-list before writing anything:
   ```bash
   python3 -c "
   import re, sys
   keep = re.compile(r'Store|WebView|VCLibs|UI\.Xaml|Defender|DesktopAppInstaller')
   pattern = sys.argv[1]
   if keep.search(pattern):
       print(f'REFUSED: {pattern!r} overlaps the AppX keep-list (AGENTS.md Hard Invariants)')
       sys.exit(1)
   print('OK: no keep-list collision')
   " "<pattern>"
   ```
   If this refuses, stop and tell the user why — do not add the pattern anyway.
3. Read `config/debloat_list.txt` and find (or create) the right `# Category`
   comment group for the pattern. Match the existing category naming style —
   don't invent a new category for something that fits an existing one.
4. Add the pattern as a new line under that category, one glob per line.
5. If the package also maps to something in `config/ntlite-presets/*.xml`'s
   `RemoveComponents`, mention that to the user — AGENTS.md notes the presets
   and `debloat_list.txt`/`component_groups.json` are kept in sync manually,
   this skill only writes `debloat_list.txt`.
6. Confirm the AppX keep-list is still intact after the edit (re-run the
   check above, this time as a full-file scan):
   ```bash
   python3 -c "
   import re
   keep = re.compile(r'Store|WebView|VCLibs|UI\.Xaml|Defender|DesktopAppInstaller')
   with open('config/debloat_list.txt', encoding='utf-8') as f:
       bad = [l for l in f if l.strip() and not l.lstrip().startswith('#') and keep.search(l)]
   print('COLLISION:', bad) if bad else print('keep-list intact')
   "
   ```
