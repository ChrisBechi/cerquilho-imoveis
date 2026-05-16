from app.providers.terrazzo_provider import TerrazzoProvider
from app.services.listing_comparator import ListingComparator


def test_detect_new_listings():

    provider = TerrazzoProvider()

    listings = provider.fetch_listings()

    comparator = ListingComparator()

    new_listings = comparator.get_new_listings(
        listings
    )

    assert isinstance(new_listings, list)