SELECT congress, outcome, COUNT(*) AS bill_count
FROM bills WHERE congress BETWEEN 113 AND 118
GROUP BY congress,outcome ORDER BY congress,outcome;
