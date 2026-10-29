CREATE SCHEMA IF NOT EXISTS btb;
CREATE TABLE IF NOT EXISTS btb.schema_versions(version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS btb.releases (
 release_id text PRIMARY KEY, manifest_sha256 text NOT NULL, manifest jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), status text NOT NULL CHECK(status IN ('loading','ready')),
 bill_count bigint NOT NULL, action_count bigint NOT NULL
);
CREATE TABLE IF NOT EXISTS btb.investigations (
 slug text PRIMARY KEY, release_id text NOT NULL REFERENCES btb.releases, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS btb.bills (
 release_id text NOT NULL REFERENCES btb.releases, bill_id text NOT NULL,
 congress integer NOT NULL, bill_type text NOT NULL, bill_number integer NOT NULL,
 title text NOT NULL, introduced_date date NOT NULL, outcome text NOT NULL,
 enacted_date date, sponsor_id text, source_url text NOT NULL,
 source_id text NOT NULL, source_record_id text NOT NULL,
 policy_area text NOT NULL, chamber text NOT NULL CHECK(chamber IN ('house','senate')),
 bipartisan boolean, sponsor_party text, sponsor_state text,
 search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english',title || ' ' || bill_id)) STORED,
 PRIMARY KEY(release_id,bill_id)
) PARTITION BY LIST(release_id);
CREATE INDEX IF NOT EXISTS bills_search ON btb.bills USING gin(search_vector);
CREATE INDEX IF NOT EXISTS bills_congress ON btb.bills(release_id,congress,bill_id);
CREATE INDEX IF NOT EXISTS bills_chamber ON btb.bills(release_id,congress,chamber,bill_id);
CREATE INDEX IF NOT EXISTS bills_policy ON btb.bills(release_id,congress,policy_area,bill_id);
CREATE INDEX IF NOT EXISTS bills_outcome ON btb.bills(release_id,congress,outcome,bill_id);
CREATE INDEX IF NOT EXISTS bills_bipartisan ON btb.bills(release_id,congress,bipartisan,bill_id);
CREATE TABLE IF NOT EXISTS btb.actions (
 release_id text NOT NULL, action_id text NOT NULL, bill_id text NOT NULL,
 action_date date, action_code text, action_text text NOT NULL, action_type text,
 source_system text, sequence_number bigint NOT NULL, source_id text NOT NULL, source_record_id text NOT NULL,
 PRIMARY KEY(release_id,action_id), FOREIGN KEY(release_id,bill_id) REFERENCES btb.bills(release_id,bill_id)
) PARTITION BY LIST(release_id);
CREATE INDEX IF NOT EXISTS actions_bill ON btb.actions(release_id,bill_id,sequence_number,action_id);
CREATE TABLE IF NOT EXISTS btb.summary_cells (
 release_id text NOT NULL REFERENCES btb.releases, congress integer NOT NULL,
 chamber text NOT NULL, policy_area text NOT NULL, outcome text NOT NULL,
 bipartisan text NOT NULL CHECK(bipartisan IN ('yes','no','unknown')), bill_count bigint NOT NULL,
 PRIMARY KEY(release_id,congress,chamber,policy_area,outcome,bipartisan)
);
CREATE TABLE IF NOT EXISTS btb.release_events (
 event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, occurred_at timestamptz NOT NULL DEFAULT now(),
 slug text NOT NULL, old_release text, new_release text NOT NULL REFERENCES btb.releases, reason text NOT NULL
);
INSERT INTO btb.schema_versions(version) VALUES(1) ON CONFLICT DO NOTHING;
