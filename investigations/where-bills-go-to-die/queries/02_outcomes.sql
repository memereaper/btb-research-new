-- Starter aggregation only, not the validated original Explore methodology.
SELECT congress, COALESCE(outcome, 'unknown') AS outcome, COUNT(*) AS bill_count
FROM read_parquet('warehouse/core/bills.parquet')
GROUP BY congress, COALESCE(outcome, 'unknown')
ORDER BY congress, outcome;
