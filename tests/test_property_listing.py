from app.models.property_listing import PropertyListing


def test_property_listing_creation():
    listing = PropertyListing(
        provider="Terrazzo",
        code="418",
        title="Casa residencial",
        price_label="R$ 1.600,00",
        bedrooms=2,
        bathrooms=2,
        property_type="Residencial",
        published_at="2 meses atrás",
        url="https://example.com"
    )

    assert listing.code == "418"
    assert listing.bedrooms == 2
