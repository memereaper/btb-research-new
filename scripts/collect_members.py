#!/usr/bin/env python3
"""Collect a pinned community-maintained member identity/term crosswalk (CC0)."""
import argparse,csv,json,os,shutil,tempfile
from pathlib import Path
import yaml
from collect_pathways import fetch,atomic_json,export_tables
from build_historical import ROOT,digest

def collect(output,refresh=False):
    path,commit_source=fetch('https://api.github.com/repos/unitedstates/congress-legislators/commits/main',refresh)
    commit=json.loads(path.read_text())['sha']
    target=Path(output)
    if target.exists():raise ValueError('Choose a new immutable output name')
    work=Path(tempfile.mkdtemp(prefix='.members-',dir=target.parent));stage=work/'staging';stage.mkdir();(work/'tables').mkdir();sources=[commit_source];people=[];terms=[];ids=[]
    try:
        for filename in ['legislators-historical.yaml','legislators-current.yaml']:
            p,m=fetch(f'https://raw.githubusercontent.com/unitedstates/congress-legislators/{commit}/{filename}',refresh);sources.append(m)
            for person in yaml.safe_load(p.read_text()):
                member=person['id']['bioguide'];name=person['name'];bio=person.get('bio',{})
                people.append({'member_id':member,'first_name':name.get('first',''),'middle_name':name.get('middle',''),'last_name':name.get('last',''),'official_full_name':name.get('official_full',''),'birthday':bio.get('birthday',''),'gender_source':bio.get('gender',''),'source_file':filename,'source_id':m['sha256']})
                for scheme,values in person['id'].items():
                    for value in values if isinstance(values,list) else [values]:
                        ids.append({'member_id':member,'identifier_scheme':scheme,'identifier':value,'source_id':m['sha256']})
                for i,term in enumerate(person.get('terms',[]),1):
                    terms.append({'member_id':member,'term_ordinal':i,'chamber':term.get('type',''),'start_date':term.get('start',''),'end_date':term.get('end',''),'state':term.get('state',''),'district':term.get('district',''),'party':term.get('party',''),'senate_class':term.get('class',''),'senate_rank':term.get('state_rank',''),'party_affiliations_json':json.dumps(term.get('party_affiliations',[]),default=str),'source_id':m['sha256']})
        for name,records in [('members',people),('member_terms',terms),('member_identifiers',ids)]:
            with (stage/(name+'.csv')).open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
        p,license_source=fetch(f'https://raw.githubusercontent.com/unitedstates/congress-legislators/{commit}/LICENSE',refresh);sources.append(license_source);shutil.copy2(p,work/'LICENSE')
        c,catalog=export_tables(stage,work/'tables')
        checks={'unique_member_ids':c.execute('SELECT count(*)=count(DISTINCT member_id) FROM members').fetchone()[0],'all_terms_have_members':c.execute('SELECT count(*) FROM member_terms t ANTI JOIN members m USING(member_id)').fetchone()[0]==0,'valid_term_dates':c.execute('SELECT count(*) FROM member_terms WHERE try_cast(start_date AS DATE) IS NULL OR try_cast(end_date AS DATE) IS NULL OR start_date>end_date').fetchone()[0]==0}
        if not all(checks.values()):raise ValueError(str(checks))
        atomic_json(work/'catalog.json',{'source_type':'Community-maintained crosswalk, not an official government identity assignment. CC0-1.0.','commit':commit,'tables':catalog,'sources':sources,'limitations':'Identifier arrays can contain multiple IDs (including FEC candidates by office). Do not join by name; check candidate office/cycle and dated service. Listed term end dates can include source-specific conventions; use dates and original party affiliations explicitly.'})
        atomic_json(work/'validation.json',{'checks':checks});c.close();shutil.rmtree(stage)
        atomic_json(work/'package.json',{'files':[{'path':str(p.relative_to(work)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(work.rglob('*')) if p.is_file()]});os.rename(work,target)
        print('Pinned member crosswalk acquired:',len(people),'members;',len(terms),'terms;',len(ids),'identifiers')
    except BaseException:shutil.rmtree(work,ignore_errors=True);raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'datasets/member-crosswalk-2026-10-28');p.add_argument('--refresh',action='store_true');a=p.parse_args();collect(a.output,a.refresh)
