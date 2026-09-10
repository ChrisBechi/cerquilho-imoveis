import sys

from app.config.event_config import BugProtection
from app.config.supabase import supabase
from app.services.listing_service import ListingsService


def find_invalid_listings():
    return (
        supabase
        .table("listings")
        .select("id, provider, code, title, current_price")
        .gt("current_price", BugProtection.MAX_PRICE)
        .execute()
        .data
        or []
    )


if __name__ == "__main__":
    invalid_listings = find_invalid_listings()
    print(f"Invalid listings found: {len(invalid_listings)}")
    for listing in invalid_listings:
        print(listing)

    if "--delete" in sys.argv:
        removed = ListingsService.remove_invalid_price_listings()
        print(f"Invalid listings removed: {removed}")
