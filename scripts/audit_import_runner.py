#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

root = Path('.').resolve()
results = []

for p in sorted(root.rglob('*.py')):
    # skip virtualenvs and git
    if any(part in ('venv', '.venv', '.git', '__pycache__', 'node_modules') for part in p.parts):
        continue
    # skip this runner
    if p.samefile(Path(__file__)):
        continue
    # skip start.py to avoid launching server
    if p.name == 'start.py':
        results.append({'path': str(p), 'ok': True, 'skipped': 'start.py'})
        continue

    cmd = [sys.executable, '-c', (
        "import importlib.util,traceback,sys,os\n"
        f"path={json.dumps(str(p))}\n"
        "try:\n"
        "    spec=importlib.util.spec_from_file_location('tmpmod', path)\n"
        "    mod=importlib.util.module_from_spec(spec)\n"
        "    sys.path.insert(0, os.path.abspath('.'))\n"
        "    spec.loader.exec_module(mod)\n"
        "    logger.info('OK')\n"
        "except Exception:\n"
        "    logger.info('ERR')\n"
        "    import traceback; traceback.print_exc()\n"
    )]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        out = proc.stdout + proc.stderr
        if proc.returncode == 0 and out.strip().startswith('OK'):
            results.append({'path': str(p), 'ok': True})
        else:
            results.append({'path': str(p), 'ok': False, 'output': out.strip()})
    except subprocess.TimeoutExpired:
        results.append({'path': str(p), 'ok': False, 'error': 'timeout'})

outpath = root / 'audit_import_results.json'
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

logger.info('WROTE', outpath)
