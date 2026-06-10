-- ============================================================
-- SIMMOON PostgreSQL Schema
-- Database: simmoon
-- Purpose: Asset metadata, generation tracking, game state
-- ============================================================

-- Drop existing tables (clean install)
DROP TABLE IF EXISTS colony_population CASCADE;
DROP TABLE IF EXISTS colony_buildings CASCADE;
DROP TABLE IF EXISTS colony_state CASCADE;
DROP TABLE IF EXISTS votes CASCADE;
DROP TABLE IF EXISTS generation_assets CASCADE;
DROP TABLE IF EXISTS generations CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ------------------------------------------------------------
-- 1. CATEGORIES
-- Lookup table for asset category taxonomy
-- ------------------------------------------------------------
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(32) NOT NULL UNIQUE,
    label       VARCHAR(64) NOT NULL,
    icon        VARCHAR(8)  NOT NULL DEFAULT '📁',
    output_dir  VARCHAR(128) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE categories IS 'Asset category taxonomy (businesses, vehicles, greenhouses, etc.)';

-- ------------------------------------------------------------
-- 2. ASSETS
-- Each generated image asset with full metadata
-- ------------------------------------------------------------
CREATE TABLE assets (
    id              SERIAL PRIMARY KEY,
    asset_id        VARCHAR(32) NOT NULL UNIQUE,
    name            VARCHAR(128) NOT NULL,
    category_id     INT NOT NULL REFERENCES categories(id),
    prompt          TEXT NOT NULL,
    negative_prompt TEXT NOT NULL DEFAULT '',
    tags            TEXT[],

    -- File paths (relative to project root)
    path_original   VARCHAR(256) NOT NULL,
    path_pixel      VARCHAR(256),

    -- File integrity
    file_size_bytes BIGINT,
    file_hash       VARCHAR(64),
    mime_type       VARCHAR(32) NOT NULL DEFAULT 'image/png',

    -- Generation params
    width           INT NOT NULL DEFAULT 512,
    height          INT NOT NULL DEFAULT 512,
    steps           INT NOT NULL DEFAULT 28,
    cfg_scale       REAL NOT NULL DEFAULT 9.0,
    sampler         VARCHAR(32) NOT NULL DEFAULT 'euler_ancestral',

    -- Backend info
    backend         VARCHAR(32) NOT NULL DEFAULT 'comfyui',
    model           VARCHAR(128) NOT NULL DEFAULT 'v1-5-pruned-emaonly.safetensors',
    checkpoint      VARCHAR(128),

    -- Status
    status          VARCHAR(16) NOT NULL DEFAULT 'generated',
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pixelated_at    TIMESTAMPTZ,

    -- Game data (for future use)
    game_cost       INT NOT NULL DEFAULT 0,
    game_upkeep     INT NOT NULL DEFAULT 0,
    game_power      INT NOT NULL DEFAULT 0,
    game_water      INT NOT NULL DEFAULT 0,
    game_oxygen     INT NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assets_category   ON assets(category_id);
CREATE INDEX idx_assets_status     ON assets(status);
CREATE INDEX idx_assets_tags       ON assets USING GIN(tags);
CREATE INDEX idx_assets_generated  ON assets(generated_at);

COMMENT ON TABLE assets IS 'Generated image assets with full metadata, prompts, file integrity, and game parameters';

-- ------------------------------------------------------------
-- 3. GENERATIONS
-- Tracks each generation batch/run
-- ------------------------------------------------------------
CREATE TABLE generations (
    id              SERIAL PRIMARY KEY,
    generation_name VARCHAR(128) NOT NULL,
    backend         VARCHAR(32) NOT NULL DEFAULT 'comfyui',
    model           VARCHAR(128) NOT NULL DEFAULT 'v1-5-pruned-emaonly.safetensors',
    total_images    INT NOT NULL DEFAULT 0,
    succeeded       INT NOT NULL DEFAULT 0,
    failed          INT NOT NULL DEFAULT 0,
    duration_seconds REAL,
    
    -- Config snapshot
    config_json     JSONB,
    
    -- Status
    status          VARCHAR(16) NOT NULL DEFAULT 'running',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_generations_status ON generations(status);
CREATE INDEX idx_generations_date   ON generations(started_at);

COMMENT ON TABLE generations IS 'Tracks each generation batch/run with config snapshot and results';

-- ------------------------------------------------------------
-- 4. GENERATION_ASSETS (junction)
-- Many-to-many between generations and the assets they produced
-- ------------------------------------------------------------
CREATE TABLE generation_assets (
    generation_id   INT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
    asset_id        INT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    prompt_order    INT,
    seed_used       BIGINT,
    generation_time REAL,
    PRIMARY KEY (generation_id, asset_id)
);

CREATE INDEX idx_ga_generation ON generation_assets(generation_id);
CREATE INDEX idx_ga_asset      ON generation_assets(asset_id);

COMMENT ON TABLE generation_assets IS 'Junction table linking each generation batch to its produced assets';

-- ------------------------------------------------------------
-- 5. COLONY STATE
-- Tracks game state per turn for the lunar colony simulation
-- ------------------------------------------------------------
CREATE TABLE colony_state (
    id              SERIAL PRIMARY KEY,
    turn            INT NOT NULL DEFAULT 1,
    population      INT NOT NULL DEFAULT 0,
    credits         INT NOT NULL DEFAULT 1000,
    minerals        INT NOT NULL DEFAULT 500,
    energy          INT NOT NULL DEFAULT 200,
    water           INT NOT NULL DEFAULT 300,
    oxygen          INT NOT NULL DEFAULT 400,
    food            INT NOT NULL DEFAULT 200,
    colony_morale   REAL NOT NULL DEFAULT 0.5,
    total_buildings INT NOT NULL DEFAULT 0,
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_colony_turn ON colony_state(turn);

COMMENT ON TABLE colony_state IS 'Game state per turn: resources, population, buildings, and morale';

-- Insert initial colony state
INSERT INTO colony_state (turn, population, credits, minerals, energy, water, oxygen, food, total_buildings, note)
VALUES (1, 0, 1000, 500, 200, 300, 400, 200, 0, 'Colony established. Awaiting first buildings.');

-- ------------------------------------------------------------
-- 6. COLONY BUILDINGS
-- Tracks placed buildings in the colony grid
-- ------------------------------------------------------------
CREATE TABLE colony_buildings (
    id              SERIAL PRIMARY KEY,
    asset_id        VARCHAR(32) REFERENCES assets(asset_id) ON DELETE SET NULL,
    building_name   VARCHAR(128) NOT NULL,
    category_slug   VARCHAR(32) NOT NULL,
    position_x      INT NOT NULL DEFAULT 0,
    position_y      INT NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    built_at_turn   INT NOT NULL DEFAULT 1,
    game_cost       INT NOT NULL DEFAULT 0,
    game_upkeep     INT NOT NULL DEFAULT 0,
    game_power      INT NOT NULL DEFAULT 0,
    game_water      INT NOT NULL DEFAULT 0,
    game_oxygen     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_buildings_position ON colony_buildings(position_x, position_y);
CREATE INDEX idx_buildings_active   ON colony_buildings(is_active);
CREATE INDEX idx_buildings_category ON colony_buildings(category_slug);

COMMENT ON TABLE colony_buildings IS 'Buildings placed in the colony grid by the player';

-- ------------------------------------------------------------
-- 7. VOTES
-- Persistent voting system (migrated from localStorage)
-- ------------------------------------------------------------
CREATE TABLE votes (
    id              SERIAL PRIMARY KEY,
    asset_id        VARCHAR(32) NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    vote_value      INT NOT NULL CHECK (vote_value >= 1 AND vote_value <= 5),
    session_id      VARCHAR(64) NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asset_id, session_id)
);

CREATE INDEX idx_votes_asset  ON votes(asset_id);
CREATE INDEX idx_votes_session ON votes(session_id);

COMMENT ON TABLE votes IS 'User votes (1-5 stars) per asset, persisted from viewer.html';

-- ------------------------------------------------------------
-- 8. UPDATE TRIGGERS
-- Auto-update updated_at columns
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_assets_updated_at
    BEFORE UPDATE ON assets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_colony_state_updated_at
    BEFORE UPDATE ON colony_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_votes_updated_at
    BEFORE UPDATE ON votes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ------------------------------------------------------------
-- 9. DAILY SUMMARIES
-- Memorias del proyecto: resúmenes diarios para agentes
-- ------------------------------------------------------------
CREATE TABLE daily_summaries (
    id              SERIAL PRIMARY KEY,
    summary_date    DATE NOT NULL UNIQUE,
    title           VARCHAR(256) NOT NULL,
    content         TEXT NOT NULL,
    
    -- Metadatos del día
    assets_created  INT NOT NULL DEFAULT 0,
    assets_total    INT NOT NULL DEFAULT 0,
    services_active INT NOT NULL DEFAULT 0,
    services_total  INT NOT NULL DEFAULT 0,
    agents_active   INT NOT NULL DEFAULT 0,
    agents_total    INT NOT NULL DEFAULT 0,
    alerts_count    INT NOT NULL DEFAULT 0,
    
    -- Tags para búsqueda
    tags            TEXT[],
    
    -- Proyecto/contexto
    project         VARCHAR(64) NOT NULL DEFAULT 'SIMMOON',
    session_id      VARCHAR(128),
    created_by      VARCHAR(64) NOT NULL DEFAULT 'Agatha Actas',
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_summaries_date     ON daily_summaries(summary_date);
CREATE INDEX idx_summaries_project  ON daily_summaries(project);
CREATE INDEX idx_summaries_tags     ON daily_summaries USING GIN(tags);

COMMENT ON TABLE daily_summaries IS 'Daily project summaries for agent memory — resúmenes diarios que permiten a los agentes recordar el trabajo anterior';

-- Trigger auto-update para daily_summaries
CREATE TRIGGER trg_daily_summaries_updated_at
    BEFORE UPDATE ON daily_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ------------------------------------------------------------
-- 10. AGENT MEMORY (memoria compartida entre agentes)
-- Permite que Hermes, OpenHuman y otros agentes compartan contexto
-- ------------------------------------------------------------
CREATE TABLE agent_memory (
    id              SERIAL PRIMARY KEY,
    
    -- Identificación del agente
    agent_name      VARCHAR(64) NOT NULL,  -- 'hermes', 'openhuman', 'buffy', etc.
    session_id      VARCHAR(128),          -- ID de sesión del agente
    
    -- Tipo de memoria
    memory_type     VARCHAR(32) NOT NULL,  -- 'context', 'fact', 'preference', 'conversation', 'task'
    
    -- Contenido de la memoria
    key_name        VARCHAR(128) NOT NULL, -- Identificador único del dato
    content         TEXT NOT NULL,         -- Valor/contenido
    content_json    JSONB,                 -- Contenido estructurado opcional
    
    -- Metadatos
    tags            TEXT[],                -- Tags para búsqueda
    importance      INT NOT NULL DEFAULT 3,-- 1=baja, 5=crítica (importancia)
    expires_at      TIMESTAMPTZ,           -- Expiración opcional
    
    -- Proveniencia
    created_by      VARCHAR(64) NOT NULL,  -- Qué agente creó esto
    project         VARCHAR(64) NOT NULL DEFAULT 'SIMMOON',
    
    -- Relaciones opcionales
    related_agent   VARCHAR(64),           -- Agente relacionado
    parent_memory_id INT,                  -- Memoria padre (para hilos de conversación)
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para búsqueda eficiente
CREATE INDEX idx_memory_agent      ON agent_memory(agent_name);
CREATE INDEX idx_memory_type       ON agent_memory(memory_type);
CREATE INDEX idx_memory_session    ON agent_memory(session_id);
CREATE INDEX idx_memory_key        ON agent_memory(key_name);
CREATE INDEX idx_memory_tags       ON agent_memory USING GIN(tags);
CREATE INDEX idx_memory_created    ON agent_memory(created_at DESC);
CREATE INDEX idx_memory_importance ON agent_memory(importance DESC);

-- Clave única: un agente solo puede tener una entrada por key_name
CREATE UNIQUE INDEX idx_memory_unique ON agent_memory(agent_name, key_name);

COMMENT ON TABLE agent_memory IS 'Memoria compartida entre agentes (Hermes, OpenHuman, Buffy, etc.) permite persistir contexto, hechos, preferencias y estado entre sesiones';

-- ------------------------------------------------------------
-- 11. COLONY POPULATION (generated population per turn)
-- ------------------------------------------------------------
CREATE TABLE colony_population (
    id              SERIAL PRIMARY KEY,
    turn            INT NOT NULL,
    total           INT NOT NULL DEFAULT 0,
    workers         INT NOT NULL DEFAULT 0,
    scientists      INT NOT NULL DEFAULT 0,
    engineers       INT NOT NULL DEFAULT 0,
    colonists       INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_population_turn ON colony_population(turn);

COMMENT ON TABLE colony_population IS 'Population breakdown per turn for the lunar colony';
