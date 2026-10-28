-- CSV source-row ordinals are preserved; identical actions are not silently deduplicated.
CREATE TABLE bills AS
SELECT measure_id AS bill_id, CAST(congress AS INTEGER) congress,
       lower(regexp_extract(measure, '^([A-Z]+)',1)) bill_type,
       CAST(regexp_extract(measure,'([0-9]+)$',1) AS INTEGER) bill_number,
       title, CAST(introduced AS DATE) introduced_date,
       nullif(furthest_stage,'') outcome, TRY_CAST(became_law AS DATE) enacted_date,
       nullif(sponsor_bioguide_id,'') sponsor_id, source_xml_url source_url,
       source_file source_id, CAST(source_row AS VARCHAR) source_record_id
FROM raw_bills;
CREATE TABLE actions AS
SELECT sha256(source_file || ':' || source_row) action_id,
       congress || '-' || lower(replace(measure,' ','')) bill_id,
       CAST(action_date AS DATE) action_date, nullif(action_code,'') action_code,
       action_text, action_type, source_system, source_row sequence_number,
       source_file source_id, CAST(source_row AS VARCHAR) source_record_id
FROM raw_actions;
-- Preserve every original bill field, including all milestone dates, without inventing entities.
CREATE TABLE historical_bill_features AS SELECT * FROM raw_bills;
CREATE TABLE outcomes AS SELECT congress,outcome,count(*) bill_count,
       count(*) * 100.0 / sum(count(*)) OVER (PARTITION BY congress) percent
FROM bills GROUP BY congress,outcome;
