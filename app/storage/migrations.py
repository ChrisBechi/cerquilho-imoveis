"""
Migrations para Supabase - Schema necessário para o sistema de eventos.

Executar estas queries no console SQL do Supabase para preparar o banco.

Ou usar: python app/storage/migrations.py
"""

# ==================================================
# MIGRATION 1: Adicionar coluna last_seen_at
# ==================================================
# Executed: ALTER TABLE listings ADD COLUMN last_seen_at TIMESTAMP;
# Purpose: Rastrear quando imóvel foi visto pela última vez no scraping

MIGRATION_ADD_LAST_SEEN_AT = """
-- Adiciona coluna last_seen_at à tabela listings
-- Esta coluna rastreia quando o imóvel foi visto pela última vez
-- Usada para detectar desaparecimento/aluguel

ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT NOW();

-- Índice para otimizar queries de detecção de rented
CREATE INDEX IF NOT EXISTS idx_listings_last_seen_at 
ON listings(last_seen_at) 
WHERE is_active = true;
"""

# ==================================================
# MIGRATION 2: Adicionar coluna rented_at
# ==================================================
# Purpose: Marcar quando imóvel foi alugado

MIGRATION_ADD_RENTED_AT = """
-- Adiciona coluna rented_at à tabela listings
-- Marca quando o imóvel foi marcado como alugado
-- Protege contra evento rented duplicado

ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS rented_at TIMESTAMPTZ;

-- Índice para otimizar queries
CREATE INDEX IF NOT EXISTS idx_listings_rented_at 
ON listings(rented_at);
"""

# ==================================================
# MIGRATION 3: Adicionar coluna is_active
# ==================================================
# Purpose: Soft delete - marca imóvel como inativo

MIGRATION_ADD_IS_ACTIVE = """
-- Adiciona coluna is_active à tabela listings
-- Substitui delete físico
-- Padrão: true (ativo)

ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Índice para otimizar queries
CREATE INDEX IF NOT EXISTS idx_listings_is_active 
ON listings(is_active);
"""

# ==================================================
# MIGRATION 4: Adicionar coluna provider_status
# ==================================================
# Purpose: Rastrear status da última execução do provider

MIGRATION_ADD_PROVIDER_STATUS = """
-- Adiciona coluna provider_status à tabela listings
-- Valores: 'success', 'failed', null
-- Protege contra rented detection quando provider falha

ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS provider_last_status TEXT;

ALTER TABLE listings 
ADD COLUMN IF NOT EXISTS provider_last_execution TIMESTAMPTZ;
"""

# ==================================================
# MIGRATION 5: Enhancear tabela listing_events
# ==================================================
# Purpose: Adicionar campos para melhor rastreamento

MIGRATION_ENHANCE_LISTING_EVENTS = """
-- Adiciona campos adicionais à tabela listing_events
-- Para melhor rastreamento de eventos

ALTER TABLE listing_events 
ADD COLUMN IF NOT EXISTS old_price_label TEXT;

ALTER TABLE listing_events 
ADD COLUMN IF NOT EXISTS new_price_label TEXT;

-- Índice para otimizar queries de eventos pendentes
CREATE INDEX IF NOT EXISTS idx_listing_events_notified 
ON listing_events(notified) 
WHERE notified = false;

-- Índice para otimizar queries por listing
CREATE INDEX IF NOT EXISTS idx_listing_events_listing_id 
ON listing_events(listing_id);
"""

# ==================================================
# MIGRATION 6: Criar tabela provider_execution_log
# ==================================================
# Purpose: Log de execução dos providers

MIGRATION_CREATE_PROVIDER_LOG = """
-- Cria tabela para log de execução de providers
-- Permite ratrear sucesso/falha de cada execução

CREATE TABLE IF NOT EXISTS provider_execution_log (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    provider_name TEXT NOT NULL,
    execution_start TIMESTAMPTZ DEFAULT NOW(),
    execution_end TIMESTAMPTZ,
    status TEXT CHECK (status IN ('success', 'failed', 'partial')),
    listings_found INT DEFAULT 0,
    listings_created INT DEFAULT 0,
    listings_updated INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para otimizar queries
CREATE INDEX IF NOT EXISTS idx_provider_log_provider_name 
ON provider_execution_log(provider_name);

CREATE INDEX IF NOT EXISTS idx_provider_log_status 
ON provider_execution_log(status);
"""

# ==================================================
# MIGRATION 7: Criar tabela event_dedup_cache
# ==================================================
# Purpose: Evitar eventos duplicados

MIGRATION_CREATE_EVENT_DEDUP = """
-- Cria tabela de cache para evitar eventos duplicados
-- Hash(provider + code + event_type + timestamp_min) = event_id

CREATE TABLE IF NOT EXISTS event_dedup_cache (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),
    
    UNIQUE(listing_id, event_type, event_hash)
);

-- Índice para cleanup automático
CREATE INDEX IF NOT EXISTS idx_event_dedup_expires_at 
ON event_dedup_cache(expires_at);
"""

# ==================================================
# QUERIES DE VERIFICAÇÃO
# ==================================================

QUERY_CHECK_MISSING_FIELDS = """
-- Verifica quais colunas faltam em listings
SELECT 
    CASE 
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'listings' AND column_name = 'last_seen_at') THEN '❌ last_seen_at'
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'listings' AND column_name = 'rented_at') THEN '❌ rented_at'
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'listings' AND column_name = 'is_active') THEN '❌ is_active'
        WHEN NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'listings' AND column_name = 'provider_last_status') THEN '❌ provider_last_status'
        ELSE '✅ Todos os campos presentes'
    END AS status;
"""

# ==================================================
# QUERY PARA DETECÇÃO DE RENTED (TESTE)
# ==================================================

QUERY_DETECT_RENTED_CANDIDATES = """
-- Identifica imóveis candidatos a marcar como alugado
-- (desapareceram há mais de 24h)

SELECT 
    l.id,
    l.provider,
    l.code,
    l.title,
    l.last_seen_at,
    NOW() - l.last_seen_at AS time_disappeared,
    l.is_active
FROM listings l
WHERE 
    l.is_active = true
    AND l.rented_at IS NULL  -- Ainda não foi marcado como alugado
    AND (NOW() - l.last_seen_at) > INTERVAL '24 hours'  -- Sumiu há mais de 24h
    AND l.last_seen_at IS NOT NULL
ORDER BY l.last_seen_at ASC;
"""

# ==================================================
# UTILITY FUNCTIONS
# ==================================================

def get_all_migrations():
    """Retorna lista de todas as migrations"""
    return [
        MIGRATION_ADD_LAST_SEEN_AT,
        MIGRATION_ADD_RENTED_AT,
        MIGRATION_ADD_IS_ACTIVE,
        MIGRATION_ADD_PROVIDER_STATUS,
        MIGRATION_ENHANCE_LISTING_EVENTS,
        MIGRATION_CREATE_PROVIDER_LOG,
        MIGRATION_CREATE_EVENT_DEDUP,
    ]


def print_migrations():
    """Imprime todas as migrations para copiar/colar no Supabase"""
    for i, migration in enumerate(get_all_migrations(), 1):
        print(f"\n{'='*60}")
        print(f"MIGRATION {i}")
        print(f"{'='*60}")
        print(migration)
        print()


if __name__ == "__main__":
    print_migrations()
