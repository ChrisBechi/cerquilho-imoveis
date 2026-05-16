from app.providers.terrazzo_provider import TerrazzoProvider


def test_fetch_listings():

    provider = TerrazzoProvider()

    listings = provider.fetch_listings()

    assert len(listings) > 0

    first = listings[0]

    assert first.code != ""
    assert first.title != ""
    assert first.url.startswith("https://")