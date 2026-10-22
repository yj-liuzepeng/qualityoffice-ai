-- SQLite product metadata baseline, not upstream dsh's session schema.
-- Enable WAL in application after opening an owned local NTFS database.
PRAGMA foreign_keys = ON;
CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, checksum TEXT NOT NULL);
CREATE TABLE session_refs(
  id TEXT PRIMARY KEY, upstream_session_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE tasks(
  id TEXT PRIMARY KEY, session_ref_id TEXT REFERENCES session_refs(id),
  title TEXT NOT NULL, task_kind TEXT NOT NULL CHECK(task_kind IN ('chat','file','kb','news','office')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
);
CREATE TABLE attempts(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
  attempt_number INTEGER NOT NULL CHECK(attempt_number>0),
  state TEXT NOT NULL CHECK(state IN ('queued','running','succeeded','partial','failed','cancelling','cancelled','interrupted')),
  state_version INTEGER NOT NULL DEFAULT 1 CHECK(state_version>0),
  started_at TEXT, finished_at TEXT, error_code TEXT, error_message TEXT,
  created_at TEXT NOT NULL, UNIQUE(task_id,attempt_number)
);
CREATE TABLE operations(
  id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id),
  tool_name TEXT NOT NULL, state TEXT NOT NULL,
  input_resource_ids_json TEXT NOT NULL CHECK(json_valid(input_resource_ids_json)),
  output_resource_ids_json TEXT NOT NULL CHECK(json_valid(output_resource_ids_json)),
  progress_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(progress_json)),
  started_at TEXT, finished_at TEXT, error_code TEXT
);
CREATE TABLE remote_runs(
  run_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
  attempt_id TEXT NOT NULL REFERENCES attempts(id),
  execution_state TEXT NOT NULL, billing_state TEXT NOT NULL,
  reserved_units INTEGER NOT NULL CHECK(reserved_units>=0),
  charged_units INTEGER CHECK(charged_units>=0), last_seq INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
CREATE TABLE file_objects(
  sha256 TEXT PRIMARY KEY CHECK(length(sha256)=64),
  relative_path TEXT NOT NULL UNIQUE, size_bytes INTEGER NOT NULL CHECK(size_bytes>=0),
  media_type TEXT NOT NULL, created_at TEXT NOT NULL,
  pending_purge_at TEXT, purged_at TEXT
);
CREATE TABLE documents(
  id TEXT PRIMARY KEY, title TEXT NOT NULL, source_type TEXT NOT NULL,
  publisher TEXT, jurisdiction TEXT, document_number TEXT,
  created_at TEXT NOT NULL, deleted_at TEXT
);
CREATE TABLE document_versions(
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
  version_number INTEGER NOT NULL CHECK(version_number>0), business_version TEXT,
  object_sha256 TEXT NOT NULL REFERENCES file_objects(sha256), original_display_name TEXT NOT NULL,
  original_path_host_only TEXT, original_url TEXT,
  published_at TEXT, effective_at TEXT, repealed_at TEXT,
  status_label TEXT NOT NULL CHECK(status_label IN ('current','historical','unknown')),
  status_origin TEXT NOT NULL DEFAULT 'user' CHECK(status_origin IN ('user','unverified_import')),
  verification_note TEXT, parse_state TEXT NOT NULL,
  parser_version TEXT, coverage_json TEXT CHECK(coverage_json IS NULL OR json_valid(coverage_json)),
  warnings_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(warnings_json)),
  created_at TEXT NOT NULL, deleted_at TEXT,
  UNIQUE(document_id,version_number)
);
CREATE TABLE task_inputs(
  task_id TEXT NOT NULL REFERENCES tasks(id), document_version_id TEXT NOT NULL REFERENCES document_versions(id),
  PRIMARY KEY(task_id,document_version_id)
);
CREATE TABLE segments(
  id TEXT PRIMARY KEY, document_version_id TEXT NOT NULL REFERENCES document_versions(id),
  ordinal INTEGER NOT NULL CHECK(ordinal>=0), kind TEXT NOT NULL, text_content TEXT NOT NULL,
  locator_json TEXT NOT NULL CHECK(json_valid(locator_json)), extraction TEXT NOT NULL,
  confidence REAL CHECK(confidence IS NULL OR confidence BETWEEN 0 AND 1),
  UNIQUE(document_version_id,ordinal)
);
CREATE TABLE source_refs(
  id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id),
  source_kind TEXT NOT NULL CHECK(source_kind IN ('local','web')),
  document_version_id TEXT REFERENCES document_versions(id), locator_json TEXT CHECK(locator_json IS NULL OR json_valid(locator_json)),
  source_url TEXT, final_url TEXT, canonical_url TEXT, title TEXT NOT NULL,
  publisher TEXT, published_at TEXT, fetched_at TEXT, body_hash TEXT,
  extraction_state TEXT NOT NULL, excerpt TEXT, deleted_source INTEGER NOT NULL DEFAULT 0 CHECK(deleted_source IN (0,1)),
  CHECK((source_kind='local' AND document_version_id IS NOT NULL) OR (source_kind='web' AND source_url IS NOT NULL))
);
CREATE TABLE artifacts(
  id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id),
  relative_path TEXT NOT NULL UNIQUE, format TEXT NOT NULL, sha256 TEXT NOT NULL,
  generation_status TEXT NOT NULL CHECK(generation_status IN ('ready','partial','invalid')),
  validation_status TEXT NOT NULL CHECK(validation_status IN ('passed','failed','not_checked')),
  preview_status TEXT NOT NULL CHECK(preview_status IN ('ready','partial','failed','not_requested')),
  source_map_json TEXT NOT NULL CHECK(json_valid(source_map_json)),
  created_at TEXT NOT NULL, deleted_at TEXT
);
-- v1.2 new local entities; actual upgrades must run a numbered migration.
CREATE TABLE office_profiles(
  id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, name TEXT NOT NULL,
  current_revision INTEGER NOT NULL CHECK(current_revision>0),
  is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0,1)),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
);
CREATE UNIQUE INDEX one_default_office_profile ON office_profiles(owner_user_id)
  WHERE is_default=1 AND deleted_at IS NULL;
CREATE TABLE office_profile_revisions(
  profile_id TEXT NOT NULL REFERENCES office_profiles(id), revision INTEGER NOT NULL CHECK(revision>0),
  profile_json TEXT NOT NULL CHECK(json_valid(profile_json)), sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(profile_id,revision)
);
CREATE TABLE domain_packages(
  domain_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
  state TEXT NOT NULL CHECK(state IN ('draft','published','withdrawn')),
  package_json TEXT NOT NULL CHECK(json_valid(package_json)), sha256 TEXT NOT NULL, installed_at TEXT NOT NULL,
  PRIMARY KEY(domain_id,version)
);
CREATE TABLE subscription_plans(
  id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL UNIQUE,
  current_revision INTEGER NOT NULL CHECK(current_revision>0), enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE subscription_plan_revisions(
  plan_id TEXT NOT NULL REFERENCES subscription_plans(id), revision INTEGER NOT NULL CHECK(revision>0),
  plan_json TEXT NOT NULL CHECK(json_valid(plan_json)), sha256 TEXT NOT NULL, effective_from TEXT NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY(plan_id,revision)
);
CREATE TABLE office_plans(
  id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id),
  schema_version TEXT NOT NULL, plan_json TEXT NOT NULL CHECK(json_valid(plan_json)), plan_sha256 TEXT NOT NULL,
  validation_state TEXT NOT NULL CHECK(validation_state IN ('valid','needs_input','rejected','expired')),
  effective_preferences_json TEXT CHECK(effective_preferences_json IS NULL OR json_valid(effective_preferences_json)),
  preferences_sha256 TEXT,
  expires_at TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE templates(
  id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
  object_sha256 TEXT NOT NULL REFERENCES file_objects(sha256),
  manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)), review_state TEXT NOT NULL,
  PRIMARY KEY(id,version)
);
CREATE TABLE knowledge_bases(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', category TEXT,
  active_generation_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT
);
CREATE TABLE kb_versions(
  kb_id TEXT NOT NULL REFERENCES knowledge_bases(id), document_version_id TEXT NOT NULL REFERENCES document_versions(id),
  included INTEGER NOT NULL DEFAULT 1 CHECK(included IN (0,1)),
  index_state TEXT NOT NULL CHECK(index_state IN ('queued','copying','parsing','chunking','embedding','indexing','ready','partial','failed','cancelled')),
  removed_at TEXT, error_code TEXT, PRIMARY KEY(kb_id,document_version_id)
);
CREATE TABLE chunks(
  id TEXT PRIMARY KEY, document_version_id TEXT NOT NULL REFERENCES document_versions(id),
  chunker_hash TEXT NOT NULL, ordinal INTEGER NOT NULL, text_content TEXT NOT NULL,
  source_segment_ids_json TEXT NOT NULL CHECK(json_valid(source_segment_ids_json)),
  locator_json TEXT NOT NULL CHECK(json_valid(locator_json)), token_count INTEGER NOT NULL CHECK(token_count>0),
  deleted_at TEXT, UNIQUE(document_version_id,chunker_hash,ordinal)
);
CREATE TABLE index_generations(
  id TEXT PRIMARY KEY, kb_id TEXT NOT NULL REFERENCES knowledge_bases(id),
  state TEXT NOT NULL CHECK(state IN ('staging','active','retired','failed')),
  model_hash TEXT NOT NULL, tokenizer_hash TEXT NOT NULL, chunker_hash TEXT NOT NULL,
  dimensions INTEGER NOT NULL CHECK(dimensions>0), vector_snapshot_path TEXT NOT NULL,
  id_map_path TEXT NOT NULL, manifest_sha256 TEXT NOT NULL, chunk_count INTEGER NOT NULL CHECK(chunk_count>=0),
  created_at TEXT NOT NULL, activated_at TEXT
);
CREATE UNIQUE INDEX one_active_generation_per_kb ON index_generations(kb_id) WHERE state='active';
CREATE TABLE generation_chunks(
  generation_id TEXT NOT NULL REFERENCES index_generations(id), chunk_id TEXT NOT NULL REFERENCES chunks(id),
  vector_ordinal INTEGER NOT NULL CHECK(vector_ordinal>=0),
  PRIMARY KEY(generation_id,chunk_id), UNIQUE(generation_id,vector_ordinal)
);
CREATE VIRTUAL TABLE chunk_fts USING fts5(chunk_id UNINDEXED,document_version_id UNINDEXED,pretokenized_text,tokenize='unicode61');
-- App must apply pre-tokenized Chinese text and explicitly join tombstone/scope filters.
CREATE TABLE subscriptions(
  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
  source_adapter_version TEXT NOT NULL, source_config_json TEXT NOT NULL CHECK(json_valid(source_config_json)),
  themes_json TEXT NOT NULL CHECK(json_valid(themes_json)),
  watermark_json TEXT CHECK(watermark_json IS NULL OR json_valid(watermark_json)),
  last_success_at TEXT, health_state TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE schedules(
  id TEXT PRIMARY KEY, plan_id TEXT UNIQUE REFERENCES subscription_plans(id),
  revision INTEGER NOT NULL CHECK(revision>0), timezone TEXT NOT NULL,
  local_time TEXT NOT NULL, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
  effective_from TEXT NOT NULL, last_completed_logical_date TEXT, created_at TEXT NOT NULL,
  UNIQUE(id,revision)
);
CREATE TABLE schedule_revisions(
  schedule_id TEXT NOT NULL REFERENCES schedules(id), revision INTEGER NOT NULL CHECK(revision>0),
  timezone TEXT NOT NULL, local_time TEXT NOT NULL, effective_from TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(schedule_id,revision)
);
CREATE TABLE schedule_runs(
  id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL REFERENCES schedules(id), schedule_revision INTEGER NOT NULL,
  plan_id TEXT, plan_revision INTEGER,
  logical_date TEXT NOT NULL, trigger_kind TEXT NOT NULL CHECK(trigger_kind IN ('scheduled','catchup','manual')),
  state TEXT NOT NULL CHECK(state IN ('queued','running','succeeded','partial','failed','cancelled')),
  coverage_start TEXT, coverage_end TEXT NOT NULL, lease_owner TEXT, lease_expires_at TEXT, heartbeat_at TEXT,
  stage TEXT NOT NULL, retry_count INTEGER NOT NULL DEFAULT 0 CHECK(retry_count BETWEEN 0 AND 2),
  next_retry_at TEXT, metrics_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metrics_json)),
  error_code TEXT, created_at TEXT NOT NULL, finished_at TEXT,
  FOREIGN KEY(plan_id,plan_revision) REFERENCES subscription_plan_revisions(plan_id,revision),
  FOREIGN KEY(schedule_id,schedule_revision) REFERENCES schedule_revisions(schedule_id,revision)
);
CREATE UNIQUE INDEX scheduled_logical_day_unique ON schedule_runs(schedule_id,schedule_revision,logical_date)
  WHERE trigger_kind IN ('scheduled','catchup');
CREATE TABLE run_sources(
  run_id TEXT NOT NULL REFERENCES schedule_runs(id), subscription_id TEXT NOT NULL REFERENCES subscriptions(id),
  state TEXT NOT NULL, next_cursor_json TEXT CHECK(next_cursor_json IS NULL OR json_valid(next_cursor_json)),
  new_count INTEGER NOT NULL DEFAULT 0, revised_count INTEGER NOT NULL DEFAULT 0, error_code TEXT,
  PRIMARY KEY(run_id,subscription_id)
);
CREATE TABLE articles(
  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, canonical_url TEXT NOT NULL,
  discovered_at TEXT NOT NULL, latest_revision INTEGER NOT NULL CHECK(latest_revision>0), duplicate_group_id TEXT,
  UNIQUE(source_id,canonical_url)
);
CREATE TABLE article_revisions(
  article_id TEXT NOT NULL REFERENCES articles(id), revision INTEGER NOT NULL CHECK(revision>0),
  title TEXT NOT NULL, url TEXT NOT NULL, publisher TEXT, published_at TEXT, fetched_at TEXT NOT NULL,
  body_hash TEXT NOT NULL, excerpt TEXT, text_relative_path TEXT, relevance_state TEXT NOT NULL,
  PRIMARY KEY(article_id,revision)
);
CREATE TABLE digests(
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES schedule_runs(id),
  logical_date TEXT NOT NULL, status TEXT NOT NULL,
  content_json TEXT NOT NULL CHECK(json_valid(content_json)),
  article_refs_json TEXT NOT NULL CHECK(json_valid(article_refs_json)),
  model_request_ids_json TEXT NOT NULL CHECK(json_valid(model_request_ids_json)),
  created_at TEXT NOT NULL
);
CREATE TABLE notifications(
  id TEXT PRIMARY KEY, schedule_id TEXT REFERENCES schedules(id),
  logical_date TEXT NOT NULL, digest_id TEXT NOT NULL REFERENCES digests(id),
  notification_kind TEXT NOT NULL, shown_at TEXT, read_at TEXT,
  UNIQUE(schedule_id,logical_date,notification_kind)
);
CREATE INDEX document_versions_doc ON document_versions(document_id,deleted_at);
CREATE INDEX chunks_doc ON chunks(document_version_id,deleted_at);
CREATE INDEX attempts_task ON attempts(task_id,state);
CREATE INDEX run_retry ON schedule_runs(state,next_retry_at);
-- Migration baseline deliberately has no production secrets or fixture rows.
