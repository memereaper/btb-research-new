-- Reusable initial schema. Revise as sources and investigations expand.
-- IDs are stable TEXT identifiers; party/committee memberships are time-dependent.
CREATE TABLE bills (
  bill_id VARCHAR, congress INTEGER, bill_type VARCHAR, bill_number INTEGER,
  title VARCHAR, introduced_date DATE, latest_action_date DATE,
  latest_action_text VARCHAR, outcome VARCHAR, enacted_date DATE,
  sponsor_id VARCHAR, source_url VARCHAR, source_id VARCHAR,
  source_record_id VARCHAR, updated_at TIMESTAMP
);
CREATE TABLE actions (
  action_id VARCHAR, bill_id VARCHAR, action_date DATE, action_time VARCHAR,
  action_code VARCHAR, action_text VARCHAR, chamber VARCHAR,
  committee_id VARCHAR, sequence_number INTEGER,
  source_url VARCHAR, source_id VARCHAR, source_record_id VARCHAR
);
CREATE TABLE legislators (
  legislator_id VARCHAR, first_name VARCHAR, last_name VARCHAR,
  full_name VARCHAR, bioguide_id VARCHAR, source_id VARCHAR
);
CREATE TABLE legislator_terms (
  legislator_id VARCHAR, congress INTEGER, chamber VARCHAR, state VARCHAR,
  district VARCHAR, party VARCHAR, term_start DATE, term_end DATE,
  source_id VARCHAR
);
CREATE TABLE cosponsorships (
  bill_id VARCHAR, legislator_id VARCHAR, joined_date DATE,
  withdrawn_date DATE, is_original BOOLEAN, source_id VARCHAR
);
CREATE TABLE committees (
  committee_id VARCHAR, name VARCHAR, chamber VARCHAR,
  parent_committee_id VARCHAR, source_id VARCHAR
);
CREATE TABLE committee_referrals (
  bill_id VARCHAR, committee_id VARCHAR, referred_date DATE,
  discharged_date DATE, source_id VARCHAR
);
CREATE TABLE votes (
  vote_id VARCHAR, bill_id VARCHAR, congress INTEGER, chamber VARCHAR,
  session_number INTEGER, rollcall_number INTEGER, vote_date DATE,
  question VARCHAR, result VARCHAR, yeas INTEGER, nays INTEGER,
  source_url VARCHAR, source_id VARCHAR
);
CREATE TABLE vote_positions (
  vote_id VARCHAR, legislator_id VARCHAR, position VARCHAR, source_id VARCHAR
);
CREATE TABLE amendments (
  amendment_id VARCHAR, bill_id VARCHAR, sponsor_id VARCHAR,
  introduced_date DATE, amendment_text VARCHAR, outcome VARCHAR,
  source_url VARCHAR, source_id VARCHAR
);
CREATE TABLE bill_text_versions (
  text_id VARCHAR, bill_id VARCHAR, version_code VARCHAR,
  issued_date DATE, text_storage_path VARCHAR, content_sha256 VARCHAR,
  source_url VARCHAR, source_id VARCHAR
);
CREATE TABLE sources (
  source_id VARCHAR, provider VARCHAR, original_url VARCHAR,
  retrieved_at TIMESTAMP, source_version VARCHAR, sha256 VARCHAR,
  license_notes VARCHAR
);
CREATE TABLE corrections (
  correction_id VARCHAR, entity_type VARCHAR, entity_id VARCHAR,
  field_name VARCHAR, previous_value VARCHAR, corrected_value VARCHAR,
  rationale VARCHAR, reviewer VARCHAR, corrected_at TIMESTAMP,
  source_id VARCHAR
);
