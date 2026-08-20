#!/usr/bin/env python3
"""Read-only CMS inspector.

Independent inspection layer: correlates diagnostics and reports findings,
without modifying source, dependencies, databases, credentials, or trading.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

CRITICAL_KEYS=('syntax','security','private','credential','secret','order','kill-switch','failed')

def read_json(p):
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception as e: return {'_read_error':str(e)}

def inspect(root):
    docs=root/'docs'
    files={n:read_json(docs/n) for n in ('COMPILE_REPORT.json','REQUEST_MAP.json','TEMPLATE_DESIGN_AUDIT.json') if (docs/n).exists()}
    findings=[]
    compile_report=files.get('COMPILE_REPORT.json',{})
    if compile_report.get('summary',{}).get('syntax_errors',0): findings.append(('critical','syntax errors detected'))
    if compile_report.get('tests',{}).get('status')=='failed': findings.append(('high','test suite failed'))
    for name,data in files.items():
        raw=json.dumps(data,ensure_ascii=False).lower()
        for key in CRITICAL_KEYS:
            if key in raw: findings.append(('review',f'{name}: contains indicator {key!r}; verify context'))
    return {'read_only':True,'sources':list(files),'findings':findings,'status':'HOLD' if any(x[0] in ('critical','high') for x in findings) else 'REVIEW'}

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); docs=root/'docs'; docs.mkdir(exist_ok=True)
    report=inspect(root)
    (docs/'INSPECTOR_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# CMS Inspector Report','','Read-only independent inspection.','',f"**Status:** {report['status']}",'', '## Findings']
    lines += [f'- **{sev.upper()}** — {msg}' for sev,msg in report['findings']] or ['- No findings from available reports.']
    lines += ['', '## Rule', 'Inspector does not modify code, install packages, change databases, or execute trades.']
    (docs/'INSPECTOR_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
