#!/usr/bin/env python3
"""Acquire every unique 2024 House roll call referenced by the new bill-status snapshot."""
import argparse,collections,csv,json,os,re,shutil,tempfile
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
import duckdb
from build_historical import ROOT,digest
from collect_pathways import fetch,atomic_json,text,export_tables

def parse_vote(raw,source):
    root=ET.fromstring(raw);m=root.find('vote-metadata');c=text(m,'congress');session=text(m,'session');number=text(m,'rollcall-num')
    vid=f'house-{c}-{session}-{number}'
    measure=text(m,'legis-num');match=re.fullmatch(r'(H\s*R|S|H\s*J\s*RES|S\s*J\s*RES)\s*(\d+)',measure,re.I)
    bid=c+'-'+re.sub(r'\s','',match[1]).lower()+match[2] if match else ''
    expected={k:int(text(m,'vote-totals/totals-by-vote/'+tag) or 0) for k,tag in [('yea','yea-total'),('nay','nay-total'),('present','present-total'),('not_voting','not-voting-total')]}
    positions=[];count=collections.Counter()
    for i,x in enumerate(root.findall('vote-data/recorded-vote'),1):
        legislator=x.find('legislator');position=text(x,'vote')
        canonical={'Yea':'yea','Aye':'yea','Nay':'nay','No':'nay','Present':'present','Not Voting':'not_voting'}.get(position)
        if canonical is None:raise ValueError('Unknown House vote position '+position)
        count[canonical]+=1
        positions.append({'vote_id':vid,'member_id':legislator.get('name-id',''),'member_name':legislator.text or '','party':legislator.get('party',''),'state':legislator.get('state',''),'position':position,'source_row':i,'source_id':source['sha256']})
    if any(count[k]!=v for k,v in expected.items()):raise ValueError('Official totals do not reconcile: '+vid)
    vote={'vote_id':vid,'congress':c,'session':session,'roll_number':number,'bill_id':bid,'measure_source':measure,'question':text(m,'vote-question'),'vote_type':text(m,'vote-type'),'result':text(m,'vote-result'),'description':text(m,'vote-desc'),'vote_date':datetime.strptime(text(m,'action-date'),'%d-%b-%Y').date().isoformat(),'vote_time':text(m,'action-time'),'amendment_number':text(m,'amendment-num'),**expected,'source_url':source['url'],'source_id':source['sha256']}
    return vote,positions

def collect(status,output,refresh=False):
    c=duckdb.connect();rows=c.execute("SELECT DISTINCT url FROM read_parquet(?) WHERE url LIKE 'https://clerk.house.gov/evs/2024/%' ORDER BY url",[str(Path(status)/'tables/vote_references.parquet')]).fetchall();c.close()
    target=Path(output)
    if target.exists():raise ValueError('Choose a new immutable output name')
    work=Path(tempfile.mkdtemp(prefix='.house-',dir=target.parent));staging=work/'staging';staging.mkdir();(work/'tables').mkdir();writers={};handles={};sources=[];failures=[]
    try:
        for index,(url,) in enumerate(rows,1):
            try:
                p,m=fetch(url,refresh);vote,positions=parse_vote(p.read_bytes(),m)
            except Exception as e:
                failures.append({'url':url,'error':str(e)});continue
            for table,data in [('votes',[vote]),('positions',positions)]:
                if table not in writers:
                    handles[table]=(staging/(table+'.csv')).open('w',newline='',encoding='utf-8');writers[table]=csv.DictWriter(handles[table],fieldnames=list(data[0]));writers[table].writeheader()
                writers[table].writerows(data)
            sources.append(m)
            if index%25==0:print('House XMLs processed',index,'/',len(rows),flush=True)
        for f in handles.values():f.close()
        c,catalog=export_tables(staging,work/'tables')
        if c.execute('SELECT count(*) FROM (SELECT vote_id,member_id FROM positions GROUP BY vote_id,member_id HAVING count(*)>1)').fetchone()[0]:raise ValueError('Duplicate vote/member IDs')
        if c.execute("SELECT count(*) FROM positions WHERE member_id=''").fetchone()[0]:raise ValueError('Missing member IDs')
        if c.execute('SELECT count(*) FROM positions p ANTI JOIN votes v USING(vote_id)').fetchone()[0]:raise ValueError('Orphan positions')
        checks={'official_totals_match_all_acquired_votes':True,'unique_vote_member_pairs':True,'no_missing_member_ids':True,'all_positions_have_vote':True,'all_requested_downloads_succeeded':not failures}
        atomic_json(work/'catalog.json',{'scope':'All unique 2024 House XML roll-call URLs referenced by HR/S/HJRES/SJRES in the acquired 118/119 status snapshot. Not all House votes, not Senate votes.','requested_votes':len(rows),'acquired_votes':len(sources),'tables':catalog,'sources':sources,'failures':failures})
        atomic_json(work/'validation.json',{'checks':checks,'analytical_limit':'Yea is not always policy support. Quorum, procedure, amendments and passage are separate source questions; Not Voting is not opposition.'})
        c.close();shutil.rmtree(staging)
        atomic_json(work/'package.json',{'files':[{'path':str(p.relative_to(work)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(work.rglob('*')) if p.is_file()]});os.rename(work,target)
        print('House collection complete',len(sources),'votes;',len(failures),'failures',flush=True)
    except BaseException:
        for f in handles.values():f.close()
        shutil.rmtree(work,ignore_errors=True);raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--status',type=Path,default=ROOT/'datasets/pathways-2026-10-28');p.add_argument('--output',type=Path,default=ROOT/'datasets/house-2024-pathway-votes');p.add_argument('--refresh',action='store_true');a=p.parse_args();collect(a.status,a.output,a.refresh)
