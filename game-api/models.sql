DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS pgcrypto;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE campaign_role AS ENUM ('owner', 'human_gm', 'co_gm', 'player', 'spectator');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE campaign_status AS ENUM ('draft', 'active', 'paused', 'completed', 'failed', 'total_party_kill', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE campaign_phase AS ENUM ('planning', 'resolving', 'narrating', 'paused', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE dm_mode AS ENUM ('llm_dm', 'hybrid', 'human_gm');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT UNIQUE NOT NULL CHECK (char_length(username) BETWEEN 2 AND 40),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL CHECK (char_length(name) BETWEEN 3 AND 80),
  description TEXT NOT NULL DEFAULT '' CHECK (char_length(description) <= 1000),
  password_hash TEXT,
  listed BOOLEAN NOT NULL DEFAULT true,
  max_players INTEGER NOT NULL DEFAULT 12 CHECK (max_players BETWEEN 1 AND 12),
  status campaign_status NOT NULL DEFAULT 'draft',
  phase campaign_phase NOT NULL DEFAULT 'planning',
  dm_mode dm_mode NOT NULL DEFAULT 'llm_dm',
  active_human_gm UUID REFERENCES players(id) ON DELETE SET NULL,
  current_round INTEGER NOT NULL DEFAULT 1 CHECK (current_round >= 1),
  created_by UUID REFERENCES players(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS campaign_members (
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  role campaign_role NOT NULL DEFAULT 'player',
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (campaign_id, player_id)
);

CREATE TABLE IF NOT EXISTS characters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
  sheet JSONB NOT NULL DEFAULT '{}'::jsonb,
  hp INTEGER NOT NULL DEFAULT 10,
  max_hp INTEGER NOT NULL DEFAULT 10 CHECK (max_hp > 0),
  temporary_hp INTEGER NOT NULL DEFAULT 0 CHECK (temporary_hp >= 0),
  armor_class INTEGER NOT NULL DEFAULT 10,
  damage_reduction INTEGER NOT NULL DEFAULT 0 CHECK (damage_reduction >= 0),
  status TEXT NOT NULL DEFAULT 'healthy' CHECK (status IN ('healthy', 'wounded', 'bloodied', 'critical', 'unconscious', 'dying', 'dead')),
  death_save_successes INTEGER NOT NULL DEFAULT 0 CHECK (death_save_successes BETWEEN 0 AND 3),
  death_save_failures INTEGER NOT NULL DEFAULT 0 CHECK (death_save_failures BETWEEN 0 AND 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS character_conditions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  condition TEXT NOT NULL CHECK (condition IN ('bleeding', 'poisoned', 'burning', 'stunned', 'blinded', 'frightened', 'exhausted', 'hacked', 'jammed', 'signal_jammed', 'malware_infected', 'EMP_shocked')),
  source TEXT NOT NULL DEFAULT '',
  expires_round INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (character_id, condition)
);

CREATE TABLE IF NOT EXISTS world_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  state JSONB NOT NULL DEFAULT '{}'::jsonb,
  round_number INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS action_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
  round_number INTEGER NOT NULL CHECK (round_number >= 1),
  action_text TEXT NOT NULL CHECK (char_length(action_text) BETWEEN 1 AND 1000),
  active BOOLEAN NOT NULL DEFAULT true,
  validated BOOLEAN NOT NULL DEFAULT false,
  resolution JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_action_per_player_round
ON action_submissions (campaign_id, player_id, round_number)
WHERE active;

CREATE TABLE IF NOT EXISTS dice_rolls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  action_submission_id UUID REFERENCES action_submissions(id) ON DELETE SET NULL,
  player_id UUID REFERENCES players(id) ON DELETE SET NULL,
  notation TEXT NOT NULL CHECK (char_length(notation) BETWEEN 2 AND 30),
  rolls JSONB NOT NULL,
  modifier INTEGER NOT NULL DEFAULT 0,
  total INTEGER NOT NULL,
  purpose TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS game_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  round_number INTEGER NOT NULL CHECK (round_number >= 1),
  event_type TEXT NOT NULL CHECK (char_length(event_type) BETWEEN 1 AND 40),
  body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 8000),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES players(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS player_campaign_status (
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  last_seen_event_id UUID REFERENCES game_events(id) ON DELETE SET NULL,
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (campaign_id, player_id)
);

CREATE TABLE IF NOT EXISTS campaign_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  through_round INTEGER NOT NULL,
  summary TEXT NOT NULL CHECK (char_length(summary) <= 12000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS campaign_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  job_type TEXT NOT NULL CHECK (job_type IN ('resolve_round', 'summarize_campaign', 'index_knowledge')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  error TEXT,
  locked_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS one_pending_resolve_job_per_campaign
ON campaign_jobs (campaign_id)
WHERE job_type = 'resolve_round' AND status IN ('pending', 'running');

CREATE TABLE IF NOT EXISTS dm_drafts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  round_number INTEGER NOT NULL,
  draft_body TEXT NOT NULL CHECK (char_length(draft_body) BETWEEN 1 AND 8000),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'edited', 'rejected')),
  reviewed_by UUID REFERENCES players(id) ON DELETE SET NULL,
  official_event_id UUID REFERENCES game_events(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS gm_takeover_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  key_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  claimed_by UUID REFERENCES players(id) ON DELETE SET NULL,
  created_by UUID REFERENCES players(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  filename TEXT NOT NULL CHECK (char_length(filename) BETWEEN 1 AND 255),
  source_type TEXT NOT NULL DEFAULT 'upload',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
  content TEXT NOT NULL CHECK (char_length(content) BETWEEN 1 AND 4000),
  qdrant_point_id UUID,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_campaign_members_player ON campaign_members(player_id);
CREATE INDEX IF NOT EXISTS idx_game_events_campaign_round ON game_events(campaign_id, round_number, created_at);
CREATE INDEX IF NOT EXISTS idx_action_submissions_campaign_round ON action_submissions(campaign_id, round_number);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_campaign ON knowledge_chunks(campaign_id);

-- Future RLS scaffold:
-- ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE campaign_members ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
-- Policies should use a per-request player id setting, e.g. current_setting('app.player_id', true),
-- once authentication/session context is implemented.
