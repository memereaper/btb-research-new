-- Retain ALL acquired vote purposes and positions. No published support rate is inferred.
SELECT v.bill_id,v.vote_id,v.vote_date,v.question,v.vote_type,v.result,v.amendment_number,
       p.member_id,p.position,p.party official_vote_party,
       c.party source_cosponsor_party,c.joined_date,c.withdrawn_date,c.is_original,
       b.sponsor_id bill_sponsor_id,b.sponsor_party source_bill_sponsor_party,
       c.party IN ('D','R') AND b.sponsor_party IN ('D','R') AND c.party<>b.sponsor_party source_strict_dr_crossparty,
       CASE WHEN c.joined_date='' THEN 'unknown_join_date'
            WHEN CAST(c.joined_date AS DATE)>CAST(v.vote_date AS DATE) THEN 'joined_after_vote'
            WHEN CAST(c.joined_date AS DATE)=CAST(v.vote_date AS DATE) OR left(c.withdrawn_date,10)=v.vote_date THEN 'same_day_order_ambiguous'
            WHEN c.withdrawn_date<>'' AND CAST(c.withdrawn_date AS DATE)<CAST(v.vote_date AS DATE) THEN 'withdrawn_before_vote'
            ELSE 'active_by_date_only' END timing_status,
       v.source_url vote_source_url,c.source_id cosponsor_source_id,c.source_member cosponsor_source_member,
       p.source_id vote_source_id
FROM house_votes v JOIN house_positions p USING(vote_id)
JOIN status_cosponsors c ON c.bill_id=v.bill_id AND c.sponsor_id=p.member_id
JOIN status_bills b ON b.bill_id=c.bill_id
ORDER BY v.vote_id,p.member_id,c.joined_date;
