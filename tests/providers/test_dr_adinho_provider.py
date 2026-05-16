from app.providers.dr_adinho_provider import (
    DrAdinhoProvider
)


def test_fetch_listings():

    provider = DrAdinhoProvider()

    listings = provider.fetch_listings()

    assert len(listings) > 0

    first = listings[0]

    assert first.title != ""

    assert first.url != ""

    assert first.code != ""

    assert first.thumbnail_url != ""