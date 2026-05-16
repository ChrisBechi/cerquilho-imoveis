from fastapi import FastAPI

from app.storage.database import (
    get_connection
)

app = FastAPI()


@app.get("/listings")
def get_listings():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            provider,
            code,
            title,
            price,
            bedrooms,
            bathrooms,
            property_type,
            published_at,
            url,
            thumbnail_url
        FROM listings
        WHERE is_active = 1
        ORDER BY last_seen DESC
    """)

    rows = cursor.fetchall()

    connection.close()

    listings = []

    for row in rows:

        listings.append({
            "provider": row[0],
            "code": row[1],
            "title": row[2],
            "price": row[3],
            "bedrooms": row[4],
            "bathrooms": row[5],
            "property_type": row[6],
            "published_at": row[7],
            "url": row[8],
            "thumbnail_url": row[9],
        })

    return listings