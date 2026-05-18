"""
Configuração centralizada para o sistema de eventos de imóveis.

Define tipos de eventos oficiais, regras de detecção e proteção contra bugs.
"""

from enum import Enum
from typing import Final

# ============================================
# TIPOS DE EVENTOS OFICIAIS
# ============================================
# NÃO VARIAR. NÃO CRIAR ALIASES. COMPATÍVEL COM FRONTEND.

class ListingEventType(str, Enum):
    """Tipos de eventos que o frontend espera"""
    CREATED = "created"          # Novo imóvel apareceu
    PRICE_DROP = "price_drop"    # Preço diminuiu
    PRICE_UP = "price_up"        # Preço aumentou
    RENTED = "rented"            # Imóvel foi alugado/desapareceu


# ============================================
# CONFIGURAÇÃO DE TIMEOUTS E LIMITES
# ============================================

class RentedDetectionConfig:
    """Configuração para fallback de detecção de imóvel alugado"""
    
    # Fallback quando a execução não informa run_started_at.
    # O pipeline principal usa regra absoluta: se não veio no provider bem-sucedido,
    # marca como alugado imediatamente.
    HOURS_BEFORE_RENTED: Final[int] = 24
    
    # Quantas execuções do provider sem aparecer (backup)
    SCRAPES_BEFORE_RENTED: Final[int] = 3
    
    # Não marcar como rented se:
    # - provider falhou (sem dados válidos)
    # - provider retornou vazio/partial


# ============================================
# PROTEÇÃO CONTRA BUGS
# ============================================

class BugProtection:
    """Proteções contra falsos positivos e bugs"""
    
    # Preço mínimo válido (em centavos) - evita preço 0
    MIN_PRICE: Final[int] = 1000  # R$ 10
    
    # Preço máximo (evita dados muito grandes)
    MAX_PRICE: Final[int] = 100_000_000  # R$ 1.000.000
    
    # Comprimento mínimo de título
    MIN_TITLE_LENGTH: Final[int] = 5
    
    # Máximo de imagens
    MAX_IMAGES: Final[int] = 50
    
    # Máximo de bedrooms
    MAX_BEDROOMS: Final[int] = 15
    
    # Máximo de bathrooms
    MAX_BATHROOMS: Final[int] = 10


# ============================================
# PROTEÇÃO CONTRA DUPLICADOS
# ============================================

class DuplicateProtection:
    """Evita criar eventos duplicados"""
    
    # Intervalo mínimo entre eventos do mesmo tipo para mesmo imóvel
    # (em minutos) - evita spam quando preço flutua
    MIN_INTERVAL_PRICE_CHANGE: Final[int] = 5
    MIN_INTERVAL_RENTED: Final[int] = 60
    
    # Se houve price_drop há menos de X minutos,
    # não criar price_up (e vice-versa) - indica flutuação
    IGNORE_OPPOSITE_WITHIN_MINUTES: Final[int] = 2


# ============================================
# CAMPOS DO SCHEMA NECESSÁRIOS
# ============================================

class DatabaseSchema:
    """Define campos esperados no banco"""
    
    # Campos que DEVEM existir em 'listings'
    REQUIRED_LISTING_FIELDS = {
        "id",
        "provider",
        "code",
        "title",
        "price_label",
        "current_price",
        "url",
        "created_at",
        "updated_at",
        "last_seen_at",  # ← NOVO: quando foi visto pela última vez
    }
    
    # Campos que DEVEM existir em 'listing_events'
    REQUIRED_EVENT_FIELDS = {
        "id",
        "listing_id",
        "type",  # created, price_drop, price_up, rented
        "title",
        "description",
        "old_price",
        "new_price",
        "notified",
        "created_at",
    }
    
    # Campos que DEVEM existir em 'listing_price_history'
    REQUIRED_PRICE_HISTORY_FIELDS = {
        "id",
        "listing_id",
        "price",
        "created_at",
    }


# ============================================
# MENSAGENS E DESCRIÇÕES
# ============================================

class EventMessages:
    """Mensagens padrão para eventos"""
    
    CREATED = {
        "title": "Imóvel adicionado",
        "description": "Um novo imóvel foi adicionado ao sistema",
    }
    
    PRICE_DROP = {
        "title": "Preço reduzido",
        "description": "O preço deste imóvel foi reduzido",
    }
    
    PRICE_UP = {
        "title": "Preço aumentado",
        "description": "O preço deste imóvel foi aumentado",
    }
    
    RENTED = {
        "title": "Imóvel alugado",
        "description": "Este imóvel foi alugado e desapareceu dos anúncios",
    }
