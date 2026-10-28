-- Run through scripts/query.py so bills resolves to the active validated version.
SELECT bill_id, congress, bill_type, bill_number, introduced_date, outcome
FROM bills WHERE congress BETWEEN 113 AND 118;
