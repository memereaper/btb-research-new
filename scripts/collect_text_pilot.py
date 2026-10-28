#!/usr/bin/env python3
"""Transparent, deterministic pilot of source-linked standalone/enacted bill passages."""
import argparse,collections,csv,hashlib,json,os,re,shutil,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import duckdb
from collect_pathways import fetch,atomic_json,export_tables
from build_historical import ROOT,digest

def sections(raw,source):
    root=ET.fromstring(raw);out=[]
    for x in root.iter():
        if x.tag.split('}')[-1]!='section':continue
        value=' '.join(' '.join(x.itertext()).split());tokens=re.findall(r'[a-z0-9]+',value.lower())
        if len(tokens)<80:continue
        ordinal=len(out)+1
        shingles={' '.join(tokens[i:i+5]) for i in range(len(tokens)-4)}
        row={'section_id':source['sha256']+':'+str(ordinal),'source_id':source['sha256'],'source_url':source['url'],'section_ordinal':ordinal,'xml_section_id':x.get('id',''),'word_count':len(tokens),'text':value}
        out.append((row,shingles))
    return out

def collect(status,output,refresh=False):
    c=duckdb.connect()
    for t in ['bills','related_bills','text_versions']:c.read_parquet(str(Path(status)/'tables'/(t+'.parquet'))).create_view(t)
    pairs=c.execute("""SELECT DISTINCT r.bill_id,r.related_bill_id,r.relationship FROM related_bills r JOIN bills a ON a.bill_id=r.bill_id JOIN bills b ON b.bill_id=r.related_bill_id WHERE a.congress='118' AND b.congress='118' AND a.law_identifiers='' AND b.law_identifiers<>'' AND r.relationship IN ('Identical bill','Related bill') QUALIFY row_number() OVER (PARTITION BY r.relationship ORDER BY r.bill_id,r.related_bill_id)<=12 ORDER BY relationship,bill_id,related_bill_id""").fetchall()
    target=Path(output)
    if target.exists():raise ValueError('Choose a new immutable output name')
    work=Path(tempfile.mkdtemp(prefix='.textpilot-',dir=target.parent));stage=work/'staging';stage.mkdir();(work/'tables').mkdir();documents={};all_sections={};matches=[];pairrows=[];failures=[]
    try:
        for left,right,relationship in pairs:
            urls=[]
            for bid,role in [(left,'introduced'),(right,'enrolled')]:
                patterns=['%ih.xml','%is.xml'] if role=='introduced' else ['%enr.xml']
                options=c.execute('SELECT DISTINCT url FROM text_versions WHERE bill_id=? AND ('+' OR '.join('url LIKE ?' for _ in patterns)+') ORDER BY url',[bid]+patterns).fetchall()
                if not options:urls=[];failures.append({'bill_id':bid,'reason':'No requested XML text version URL'});break
                url=options[0][0]
                if url not in documents:
                    try:
                        p,m=fetch(url,refresh);parsed=sections(p.read_bytes(),m)
                        documents[url]={'meta':m,'sections':parsed}
                        for row,shingles in parsed:all_sections[row['section_id']]=row
                    except Exception as e:
                        failures.append({'url':url,'error':str(e)});urls=[];break
                urls.append(url)
            if len(urls)!=2:continue
            pairrows.append({'source_bill_id':left,'enacted_bill_id':right,'official_relationship':relationship,'source_url':urls[0],'enacted_url':urls[1],'source_eligible_sections':len(documents[urls[0]]['sections']),'enacted_eligible_sections':len(documents[urls[1]]['sections']),'comparison_status':'eligible' if documents[urls[0]]['sections'] and documents[urls[1]]['sections'] else 'no_section_meets_80_word_minimum'})
            targets=documents[urls[1]]['sections']
            if not targets:continue
            for section,words in documents[urls[0]]['sections']:
                scored=[(len(words&other)/len(words),len(words&other),row) for row,other in targets]
                score,shared,best=max(scored,key=lambda x:(x[0],x[1],x[2]['section_id']))
                if score>=0.5 and shared>=20:
                    matches.append({'source_bill_id':left,'enacted_bill_id':right,'source_section_id':section['section_id'],'enacted_section_id':best['section_id'],'source_shingle_containment':score,'shared_unique_5grams':shared,'label':'unreviewed lexical candidate; not proof of incorporation or influence'})
            print('Compared source-linked pair',left,right,flush=True)
        for name,rows in [('text_sections',list(all_sections.values())),('text_pairs',pairrows),('passage_candidates',matches)]:
            if not rows:continue
            with (stage/(name+'.csv')).open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        db,catalog=export_tables(stage,work/'tables');db.close();c.close();shutil.rmtree(stage)
        atomic_json(work/'catalog.json',{'scope':'Deterministic first 12 Identical bill and first 12 Related bill relationships (lexicographic bill-ID order) from non-enacted 118th vehicles to enacted 118th vehicles, with available introduced and enrolled XML. This is a feasibility pilot, not a random or representative sample.','selection_pairs':len(pairs),'acquired_pairs':len(pairrows),'documents':len(documents),'tables':catalog,'sources':[x['meta'] for x in documents.values()],'failures':failures,'method':'Lowercase word/number tokens; unique 5-word shingles per XML section with at least 80 tokens. Keep the best enrolled-section match when at least 20 shingles and 50% source containment match. Shared boilerplate can trigger candidates. Long sections may hide short surviving provisions. No human-reviewed labels or causal claims.'})
        atomic_json(work/'validation.json',{'checks':{'all_texts_parse':True,'all_requested_pairs_acquired':len(pairs)==len(pairrows)},'analytical_status':'unreviewed candidate matches only'})
        atomic_json(work/'package.json',{'files':[{'path':str(p.relative_to(work)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(work.rglob('*')) if p.is_file()]});os.rename(work,target)
        print('Text pilot:',len(pairrows),'pairs,',len(documents),'documents,',len(matches),'unreviewed passage candidates',flush=True)
    except BaseException:shutil.rmtree(work,ignore_errors=True);raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--status',type=Path,default=ROOT/'datasets/pathways-2026-10-28');p.add_argument('--output',type=Path,default=ROOT/'datasets/text-survival-pilot-2026-10-28');p.add_argument('--refresh',action='store_true');a=p.parse_args();collect(a.status,a.output,a.refresh)
