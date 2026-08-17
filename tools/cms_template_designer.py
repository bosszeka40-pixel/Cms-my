#!/usr/bin/env python3
"""Read-only template/function coverage auditor.

Builds a design-oriented inventory of template capabilities and compares
frontend template references with backend routes/static assets. It reports
missing or suspicious coverage; it does not modify application files.
"""
from __future__ import annotations
import json,re,sys
from pathlib import Path

SKIP={'.git','.venv','venv','node_modules','__pycache__','.pytest_cache'}
ROUTE=re.compile(r'@(?:app|router)\.(get|post|put|patch|delete|websocket)\s*\(\s*["\']([^"\']+)',re.I)
FETCH=re.compile(r'(?:fetch|axios\.(?:get|post|put|patch|delete))\s*\(\s*[`"\']([^`"\']+)',re.I)
TEMPLATE=re.compile(r'\{\{\s*([^}]+?)\s*\}\}|\{%\s*([^%]+?)\s*%\}')

def files(root,exts):
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in exts and not any(x in SKIP for x in p.parts): yield p

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
    routes=[]; calls=[]; templates=[]; assets=[]
    for p in files(root,{'.py'}):
        text=p.read_text(encoding='utf-8',errors='replace')
        for m in ROUTE.finditer(text): routes.append({'method':m.group(1).upper(),'path':m.group(2),'file':p.relative_to(root).as_posix()})
    for p in files(root,{'.html','.htm','.js','.ts','.tsx','.jsx'}):
        text=p.read_text(encoding='utf-8',errors='replace')
        for m in FETCH.finditer(text): calls.append({'path':m.group(1),'file':p.relative_to(root).as_posix()})
        for m in TEMPLATE.finditer(text): templates.append({'file':p.relative_to(root).as_posix(),'reference':(m.group(1) or m.group(2)).strip()})
    for p in files(root,{'.css','.scss','.png','.jpg','.jpeg','.svg','.webp','.ico','.woff','.woff2'}): assets.append(p.relative_to(root).as_posix())
    route_paths={r['path'] for r in routes}; call_paths={c['path'] for c in calls}
    suspicious=[c for c in calls if c['path'].startswith('/api/') and c['path'] not in route_paths]
    capability_terms=['chart','candlestick','order','position','portfolio','balance','market','strategy','signal','ai','memory','risk','history','settings','admin','auth','notification','websocket']
    capability_hits={term:[] for term in capability_terms}
    for p in list(files(root,{'.html','.htm','.js','.ts','.tsx','.jsx'})):
        text=p.read_text(encoding='utf-8',errors='replace').lower(); rel=p.relative_to(root).as_posix()
        for term in capability_terms:
            if term in text: capability_hits[term].append(rel)
    report={'read_only':True,'routes':routes,'frontend_calls':calls,'template_references':templates,'assets':assets,'suspicious_api_calls':suspicious,'capability_coverage':capability_hits}
    docs=root/'docs'; docs.mkdir(exist_ok=True)
    (docs/'TEMPLATE_DESIGN_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md=['# CMS Template / Function Coverage Audit','', 'Read-only inventory. No application files are modified.','',f'- Backend routes: **{len(routes)}**',f'- Frontend API calls: **{len(calls)}**',f'- Template references: **{len(templates)}**',f'- Static/design assets: **{len(assets)}**','', '## Suspicious frontend API calls']
    if suspicious:
        md += [f"- `{x['path']}` — `{x['file']}`" for x in suspicious]
    else: md.append('None detected by static comparison.')
    md += ['', '## Capability coverage']
    for k,v in capability_hits.items(): md.append(f"- **{k}**: {len(v)} matching file(s)")
    md += ['', '## Intended audit scope','- Verify every module capability has an appropriate UI surface.','- Verify charts/candles/live mode are actually wired to data.','- Verify order/position/risk controls match backend permissions.','- Verify AI signals, memory, strategy and learning surfaces are present.','- Verify settings/auth/admin controls are not exposed to ordinary users.','- Flag missing or orphaned UI without guessing implementation.']
    (docs/'TEMPLATE_DESIGN_AUDIT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(f'Routes={len(routes)} API calls={len(calls)} suspicious={len(suspicious)} assets={len(assets)}')
if __name__=='__main__': main()
