#!/usr/bin/env python3
"""Resumable GovInfo BILLS bulk collector -> parquet (bill text versions + sections).

Source: https://www.govinfo.gov/bulkdata/BILLS/{congress}/{session}/{type}/BILLS-{congress}-{session}-{type}.zip
(GovInfo, not the Congress.gov API: does not draw on the shared api.congress.gov hourly budget.)
Raw zips go to --cache (sha256 recorded); one parquet pair + one checkpoint JSON per unit.
Rerun is safe: units with a checkpoint are skipped. Usage:
  collect_bill_text.py --out OUT --cache CACHE [--congress 113 114 ...]
"""
import argparse, hashlib, io, json, re, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
import requests
import pyarrow as pa, pyarrow.parquet as pq
from lxml import etree

TYPES = ['hr', 's', 'hjres', 'sjres', 'hconres', 'sconres', 'hres', 'sres']
UA = 'BetweenTheBills-research/1.0 (public-records research)'
FN = re.compile(r'BILLS-(\d+)([a-z]+?)(\d+)([a-z]+\d*)\.xml$')
DC = '{http://purl.org/dc/elements/1.1/}'

def norm(s): return ' '.join(s.split())

def download(url, dest, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, headers={'User-Agent': UA}, timeout=180, stream=True)
            if r.status_code == 404: return None
            r.raise_for_status()
            tmp = dest.with_suffix('.part'); h = hashlib.sha256()
            with open(tmp, 'wb') as f:
                for ch in r.iter_content(1 << 20): f.write(ch); h.update(ch)
            tmp.replace(dest); return h.hexdigest()
        except Exception as e:
            print('retry', url, e, file=sys.stderr); time.sleep(2 ** i * 2)
    raise RuntimeError('download failed ' + url)

def parse(name, raw, url, congress, session):
    m = FN.search(name)
    if not m: return None
    cong, typ, num, ver = m.groups()
    root = etree.fromstring(raw, parser=etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True, recover=True))
    title = root.findtext(f'.//{DC}title'); date = root.findtext(f'.//{DC}date')
    body = next((c for c in root if isinstance(c.tag, str) and etree.QName(c).localname.endswith('-body')), None)
    official = root.findtext('.//official-title')
    legis = root.findtext('.//legis-num')
    bill_id = f'{cong}-{typ}{num}'
    vid = f'{bill_id}-{ver}'
    full = norm(''.join(body.itertext())) if body is not None else ''
    vrow = dict(version_id=vid, bill_id=bill_id, congress=int(cong), bill_type=typ, bill_number=int(num), version_code=ver,
                stage_attr=root.get('bill-stage') or root.get('resolution-stage') or root.get('amend-stage'),
                dc_title=title, dc_date=date, legis_num=norm(legis or ''), official_title=norm(official or ''),
                session=int(session), word_count=len(full.split()), text_sha256=hashlib.sha256(full.encode()).hexdigest(),
                xml_sha256=hashlib.sha256(raw).hexdigest(), source_url=url, zip_member=name)
    srows = []
    if body is not None:
        secs = [s for s in body.iter('section', 'division', 'title') if etree.QName(s).localname in ('section', 'division', 'title')]
        # leaf-level provisions: top-level sections of the body (not nested subsections)
        top = [s for s in body.iter('section') if not any(etree.QName(a).localname == 'section' for a in s.iterancestors() if a is not body)]
        for i, s in enumerate(top):
            enum = norm(s.findtext('enum') or ''); hdr = norm(s.findtext('header') or '')
            txt = norm(''.join(s.itertext()))
            srows.append(dict(version_id=vid, bill_id=bill_id, section_index=i, section_xml_id=s.get('id'), enum=enum, header=hdr,
                              word_count=len(txt.split()), text_sha256=hashlib.sha256(txt.encode()).hexdigest(), text=txt))
    return vrow, srows

def run_unit(congress, session, typ, out, cache):
    key = f'{congress}-{session}-{typ}'
    ck = out / 'checkpoints' / f'{key}.json'
    if ck.exists(): return json.loads(ck.read_text())
    url = f'https://www.govinfo.gov/bulkdata/BILLS/{congress}/{session}/{typ}/BILLS-{congress}-{session}-{typ}.zip'
    z = cache / f'BILLS-{key}.zip'
    sha = hashlib.sha256(z.read_bytes()).hexdigest() if z.exists() else download(url, z)
    if sha is None:
        meta = dict(unit=key, url=url, status='not_available_404', versions=0, sections=0, retrieved_at=datetime.now(timezone.utc).isoformat())
    else:
        vrows, srows, bad = [], [], []
        with zipfile.ZipFile(z) as zf:
            for n in sorted(zf.namelist()):
                if not n.endswith('.xml'): continue
                try:
                    r = parse(n, zf.read(n), f'https://www.govinfo.gov/content/pkg/{n[:-4]}/xml/{n}', congress, session)
                except Exception as e:
                    bad.append(dict(member=n, error=str(e))); continue
                if r: vrows.append(r[0]); srows += r[1]
        empty = sum(1 for v in vrows if v['word_count'] == 0)
        if vrows and empty > 0.02 * len(vrows):
            raise RuntimeError(f'{key}: {empty}/{len(vrows)} versions parsed with empty body; parser assumption failed')
        d = out / 'tables'; d.mkdir(parents=True, exist_ok=True)
        if vrows:
            pq.write_table(pa.Table.from_pylist(vrows), d / f'bill_text_versions_{key}.parquet', compression='zstd')
            pq.write_table(pa.Table.from_pylist(srows), d / f'bill_text_sections_{key}.parquet', compression='zstd')
        meta = dict(unit=key, url=url, status='ok', zip_sha256=sha, zip_bytes=z.stat().st_size, versions=len(vrows),
                    sections=len(srows), parse_errors=bad, retrieved_at=datetime.now(timezone.utc).isoformat())
    ck.parent.mkdir(parents=True, exist_ok=True)
    tmp = ck.with_suffix('.tmp'); tmp.write_text(json.dumps(meta, indent=1)); tmp.replace(ck)
    if not meta.get('keep_zip', False) and z.exists() and meta['status'] == 'ok': z.unlink()  # raw is re-downloadable; sha256 kept in checkpoint
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--cache', required=True)
    ap.add_argument('--congress', nargs='+', type=int, default=[119, 118, 117, 116, 115, 114, 113])
    ap.add_argument('--keep-zips', action='store_true')
    a = ap.parse_args(); out, cache = Path(a.out), Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    for c in a.congress:
        for s in (1, 2):
            for t in TYPES:
                m = run_unit(c, s, t, out, cache)
                print(m['unit'], m['status'], m['versions'], m['sections'], len(m.get('parse_errors', [])), flush=True)

if __name__ == '__main__': main()
