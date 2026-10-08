from app.config.supabase import supabase
from app.services.listing_service import ListingsService


def restore_rented_galleries() -> tuple[int, int]:
    bucket = supabase.storage.from_(ListingsService.image_bucket_name())
    rented_image = ListingsService.rented_image_url()
    listings = (
        supabase
        .table("listings")
        .select("id")
        .filter("rented_at", "not.is", "null")
        .execute()
        .data
        or []
    )

    restored_listings = 0
    restored_images = 0

    for listing in listings:
        listing_id = listing["id"]
        files = bucket.list(f"listings/{listing_id}") or []
        existing = (
            supabase
            .table("listing_images")
            .select("image_url")
            .eq("listing_id", listing_id)
            .execute()
            .data
            or []
        )
        existing_urls = {item["image_url"] for item in existing}
        recovered_urls = []

        for file in files:
            name = file.get("name")
            if not name or name.endswith("/"):
                continue
            url = bucket.get_public_url(f"listings/{listing_id}/{name}")
            if url != rented_image and url not in existing_urls:
                recovered_urls.append(url)

        if recovered_urls:
            supabase.table("listing_images").insert([
                {"listing_id": listing_id, "image_url": url}
                for url in recovered_urls
            ]).execute()
            restored_listings += 1
            restored_images += len(recovered_urls)

        ListingsService.prepend_rented_image(listing_id)

    print(
        f"Rented galleries restored: listings={restored_listings} "
        f"images={restored_images}"
    )
    return restored_listings, restored_images


if __name__ == "__main__":
    restore_rented_galleries()
