"""Refresh complete Scudeler galleries without events or notifications."""

import argparse
from urllib.parse import urlparse

from app.config.supabase import supabase
from app.providers.scudeler_provider import ScudelerProvider
from app.services.listing_service import ListingsService


def refresh_galleries(apply=False, codes=None):
    query = (supabase.table("listings").select("id,code,url")
             .eq("provider", ScudelerProvider.NAME).is_("rented_at", "null"))
    if codes:
        query = query.in_("code", codes)
    listings = query.execute().data or []
    provider = ScudelerProvider()
    added = 0
    failures = 0

    for listing in listings:
        source_id = urlparse(listing["url"]).path.rstrip("/").rsplit("/", 1)[-1]
        images = provider.fetch_listing_images(source_id)
        if images is None:
            failures += 1
            continue

        listing_id = listing["id"]
        existing = (supabase.table("listing_images").select("image_url")
                    .eq("listing_id", listing_id).execute().data or [])
        existing_urls = {row["image_url"] for row in existing}
        expected_urls = {ListingsService.stored_image_url(listing_id, url)
                         for url in images}
        print(f"[GALLERY {'APPLY' if apply else 'PREVIEW'}] "
              f"code={listing['code']} listing_id={listing_id} "
              f"saved={len(existing_urls)} source={len(images)} "
              f"missing={len(expected_urls - existing_urls)}", flush=True)

        if apply:
            added += ListingsService.sync_images(listing_id, images)
            saved = (supabase.table("listing_images").select("image_url")
                     .eq("listing_id", listing_id).execute().data or [])
            saved_urls = {row["image_url"] for row in saved}
            if not expected_urls.issubset(saved_urls):
                failures += 1
                print(f"[GALLERY INCOMPLETE] code={listing['code']} "
                      f"missing={len(expected_urls - saved_urls)}", flush=True)
            else:
                print(f"[GALLERY VERIFIED] code={listing['code']} "
                      f"saved={len(saved_urls)}", flush=True)

    print(f"[GALLERY SUMMARY] checked={len(listings)} added={added} "
          f"failed={failures} apply={apply}", flush=True)
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Upload and save images; default is a read-only preview.")
    parser.add_argument("--code", action="append", help="Limit to a property code.")
    arguments = parser.parse_args()
    raise SystemExit(1 if refresh_galleries(arguments.apply, arguments.code) else 0)
