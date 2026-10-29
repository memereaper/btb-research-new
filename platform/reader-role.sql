-- Run as the database owner after creating a dedicated login in your host's dashboard.
-- Replace btb_reader only if you chose a different existing role. No password belongs in this file.
GRANT CONNECT ON DATABASE btb TO btb_reader;
GRANT USAGE ON SCHEMA btb TO btb_reader;
GRANT SELECT ON btb.releases,btb.investigations,btb.bills,btb.actions,btb.summary_cells TO btb_reader;
ALTER ROLE btb_reader SET default_transaction_read_only = on;
ALTER ROLE btb_reader SET statement_timeout = '2500ms';
ALTER ROLE btb_reader SET lock_timeout = '1000ms';
-- Do not grant schema CREATE, table writes, release promotion, or collection credentials.
