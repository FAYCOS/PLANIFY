#!/usr/bin/env python3
"""Script d'automatisation : remplace les appels print() par logger.*

Usage: python3 tools/replace_prints.py
Il sauvegarde chaque fichier modifié avec suffixe .bak
"""
import re
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

py_files = list(ROOT.rglob('*.py'))

def choose_level(s):
    s_lower = s.lower()
    if 'error' in s_lower or 'erreur' in s_lower or '❌' in s:
        return 'error'
    if 'warn' in s_lower or '⚠' in s or 'attention' in s_lower:
        return 'warning'
    if 'password' in s_lower or 'mot de passe' in s_lower:
        return 'warning'
    return 'info'

def main():
for p in py_files:
    # skip tools folder
    if 'tools' in p.parts:
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue

    orig = text

    # simple heuristic: only replace top-level print( occurrences, skip in tests or docs by file name
    if p.name.startswith('test_'):
        continue

    changed = False

    # ensure logger import
    if 'logger =' not in text and 'import logging' not in text:
        # place after first block of imports
        parts = text.split('\n')
        insert_at = 0
        for i, line in enumerate(parts):
            if line.strip().startswith('import') or line.strip().startswith('from'):
                insert_at = i+1
        parts.insert(insert_at, 'import logging')
        parts.insert(insert_at+1, "logger = logging.getLogger(__name__)")
        text = '\n'.join(parts)
        changed = True

    # replace print(...) -> logger.<level>(...)
    def repl(match):
        inner = match.group(1)
        lvl = choose_level(inner)
        return f"logger.{lvl}({inner})"

    # regex to match print( ... ) non-greedy across single line
    new_text, n = re.subn(r"print\(([^\n]*)\)", repl, text)
    if n > 0:
        text = new_text
        changed = True

    if changed and text != orig:
        bak = p.with_suffix(p.suffix + '.bak')
        p.rename(bak)
        p.write_text(text, encoding='utf-8')
        print(f"Patched: {p} (backup: {bak.name})")

if __name__ == '__main__':
    main()
    print('Done')
