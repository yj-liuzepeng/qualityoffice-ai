-- PostgreSQL product server schema baseline. UUIDs supplied by the application.
-- Production migrations must be generated, versioned and tested on a real PostgreSQL instance.
CREATE TABLE schema_migrations(version integer PRIMARY KEY, applied_at timestamptz NOT NULL, checksum text NOT NULL);
CREATE TABLE users(
 id uuid PRIMARY KEY, username text NOT NULL UNIQUE, email text,
 password_hash text, state text NOT NULL CHECK(state IN ('active','disabled')),
 role text NOT NULL CHECK(role IN ('user','admin')),
 activation_hash text, activation_expires_at timestamptz, activation_used_at timestamptz,
 activation_kind text CHECK(activation_kind IN ('activate','password_reset')),
 failed_login_count integer NOT NULL DEFAULT 0, locked_until timestamptz,
 version bigint NOT NULL DEFAULT 1 CHECK(version>0), created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL
);
CREATE TABLE devices(
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id), installation_id uuid NOT NULL,
 label text NOT NULL, first_seen_at timestamptz NOT NULL, last_seen_at timestamptz NOT NULL,
 revoked_at timestamptz, version bigint NOT NULL DEFAULT 1, UNIQUE(user_id,installation_id)
);
CREATE TABLE refresh_sessions(
 id uuid PRIMARY KEY, family_id uuid NOT NULL, user_id uuid NOT NULL REFERENCES users(id),
 device_id uuid NOT NULL REFERENCES devices(id), token_hash text NOT NULL UNIQUE,
 created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 consumed_at timestamptz, revoked_at timestamptz, replaced_by_id uuid REFERENCES refresh_sessions(id)
);
CREATE TABLE memberships(
 user_id uuid PRIMARY KEY REFERENCES users(id), starts_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 features jsonb NOT NULL CHECK(jsonb_typeof(features)='array'),
 policy_version text NOT NULL, version bigint NOT NULL DEFAULT 1,
 CHECK(expires_at>starts_at)
);
CREATE TABLE price_cards(
 id uuid PRIMARY KEY, version text NOT NULL UNIQUE,
 input_units_per_million bigint NOT NULL CHECK(input_units_per_million>=0),
 cached_input_units_per_million bigint NOT NULL CHECK(cached_input_units_per_million>=0),
 output_units_per_million bigint NOT NULL CHECK(output_units_per_million>=0),
 provider_currency text NOT NULL, provider_rate_snapshot jsonb NOT NULL,
 created_at timestamptz NOT NULL
);
CREATE TABLE model_routes(
 id uuid PRIMARY KEY, alias text NOT NULL, version integer NOT NULL CHECK(version>0),
 provider_config_ref text NOT NULL, model_id text NOT NULL, price_card_id uuid NOT NULL REFERENCES price_cards(id),
 input_token_limit integer NOT NULL CHECK(input_token_limit>0),
 output_token_limit integer NOT NULL CHECK(output_token_limit>0),
 enabled boolean NOT NULL, verified_capabilities jsonb NOT NULL,
 created_at timestamptz NOT NULL, UNIQUE(alias,version)
);
CREATE TABLE credit_grants(
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id),
 amount_units bigint NOT NULL CHECK(amount_units>0), revoked_units bigint NOT NULL DEFAULT 0 CHECK(revoked_units>=0),
 spent_units bigint NOT NULL DEFAULT 0 CHECK(spent_units>=0), reserved_units bigint NOT NULL DEFAULT 0 CHECK(reserved_units>=0),
 starts_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, origin_ref text,
 created_by uuid NOT NULL REFERENCES users(id), reason text NOT NULL, version bigint NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL,
 CHECK(expires_at>starts_at), CHECK(amount_units>=revoked_units+spent_units+reserved_units)
);
CREATE TABLE feature_daily_budgets(
 user_id uuid NOT NULL REFERENCES users(id), feature text NOT NULL CHECK(feature='news'),
 logical_date date NOT NULL, timezone text NOT NULL,
 first_call_available_units bigint NOT NULL CHECK(first_call_available_units>=0),
 cap_units bigint NOT NULL CHECK(cap_units>=0), spent_units bigint NOT NULL DEFAULT 0 CHECK(spent_units>=0),
 reserved_units bigint NOT NULL DEFAULT 0 CHECK(reserved_units>=0),
 request_count integer NOT NULL DEFAULT 0 CHECK(request_count BETWEEN 0 AND 2),
 created_at timestamptz NOT NULL,
 PRIMARY KEY(user_id,feature,logical_date), CHECK(spent_units+reserved_units<=cap_units)
);
CREATE TABLE model_runs(
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id), device_id uuid NOT NULL REFERENCES devices(id),
 request_id uuid NOT NULL, task_id uuid NOT NULL, attempt_id uuid NOT NULL,
 purpose text NOT NULL CHECK(purpose IN ('chat','task','news')), feature_budget_date date,
 route_id uuid NOT NULL REFERENCES model_routes(id), price_card_id uuid NOT NULL REFERENCES price_cards(id),
 request_hash text NOT NULL, provider_request_id text,
 state text NOT NULL CHECK(state IN ('reserved','dispatched','streaming','completed','failed','cancelled','unknown')),
 billing_state text NOT NULL CHECK(billing_state IN ('held','settled','pending_usage','released','waived_unknown')),
 reserved_units bigint NOT NULL CHECK(reserved_units>=0), charged_units bigint CHECK(charged_units>=0),
 platform_absorbed_units bigint NOT NULL DEFAULT 0 CHECK(platform_absorbed_units>=0),
 uncached_input_tokens bigint CHECK(uncached_input_tokens>=0), cached_input_tokens bigint CHECK(cached_input_tokens>=0),
 output_tokens bigint CHECK(output_tokens>=0), reasoning_tokens bigint CHECK(reasoning_tokens>=0),
 usage_source text NOT NULL CHECK(usage_source IN ('provider','reconciled','unknown')),
 provider_currency text, provider_cost_amount numeric(20,8),
 cancel_requested_at timestamptz, dispatched_at timestamptz,
 usage_pending_since timestamptz, reconcile_deadline_at timestamptz,
 last_reconciled_at timestamptz, error_code text,
 created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL, finalized_at timestamptz,
 version bigint NOT NULL DEFAULT 1, UNIQUE(user_id,request_id),
 CHECK(charged_units IS NULL OR charged_units<=reserved_units),
 CHECK(provider_cost_amount IS NULL OR provider_cost_amount>=0)
);
CREATE TABLE reservation_allocations(
 run_id uuid NOT NULL REFERENCES model_runs(id), grant_id uuid NOT NULL REFERENCES credit_grants(id),
 reserved_units bigint NOT NULL CHECK(reserved_units>0),
 charged_units bigint CHECK(charged_units>=0), released_units bigint CHECK(released_units>=0),
 PRIMARY KEY(run_id,grant_id),
 CHECK(charged_units IS NULL OR charged_units<=reserved_units),
 CHECK(charged_units IS NULL OR released_units IS NULL OR charged_units+released_units=reserved_units)
);
CREATE TABLE usage_ledger(
 id uuid PRIMARY KEY, run_id uuid NOT NULL UNIQUE REFERENCES model_runs(id), user_id uuid NOT NULL REFERENCES users(id),
 charged_units bigint NOT NULL CHECK(charged_units>=0), price_card_id uuid NOT NULL REFERENCES price_cards(id),
 settlement_kind text NOT NULL CHECK(settlement_kind IN ('actual','released_not_dispatched','waived_unknown')),
 created_at timestamptz NOT NULL
);
-- Late provider cost evidence is appended; never rewrite an immutable usage ledger.
CREATE TABLE provider_cost_events(
 id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES model_runs(id), evidence_key text NOT NULL,
 event_kind text NOT NULL CHECK(event_kind IN ('final_usage','late_usage','correction')),
 currency text NOT NULL, amount_delta numeric(20,8) NOT NULL,
 usage_metadata jsonb NOT NULL, created_at timestamptz NOT NULL,
 UNIQUE(run_id,evidence_key)
);
CREATE TABLE idempotency_records(
 user_id uuid NOT NULL REFERENCES users(id), key uuid NOT NULL, operation text NOT NULL,
 request_hash text NOT NULL, resource_id uuid, http_status integer NOT NULL,
 result_metadata jsonb NOT NULL, created_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 PRIMARY KEY(user_id,key)
);
CREATE TABLE admin_audits(
 id uuid PRIMARY KEY, actor_user_id uuid NOT NULL REFERENCES users(id),
 action text NOT NULL, object_type text NOT NULL, object_id uuid NOT NULL,
 before_metadata jsonb, after_metadata jsonb, reason text NOT NULL,
 request_id uuid NOT NULL, created_at timestamptz NOT NULL
);
CREATE TABLE search_requests(
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id), request_id uuid NOT NULL,
 task_id uuid NOT NULL, attempt_id uuid NOT NULL, operation text NOT NULL CHECK(operation IN ('search','read')),
 query_hash text NOT NULL, provider_config_ref text NOT NULL, state text NOT NULL,
 result_count integer NOT NULL CHECK(result_count>=0), currency text,
 provider_cost_amount numeric(20,8), error_code text, created_at timestamptz NOT NULL,
 UNIQUE(user_id,request_id)
);
CREATE INDEX credit_grants_lock_order ON credit_grants(user_id,expires_at,id);
CREATE INDEX model_run_reconcile ON model_runs(billing_state,reconcile_deadline_at);
CREATE INDEX model_run_history ON model_runs(user_id,created_at DESC,id);
CREATE INDEX active_refresh ON refresh_sessions(user_id,device_id) WHERE revoked_at IS NULL;
CREATE INDEX audit_history ON admin_audits(created_at DESC,id);
-- Application transactions: lock user row for paid-call concurrency and device count;
-- lock grants ORDER BY expires_at,id; update grant aggregates + allocations + run + ledger together.
-- Runtime roles must not UPDATE/DELETE usage_ledger, price_cards or admin_audits.
-- Migration roles separate. Do not record message/document bodies, keys or secret token values.
