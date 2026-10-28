-- Same normalized title and sponsor in adjacent Congresses are candidates, not proven reintroductions.
WITH all_bills AS (
  SELECT bill_id,CAST(congress AS INTEGER) congress,title,sponsor_bioguide_id sponsor_id,introduced introduced_date,'original_2013_2024_extract' source_snapshot
  FROM historical_features
  UNION ALL
  SELECT bill_id,CAST(congress AS INTEGER),title,sponsor_id,introduced_date,'new_official_119_snapshot'
  FROM status_bills WHERE congress='119'
), normalized AS (
  SELECT *,lower(trim(regexp_replace(title,'[^a-zA-Z0-9]+',' ','g'))) title_key FROM all_bills
)
SELECT a.bill_id earlier_bill_id,b.bill_id later_bill_id,a.congress earlier_congress,b.congress later_congress,
       a.title earlier_title,b.title later_title,a.sponsor_id,a.introduced_date earlier_introduced,b.introduced_date later_introduced,
       a.source_snapshot earlier_source,b.source_snapshot later_source,
       'same normalized title + sponsor, adjacent Congress; unverified recurrence candidate' candidate_rule
FROM normalized a JOIN normalized b ON a.congress+1=b.congress AND a.title_key=b.title_key AND a.sponsor_id=b.sponsor_id
WHERE a.sponsor_id<>'' AND length(a.title_key)>=30
ORDER BY a.bill_id,b.bill_id;
