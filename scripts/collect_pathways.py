#!/usr/bin/env python3
"""Resumable primary-source acquisition for legislative pathways, not inferred causation."""
import argparse,collections,csv,hashlib,json,os,re,shutil,subprocess,tempfile,time,zipfile
from datetime import datetime,timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import duckdb
from build_historical import ROOT,digest,quote
csv.field_size_limit(16*1024*1024)
CACHE=ROOT/'warehouse/collection-cache'
LAST={}
def now():return datetime.now(timezone.utc).isoformat()
def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2,default=str)+'\n');os.replace(temporary,path)
def fetch(url,refresh=False):
    key=hashlib.sha256(url.encode()).hexdigest();meta=CACHE/'urls'/(key+'.json')
    if meta.exists() and not refresh:
        m=json.loads(meta.read_text());p=CACHE/'objects'/m['sha256']
        if p.is_file() and digest(p)==m['sha256']:return p,m
    from urllib.parse import urlsplit
    host=urlsplit(url).netloc
    time.sleep(max(0,0.6-(time.monotonic()-LAST.get(host,0))))
    pending=CACHE/'pending';pending.mkdir(parents=True,exist_ok=True)
    part=pending/key;headers=pending/(key+'.headers')
    # curl uses the Mac's trusted certificates. No TLS verification is disabled.
    command=['curl','--fail','--location','--silent','--show-error','--retry','4','--retry-delay','2','--connect-timeout','20','--max-time','180','--dump-header',str(headers),'--output',str(part),url]
    for attempt in range(3):
        result=subprocess.run(command,capture_output=True,text=True)
        if result.returncode not in (35,56) or attempt==2:break
        time.sleep(1+attempt)
    LAST[host]=time.monotonic()
    if result.returncode:raise RuntimeError(url+': '+result.stderr.strip())
    sha=digest(part);p=CACHE/'objects'/sha;p.parent.mkdir(exist_ok=True)
    if p.exists():part.unlink()
    else:os.replace(part,p)
    m={'url':url,'retrieved_utc':now(),'sha256':sha,'bytes':p.stat().st_size,'response_headers':headers.read_text(errors='replace')}
    atomic_json(meta,m);return p,m

def text(node,path):return (node.findtext(path) or '').strip() if node is not None else ''
def bill_id(congress,typ,number):return f'{congress}-{typ.lower()}{number}'
def parse_bill(raw,archive_sha,member):
    b=ET.fromstring(raw).find('bill')
    if b is None:raise ValueError('No bill element: '+member)
    c=text(b,'congress');typ=text(b,'type') or text(b,'billType');num=text(b,'number') or text(b,'billNumber')
    if not(c and typ and num):raise ValueError('Missing bill identity')
    bid=bill_id(c,typ,num)
    provenance={'source_id':archive_sha,'source_member':member,'source_record_sha256':hashlib.sha256(raw).hexdigest()}
    sp=b.find('sponsors/item');latest=b.find('latestAction')
    rows=collections.defaultdict(list)
    def add(table,row):rows[table].append({**row,**provenance})
    add('bills',{'bill_id':bid,'congress':int(c),'bill_type':typ.lower(),'bill_number':int(num),'title':text(b,'title'),'introduced_date':text(b,'introducedDate'),'updated_at':text(b,'updateDate'),'updated_including_text':text(b,'updateDateIncludingText'),'origin_chamber':text(b,'originChamber'),'policy_area':text(b,'policyArea/name') or text(b,'subjects/policyArea/name'),'sponsor_id':text(sp,'bioguideId'),'sponsor_name':text(sp,'fullName'),'sponsor_party':text(sp,'party'),'sponsor_state':text(sp,'state'),'sponsor_district':text(sp,'district'),'latest_action_date':text(latest,'actionDate'),'latest_action_text':text(latest,'text'),'law_identifiers':';'.join(text(x,'type')+' '+text(x,'congress')+'-'+text(x,'number') for x in b.findall('laws/item')),'congress_url':text(b,'legislationUrl'),'source_xml_url':f'https://www.govinfo.gov/content/pkg/BILLSTATUS-{c}{typ.lower()}{num}/xml/BILLSTATUS-{c}{typ.lower()}{num}.xml'})
    for i,x in enumerate(b.findall('cosponsors/item'),1):
        add('cosponsors',{'bill_id':bid,'sponsor_id':text(x,'bioguideId'),'member_name':text(x,'fullName'),'party':text(x,'party'),'state':text(x,'state'),'district':text(x,'district'),'joined_date':text(x,'sponsorshipDate'),'withdrawn_date':text(x,'sponsorshipWithdrawnDate'),'is_original':text(x,'isOriginalCosponsor'),'source_row':i})
    for i,x in enumerate(b.findall('actions/item'),1):
        aid=f'{bid}:a{i}'
        add('actions',{'action_id':aid,'bill_id':bid,'action_date':text(x,'actionDate'),'action_time':text(x,'actionTime'),'action_code':text(x,'actionCode'),'action_type':text(x,'type'),'action_text':text(x,'text'),'source_system':text(x,'sourceSystem/name'),'source_order':i})
        for j,v in enumerate(x.findall('recordedVotes/recordedVote'),1):
            add('vote_references',{'bill_id':bid,'action_id':aid,'chamber':text(v,'chamber'),'congress':text(v,'congress'),'session':text(v,'sessionNumber'),'roll_number':text(v,'rollNumber'),'vote_date':text(v,'date'),'url':text(v,'url'),'source_row':j})
    for x in b.findall('committees/item'):
        cid=text(x,'systemCode')
        add('committees',{'bill_id':bid,'committee_id':cid,'committee_name':text(x,'name'),'chamber':text(x,'chamber'),'committee_type':text(x,'type')})
        for a in x.findall('activities/item'):
            add('committee_events',{'bill_id':bid,'committee_id':cid,'parent_committee_id':'','event_name':text(a,'name'),'event_date':text(a,'date')})
        for sub in x.findall('subcommittees/item'):
            for a in sub.findall('activities/item'):
                add('committee_events',{'bill_id':bid,'committee_id':text(sub,'systemCode'),'parent_committee_id':cid,'event_name':text(a,'name'),'event_date':text(a,'date')})
    for x in b.findall('relatedBills/item'):
        for rel in x.findall('relationshipDetails/item') or [None]:
            add('related_bills',{'bill_id':bid,'related_bill_id':bill_id(text(x,'congress'),text(x,'type'),text(x,'number')),'relationship':text(rel,'type'),'identified_by':text(rel,'identifiedBy'),'latest_action_date':text(x,'latestAction/actionDate'),'latest_action_text':text(x,'latestAction/text')})
    for x in b.findall('textVersions/item'):
        for f in x.findall('formats/item'):
            add('text_versions',{'bill_id':bid,'version_type':text(x,'type'),'version_date':text(x,'date'),'format_type':text(f,'type'),'url':text(f,'url'),'is_errata':text(f,'isErrata')})
    for x in b.findall('cboCostEstimates/item'):
        add('cbo_estimates',{'bill_id':bid,'title':text(x,'title'),'publication_date':text(x,'pubDate'),'url':text(x,'url'),'description':text(x,'description')})
    for x in b.findall('subjects/legislativeSubjects/item'):
        add('subjects',{'bill_id':bid,'subject':text(x,'name'),'updated_at':text(x,'updateDate')})
    for x in b.findall('summaries/summary'):
        add('summaries',{'bill_id':bid,'action_date':text(x,'actionDate'),'action_description':text(x,'actionDesc'),'version_code':text(x,'versionCode'),'updated_at':text(x,'updateDate'),'summary_html':text(x,'text')})
    return rows

def acquire(congresses,refresh=False):
    manifest=[]
    for c in congresses:
        for typ in ['hr','s','hjres','sjres']:
            url=f'https://www.govinfo.gov/bulkdata/BILLSTATUS/{c}/{typ}/BILLSTATUS-{c}-{typ}.zip'
            path,m=fetch(url,refresh)
            with zipfile.ZipFile(path) as z:
                bad=z.testzip()
                if bad:raise ValueError('ZIP corruption '+bad)
                count=sum(x.endswith('.xml') for x in z.namelist())
            manifest.append({**m,'kind':'billstatus','congress':c,'bill_type':typ,'xml_members':count})
            print('Acquired',c,typ,count,'XML records',flush=True)
    atomic_json(CACHE/'acquisition.json',{'started_scope':congresses,'sources':manifest})
    return manifest

def export_tables(csvdir,out):
    c=duckdb.connect();c.execute("SET memory_limit='1GB'")
    catalog=[]
    for p in sorted(csvdir.glob('*.csv')):
        table=p.stem
        options = "header=true,all_varchar=true,delim=',',quote='\"',escape='\"',nullstr='__BTB_RESERVED_NULL__'"
        c.execute(f'CREATE TABLE "{table}" AS SELECT * FROM read_csv({quote(p)},{options})')
        c.execute(f'COPY (SELECT * FROM "{table}" ORDER BY ALL) TO {quote(out/(table+".parquet"))} (FORMAT PARQUET,COMPRESSION ZSTD)')
        with p.open(encoding='utf-8',newline='') as f:
            reader=csv.reader(f);next(reader);expected=sum(1 for _ in reader)
        actual=c.execute(f'SELECT count(*) FROM \"{table}\"').fetchone()[0]
        if actual!=expected:raise ValueError('Independent CSV row count mismatch: '+table)
        catalog.append({'table':table,'rows':c.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0],'fields':[d[0] for d in c.execute(f'SELECT * FROM "{table}" LIMIT 0').description]})
    return c,catalog

def build(manifest,output):
    target=Path(output)
    if target.exists():raise ValueError('Output exists; choose a new release name')
    target.parent.mkdir(exist_ok=True,parents=True)
    work=Path(tempfile.mkdtemp(prefix='.pathways-',dir=target.parent));csvdir=work/'staging';csvdir.mkdir();core=work/'tables';core.mkdir()
    writers={};handles={};xml_counts={};source_list=[]
    try:
        for source in manifest:
            sha=source['sha256'];p=CACHE/'objects'/sha
            if digest(p)!=sha:raise ValueError('Source hash mismatch')
            count=0
            with zipfile.ZipFile(p) as z:
                for member in sorted(z.namelist()):
                    if not member.endswith('.xml'):continue
                    rows=parse_bill(z.read(member),sha,member);count+=1
                    for table,records in rows.items():
                        for row in records:
                            if table not in writers:
                                handles[table]=(csvdir/(table+'.csv')).open('w',encoding='utf-8',newline='');writers[table]=csv.DictWriter(handles[table],fieldnames=list(row));writers[table].writeheader()
                            writers[table].writerow(row)
            xml_counts[f"{source['congress']}-{source['bill_type']}"]=count;source_list.append(source)
        for f in handles.values():f.close()
        c,catalog=export_tables(csvdir,core)
        checks={}
        checks['source_xml_equals_bills']=c.execute('SELECT count(*) FROM bills').fetchone()[0]==sum(xml_counts.values())
        checks['unique_bill_ids']=c.execute('SELECT count(*)=count(DISTINCT bill_id) FROM bills').fetchone()[0]
        checks['unique_action_ids']=c.execute('SELECT count(*)=count(DISTINCT action_id) FROM actions').fetchone()[0]
        for t in ['cosponsors','actions','committees','committee_events','related_bills','text_versions','cbo_estimates','subjects','summaries','vote_references']:
            if (core/(t+'.parquet')).exists():checks[t+'_bill_links']=c.execute(f'SELECT count(*) FROM {t} x ANTI JOIN bills b USING(bill_id)').fetchone()[0]==0
        checks['valid_introduction_dates']=c.execute("SELECT count(*) FROM bills WHERE try_cast(introduced_date AS DATE) IS NULL").fetchone()[0]==0
        checks['valid_cosponsor_dates']=c.execute("SELECT count(*) FROM cosponsors WHERE joined_date<>'' AND try_cast(joined_date AS DATE) IS NULL").fetchone()[0]==0
        if not all(checks.values()):raise ValueError('Validation failed '+str(checks))
        missing={'cosponsor_member_ids':c.execute("SELECT count(*) FROM cosponsors WHERE sponsor_id=''").fetchone()[0],'sponsor_ids':c.execute("SELECT count(*) FROM bills WHERE sponsor_id=''").fetchone()[0],'related_bills_outside_scope':c.execute('SELECT count(*) FROM related_bills r ANTI JOIN bills b ON r.related_bill_id=b.bill_id').fetchone()[0]}
        atomic_json(work/'catalog.json',{'scope':xml_counts,'tables':catalog,'sources':source_list,'collected_utc':now(),'status':'official source fields; relationships are source assertions, not proof of policy influence'})
        atomic_json(work/'validation.json',{'checks':checks,'missingness':missing})
        c.close();shutil.rmtree(csvdir)
        atomic_json(work/'package.json',{'files':[{'path':str(p.relative_to(work)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(work.rglob('*')) if p.is_file()]})
        os.rename(work,target);print('Built',target,flush=True)
    except BaseException:
        for f in handles.values():f.close()
        shutil.rmtree(work,ignore_errors=True);raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--congress',type=int,nargs='+',default=[118,119]);p.add_argument('--refresh',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'datasets/pathways-2026-10-28');a=p.parse_args()
    build(acquire(a.congress,a.refresh),a.output)
