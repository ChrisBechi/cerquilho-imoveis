from app.config.supabase import (
    supabase
)

payload = {

    "provider":
        "Prime Imóveis",

    "title":
        "Casa moderna no centro",

    "neighborhood":
        "Centro",

    "bedrooms":
        3,

    "bathrooms":
        2,

    "area":
        120,

    "url":
        "https://teste.com/imovel-1",

    "thumbnail_url":
        "https://picsum.photos/800/600",

    "current_price":
        2500
}

response = (

    supabase

    .table("listings")

    .insert(payload)

    .execute()
)

print(response.data)