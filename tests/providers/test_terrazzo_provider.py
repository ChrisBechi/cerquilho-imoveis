from bs4 import BeautifulSoup

from app.providers.terrazzo_provider import TerrazzoProvider


def test_extract_image_url_supports_current_markup():
    soup = BeautifulSoup(
        '<a href="#"><img src="https://example.com/photo.jpeg"></a>',
        "lxml",
    )

    assert (
        TerrazzoProvider.extract_image_url(soup.a)
        == "https://example.com/photo.jpeg"
    )


def test_extract_image_url_prefers_legacy_lazy_source():
    soup = BeautifulSoup(
        '<img src="data:image/svg+xml,placeholder" '
        'data-src="https://example.com/real.jpeg">',
        "lxml",
    )

    assert (
        TerrazzoProvider.extract_image_url(soup.img)
        == "https://example.com/real.jpeg"
    )


def test_fetch_listings():

    provider = TerrazzoProvider()

    listings = provider.fetch_listings()

    assert len(listings) > 0

    first = listings[0]

    assert first.code != ""
    assert first.title != ""
    assert first.url.startswith("https://")
