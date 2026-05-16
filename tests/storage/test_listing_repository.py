from app.models.property_listing import PropertyListing
from app.storage.database import get_connection
from app.storage.listing_repository import ListingRepository


def clear_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("DELETE FROM listings")

    connection.commit()

    connection.close()


def test_save_and_exists():

    clear_database()

    repository = ListingRepository()

    listing = PropertyListing(
        provider="Test",
        code="123",
        title="Casa Teste",
        price_label="1000",
        bedrooms=2,
        bathrooms=1,
        property_type="Casa",
        published_at="Hoje",
        url="https://example.com"
    )

    repository.save(listing)

    exists = repository.exists(
        "Test",
        "123"
    )

    assert exists is True
