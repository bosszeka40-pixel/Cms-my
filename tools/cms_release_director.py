#!/usr/bin/env python3
"""CMS Release Director: evidence-based validation gate.

This tool reviews generated diagnostics and repository state. It NEVER edits
source code, merges PRs, enables LIVE trading, or silently approves failures.
It returns APPROVED only when all mandatory gates are explicitly satisfied.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REQUIRED = [
    ('compile', 'docs/COMPILE_REPORT.json'),
    ('request_map', 'docs/REQUEST_MAP.json'),
    ('template_audit', 'docs/TEMPLATE_DESIGN_AUDIT.json'),
]

def load(root, path):
    p=root/path
    if not p.exists(): return None
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return None

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
    reasons=[]; gates={}
    for name,path in REQUIRED:
        data=load(root,Path(path))
        gates[name]=bool(data)
        if not data: reasons.append(f'Missing or invalid {path}')
    c=load(root,Path('docs/COMPILE_REPORT.json'))
    if c:
        if c.get('summary',{}).get('syntax_errors',0): reasons.append('Python syntax errors remain')
        if c.get('tests',{}).get('status') != 'passed': reasons.append('Tests are not proven passing')
    audit=load(root,Path('docs/TEMPLATE_DESIGN_AUDIT.json'))
    if audit and audit.get('critical_gaps'): reasons.append('Critical template/function gaps remain')
    result={'decision':'APPROVED' if not reasons else 'HOLD','gates':gates,'reasons':reasons,'live_trading':False,'source_changes':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    (root/'docs'/'RELEASE_DIRECTOR_REPORT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md=['# CMS Release Director Report','','Decision: **'+result['decision']+'**','','## Gates']
    for k,v in gates.items(): md.append(f'- {k}: {"PASS" if v else "MISSING"}')
    md += ['', '## Blocking reasons']
    md += [f'- {r}' for r in reasons] or ['- None']
    md += ['', '## Safety', '- LIVE trading remains disabled.', '- This director never modifies source code or merges changes.', '- Approval means the evidence gates passed; it is not a financial/trading guarantee.']
    (root/'docs'/'RELEASE_DIRECTOR_REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    raise SystemExit(0 if not reasons else 2)

if __name__=='__main__': main()
