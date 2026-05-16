from app.services.listing_service import ListingsService

payload = {

    "provider":
        "Teste",

    "code":
        "ABC123",

    "title":
        "Apartamento Luxuoso",

    "neighborhood":
        "Centro",

    "bedrooms":
        3,

    "bathrooms":
        2,

    "area":
        120,

    "url":
        "https://teste.com/imovel-x",

    "thumbnail_url":
        "https://picsum.photos/800/700",

    "current_price":
        2500
}

# ====================================
# PRIMEIRA EXECUÇÃO
# ====================================

ListingsService.upsert_listing(
    payload
)

# ====================================
# ALTERA PREÇO
# ====================================

payload["current_price"] = 2200

ListingsService.upsert_listing(
    payload
)

print("DONE")