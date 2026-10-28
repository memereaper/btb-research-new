-- Example population; confirm inclusion rules with published methodology.
SELECT bill_id, congress, bill_type, bill_number, introduced_date, outcome
FROM read_parquet('warehouse/core/bills.parquet')
WHERE congress BETWEEN 113 AND 118;
