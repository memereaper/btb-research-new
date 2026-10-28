import sys,unittest,tempfile,csv,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_pathways import parse_bill,export_tables
from collect_house_votes import parse_vote
from collect_text_pilot import sections

class CollectorTests(unittest.TestCase):
    def test_bill_event_provenance_and_withdrawal(self):
        raw=b'''<billStatus><bill><congress>118</congress><type>HR</type><number>1</number><cosponsors><item><bioguideId>A000001</bioguideId><sponsorshipDate>2023-01-04</sponsorshipDate><sponsorshipWithdrawnDate>2023-01-10</sponsorshipWithdrawnDate></item></cosponsors><actions><item><actionDate>2023-01-05</actionDate><text>first</text><recordedVotes><recordedVote><url>https://clerk.house.gov/example.xml</url></recordedVote></recordedVotes></item><item><actionDate>2023-01-05</actionDate><text>first</text></item></actions><relatedBills><item><congress>118</congress><type>S</type><number>2</number><relationshipDetails><item><type>Identical bill</type><identifiedBy>CRS</identifiedBy></item></relationshipDetails></item></relatedBills></bill></billStatus>'''
        r=parse_bill(raw,'archivehash','record.xml')
        self.assertEqual(r['bills'][0]['bill_id'],'118-hr1')
        self.assertEqual(r['cosponsors'][0]['withdrawn_date'],'2023-01-10')
        self.assertEqual(len(r['actions']),2)
        self.assertNotEqual(r['actions'][0]['action_id'],r['actions'][1]['action_id'])
        self.assertEqual(r['related_bills'][0]['related_bill_id'],'118-s2')
        self.assertEqual(r['vote_references'][0]['action_id'],r['actions'][0]['action_id'])
        self.assertEqual(r['actions'][0]['source_id'],'archivehash')

    def test_late_quoted_large_csv_field(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'out').mkdir()
            with (root/'large.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['id','value'])
                w.writerows((i,'') for i in range(21000))
                large='{"party":"D","evidence":"'+('x'*140000)+'"}'
                w.writerow([21000,large])
            c,catalog=export_tables(root,root/'out')
            self.assertEqual(catalog[0]['rows'],21001)
            self.assertEqual(c.execute("SELECT value FROM large WHERE id='21000'").fetchall()[0][0],large)
            c.close()

    def vote(self,total=1):
        return f'''<rollcall-vote><vote-metadata><congress>118</congress><session>2nd</session><rollcall-num>9</rollcall-num><legis-num>HR 1</legis-num><action-date>10-Jan-2024</action-date><vote-totals><totals-by-vote><yea-total>0</yea-total><nay-total>0</nay-total><present-total>0</present-total><not-voting-total>{total}</not-voting-total></totals-by-vote></vote-totals></vote-metadata><vote-data><recorded-vote><legislator name-id="A000001" party="D" state="TX">A</legislator><vote>Not Voting</vote></recorded-vote></vote-data></rollcall-vote>'''.encode()
    def test_absence_stays_absence_and_totals_checked(self):
        v,p=parse_vote(self.vote(),{'sha256':'source','url':'https://clerk.house.gov/example'})
        self.assertEqual(p[0]['position'],'Not Voting');self.assertEqual(v['bill_id'],'118-hr1')
        with self.assertRaises(ValueError):parse_vote(self.vote(2),{'sha256':'source','url':'x'})
    def test_text_section_minimum_and_verbatim_evidence(self):
        source={'sha256':'hash','url':'https://www.govinfo.gov/example'}
        result=sections(('<bill><section id="s1"><text>'+'policy evidence '*60+'</text></section><section>short</section></bill>').encode(),source)
        self.assertEqual(len(result),1);self.assertEqual(result[0][0]['xml_section_id'],'s1')
        self.assertIn('policy evidence',result[0][0]['text'])
if __name__=='__main__':unittest.main()
