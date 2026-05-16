import hashlib


def generate_listing_hash(listing) -> str:

    content = (
        f"{listing.title}|"
        f"{listing.price_label}|"
        f"{listing.bedrooms}|"
        f"{listing.bathrooms}|"
        f"{listing.property_type}"
    )

    return hashlib.md5(
        content.encode("utf-8")
    ).hexdigest()