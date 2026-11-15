#!/usr/bin/env python3
"""Resumable GovInfo PLAW bulk collector (USLM XML, public laws 113th+) -> parquet.
Zip: https://www.govinfo.gov/bulkdata/PLAW/{congress}/public/PLAW-{congress}-public.zip
Outputs law_texts and law_sections parquet plus checkpoint per Congress (zip sha256, counts).
"""
import argparse, hashlib, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
import zipfile, requests
import pyarrow as pa, pyarrow.parquet as pq
from lxml import etree
sys.path.insert(0, str(Path(__file__).parent))
from collect_bill_text import download, norm

U = '{http://schemas.gpo.gov/xml/uslm}'
DC = '{http://purl.org/dc/elements/1.1/}'

def parse(name, raw, url, congress):
    m = re.search(r'PLAW-(\d+)publ(\d+)\.xml$', name)
    if not m: return None
    root = etree.fromstring(raw, parser=etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True, recover=True))
    meta = root.find(U + 'meta')
    main = root.find(U + 'main')
    law_id = f'{m[1]}-pl-{int(m[2])}'
    full = norm(''.join(main.itertext())) if main is not None else ''
    stat = [c.text for c in meta.findall(U + 'citableAs')] if meta is not None else []
    row = dict(law_id=law_id, congress=int(m[1]), law_number=int(m[2]), title=(meta.findtext(DC + 'title') if meta is not None else None),
               approved_date=(meta.findtext(U + 'approvedDate') if meta is not None else None), citations='; '.join(c for c in stat if c),
               word_count=len(full.split()), text_sha256=hashlib.sha256(full.encode()).hexdigest(),
               xml_sha256=hashlib.sha256(raw).hexdigest(), source_url=url, zip_member=name)
    srows = []
    if main is not None:
        top = [s for s in main.iter(U + 'section')
               if not any(etree.QName(a).localname in ('section', 'quotedContent', 'quotedText') for a in s.iterancestors())]
        for i, s in enumerate(top):
            txt = norm(''.join(s.itertext()))
            srows.append(dict(law_id=law_id, section_index=i, section_xml_id=s.get('identifier') or s.get('id'),
                              enum=norm(s.findtext(U + 'num') or ''), header=norm(s.findtext(U + 'heading') or ''),
                              word_count=len(txt.split()), text_sha256=hashlib.sha256(txt.encode()).hexdigest(), text=txt))
    return row, srows

def run(congress, out, cache):
    ck = out / 'checkpoints' / f'plaw-{congress}.json'
    if ck.exists(): return json.loads(ck.read_text())
    url = f'https://www.govinfo.gov/bulkdata/PLAW/{congress}/public/PLAW-{congress}-public.zip'
    z = cache / f'PLAW-{congress}.zip'
    sha = hashlib.sha256(z.read_bytes()).hexdigest() if z.exists() else download(url, z)
    if sha is None:
        meta = dict(unit=f'plaw-{congress}', status='not_available_404', laws=0, sections=0, url=url)
    else:
        rows, srows, bad = [], [], []
        with zipfile.ZipFile(z) as zf:
            for n in sorted(zf.namelist()):
                if not n.endswith('.xml'): continue
                try:
                    r = parse(n, zf.read(n), f'https://www.govinfo.gov/content/pkg/{n[:-4]}/xml/{n}', congress)
                except Exception as e:
                    bad.append(dict(member=n, error=str(e))); continue
                if r: rows.append(r[0]); srows += r[1]
        empty = sum(1 for r in rows if r['word_count'] == 0)
        if rows and empty > 0.02 * len(rows): raise RuntimeError(f'{congress}: {empty}/{len(rows)} laws empty')
        d = out / 'tables'; d.mkdir(parents=True, exist_ok=True)
        if rows:
            pq.write_table(pa.Table.from_pylist(rows), d / f'law_texts_{congress}.parquet', compression='zstd')
            pq.write_table(pa.Table.from_pylist(srows), d / f'law_sections_{congress}.parquet', compression='zstd')
        meta = dict(unit=f'plaw-{congress}', status='ok', url=url, zip_sha256=sha, zip_bytes=z.stat().st_size, laws=len(rows),
                    sections=len(srows), parse_errors=bad, retrieved_at=datetime.now(timezone.utc).isoformat())
    ck.parent.mkdir(parents=True, exist_ok=True)
    t = ck.with_suffix('.tmp'); t.write_text(json.dumps(meta, indent=1)); t.replace(ck)
    return meta

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--cache', required=True)
    ap.add_argument('--congress', nargs='+', type=int, default=[118, 117, 116, 115, 114, 113, 119])
    a = ap.parse_args(); out, cache = Path(a.out), Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    for c in a.congress:
        m = run(c, out, cache); print(m['unit'], m['status'], m['laws'], m['sections'], len(m.get('parse_errors', [])), flush=True)
