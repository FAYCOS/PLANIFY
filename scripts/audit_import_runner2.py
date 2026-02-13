#!/usr/bin/env python3
import os,sys,json,subprocess
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
root=Path('.').resolve()
results=[]
for p in sorted(root.rglob('*.py')):
    if any(part in ('venv','.venv','.git','__pycache__','node_modules') for part in p.parts):
        continue
    if p.name=='start.py' or p.name=='run.py' or p.name=='run_production.py':
        results.append({'path':str(p),'ok':True,'skipped':p.name})
        continue
    text=p.read_text(encoding='utf-8')
    if "if __name__ == '__main__'" in text or 'app.run(' in text or 'serve(' in text:
        results.append({'path':str(p),'ok':True,'skipped':'has_main_or_run'})
        continue
    cmd=[sys.executable,'-c', (
        "import importlib.util,traceback,sys,os,logging\n"
        "logger = logging.getLogger('tmp_audit')\n"
        "# Allow empty logger.info() calls during audit by monkeypatching\n"
        "_orig_info = logging.Logger.info\n"
        "def _info(self, msg='', *args, **kwargs):\n"
        "    return _orig_info(self, msg, *args, **kwargs)\n"
        "logging.Logger.info = _info\n"
        f"path={json.dumps(str(p))}\n"
        "try:\n"
        "    spec=importlib.util.spec_from_file_location('tmpmod', path)\n"
        "    mod=importlib.util.module_from_spec(spec)\n"
        "    sys.path.insert(0, os.path.abspath('.'))\n"
        "    spec.loader.exec_module(mod)\n"
        "    logger.info('OK')\n"
        "    print('OK')\n"
        "except Exception:\n"
        "    logger.info('ERR')\n"
        "    print('ERR')\n"
        "    import traceback; traceback.print_exc()\n"
    )]
    try:
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=5)
        out=proc.stdout+proc.stderr
        if proc.returncode==0 and out.strip().startswith('OK'):
            results.append({'path':str(p),'ok':True})
        else:
            results.append({'path':str(p),'ok':False,'output':out.strip()})
    except subprocess.TimeoutExpired:
        results.append({'path':str(p),'ok':False,'error':'timeout'})

outpath=root/ 'audit_import_results2.json'
with open(outpath,'w',encoding='utf-8') as f:
    json.dump(results,f,ensure_ascii=False,indent=2)
logger.info('WROTE', outpath)
