import json
import time
import urllib.error
import urllib.request

CARDS_FILE = "../data/cards.json"
TPIP_LOOKUP_FILE = "../data/tpip_lookup.json"

BATCH_SIZE = 75

HEADERS = {
    "User-Agent": "JakeFalloutTracker/1.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

TCGPLAYER_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def get_scryfall_batch(cards):

    identifiers = []

    for card in cards:

        set_code = str(
            card.get("set", "")
        ).strip()

        collector_number = str(
            card.get("number", "")
        ).strip()

        if not set_code or not collector_number:
            continue

        # SLD Rainbow Foil cards use a star in
        # Scryfall's collector number.
        if (
            set_code.upper() == "SLD"
            and collector_number in {
                "790",
                "795",
                "796"
            }
        ):
            collector_number += "★"

        # TPIP cards use the separate TCGplayer
        # pricing system.
        if set_code.upper() == "TPIP":
            continue

        identifiers.append({
            "set": set_code.lower(),
            "collector_number": collector_number
        })

    if not identifiers:
        return {}, []

    url = "https://api.scryfall.com/cards/collection"

    payload = json.dumps({
        "identifiers": identifiers
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers=HEADERS,
        method="POST"
    )

    for attempt in range(3):

        try:

            with urllib.request.urlopen(request) as response:

                if response.status != 200:
                    return {}, [
                        f"HTTP {response.status}"
                    ]

                data = json.loads(
                    response.read().decode("utf-8")
                )

            results = {}

            for card in data.get("data", []):

                set_code = str(
                    card.get("set", "")
                ).lower()

                collector_number = str(
                    card.get("collector_number", "")
                )

                key = (
                    set_code,
                    collector_number
                )

                prices = card.get("prices", {})

                results[key] = {
                    "usd": prices.get("usd") or "",
                    "usd_foil": prices.get("usd_foil") or ""
                }

            not_found = []

            for missing in data.get("not_found", []):

                not_found.append(
                    str(missing)
                )

            return results, not_found

        except urllib.error.HTTPError as error:

            if error.code == 429:

                wait_time = 2 ** attempt

                print(
                    f"HTTP 429. "
                    f"Waiting {wait_time} seconds...",
                    flush=True
                )

                time.sleep(wait_time)

                continue

            return {}, [
                f"HTTP {error.code}"
            ]

        except Exception as error:

            return {}, [
                str(error)
            ]

    return {}, [
        "HTTP 429 after 3 attempts"
    ]

def update_tpip_prices(cards):

    print(
        "",
        flush=True
    )

    print(
        "Loading TPIP lookup...",
        flush=True
    )

    with open(
        TPIP_LOOKUP_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        tpip_lookup = json.load(file)

    print(
        f"Found {len(tpip_lookup)} TPIP cards.",
        flush=True
    )

    total_updated = 0
    total_no_product = 0
    total_errors = 0

    for index, card in enumerate(cards, start=1):

        set_code = str(
            card.get("set", "")
        ).strip().upper()

        if set_code != "TPIP":
            continue

        number = str(
            card.get("number", "")
        ).strip()

        print(
            f"[{index}] TPIP {number}",
            flush=True
        )

        lookup = tpip_lookup.get(number)

        if not lookup:

            print(
                "    No TPIP lookup entry.",
                flush=True
            )

            total_errors += 1
            continue

        product_id = lookup.get("product_id")

        if not product_id:

            print(
                "    No TCGplayer Product ID.",
                flush=True
            )

            total_no_product += 1
            continue

        print(
            f"    Product ID: {product_id}",
            flush=True
        )

        try:

            details_url = (
                "https://mp-search-api.tcgplayer.com/"
                f"v2/product/{product_id}/details"
            )

            details_request = urllib.request.Request(
                details_url,
                headers=TCGPLAYER_HEADERS
            )

            with urllib.request.urlopen(
                details_request
            ) as response:

                if response.status != 200:

                    print(
                        f"    Details HTTP {response.status}",
                        flush=True
                    )

                    total_errors += 1
                    continue

                details = json.loads(
                    response.read().decode("utf-8")
                )

            normal_sku = None
            foil_sku = None

            for sku in details.get("skus", []):

                if (
                    sku.get("language") == "English"
                    and sku.get("condition") == "Near Mint"
                ):

                    if sku.get("variant") == "Normal":
                        normal_sku = sku.get("sku")

                    elif sku.get("variant") == "Foil":
                        foil_sku = sku.get("sku")

            sku_ids = []

            if normal_sku:
                sku_ids.append(normal_sku)

            if foil_sku:
                sku_ids.append(foil_sku)

            if not sku_ids:

                print(
                    "    No English Near Mint SKUs.",
                    flush=True
                )

                total_errors += 1
                continue

            price_url = (
                "https://mpgateway.tcgplayer.com/"
                "v1/pricepoints/marketprice/skus/search"
            )

            payload = json.dumps({
                "skuIds": sku_ids
            }).encode("utf-8")

            price_request = urllib.request.Request(
                price_url,
                data=payload,
                headers=TCGPLAYER_HEADERS,
                method="POST"
            )

            with urllib.request.urlopen(
                price_request
            ) as response:

                if response.status != 200:

                    print(
                        f"    Price HTTP {response.status}",
                        flush=True
                    )

                    total_errors += 1
                    continue

                prices = json.loads(
                    response.read().decode("utf-8")
                )

            normal_price = ""
            foil_price = ""

            for price in prices:

                if price.get("skuId") == normal_sku:

                    market_price = price.get(
                        "marketPrice"
                    )

                    if market_price is not None:
                        normal_price = str(
                            market_price
                        )

                if price.get("skuId") == foil_sku:

                    market_price = price.get(
                        "marketPrice"
                    )

                    if market_price is not None:
                        foil_price = str(
                            market_price
                        )

            if not normal_price and not foil_price:

                print(
                    "    No market prices returned.",
                    flush=True
                )

                total_errors += 1
                continue

            print(
                f"    Normal: "
                f"{normal_price or 'None'}",
                flush=True
            )

            print(
                f"    Foil: "
                f"{foil_price or 'None'}",
                flush=True
            )

            if normal_price:

                card["noFoilValue"] = normal_price

            if foil_price:

                card["standardFoilValue"] = foil_price

                card["surgeFoilValue"] = foil_price

                card["rainbowFoilValue"] = foil_price

            total_updated += 1

            time.sleep(0.1)

        except urllib.error.HTTPError as error:

            print(
                f"    HTTP error: {error.code}",
                flush=True
            )

            total_errors += 1

        except Exception as error:

            print(
                f"    Error: {error}",
                flush=True
            )

            total_errors += 1

    print(
        "",
        flush=True
    )

    print(
        "TPIP price update complete.",
        flush=True
    )

    print(
        f"TPIP cards updated: {total_updated}",
        flush=True
    )

    print(
        f"TPIP cards without Product ID: "
        f"{total_no_product}",
        flush=True
    )

    print(
        f"TPIP errors: {total_errors}",
        flush=True
    )

def main():

    print(
        "Loading cards.json...",
        flush=True
    )

    with open(
        CARDS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        cards = json.load(file)

    print(
        f"Found {len(cards)} cards.",
        flush=True
    )

    total_updated = 0
    total_errors = 0
    total_skipped = 0

    batches = [
        cards[i:i + BATCH_SIZE]
        for i in range(
            0,
            len(cards),
            BATCH_SIZE
        )
    ]

    print(
        f"Processing {len(batches)} batches...",
        flush=True
    )

    for batch_number, batch in enumerate(
        batches,
        start=1
    ):

        print(
            "",
            flush=True
        )

        print(
            f"Batch {batch_number}/{len(batches)}",
            flush=True
        )

        results, problems = get_scryfall_batch(
            batch
        )

        for card in batch:

            set_code = str(
                card.get("set", "")
            ).strip()

            collector_number = str(
                card.get("number", "")
            ).strip()

            if not set_code or not collector_number:

                total_errors += 1

                continue

            if set_code.upper() == "TPIP":

                total_skipped += 1

                continue

            lookup_collector_number = collector_number

            if (
                set_code.upper() == "SLD"
                and collector_number in {
                    "790",
                    "795",
                    "796"
                }
            ):
                lookup_collector_number += "★"

            key = (
                set_code.lower(),
                lookup_collector_number
            )

            if key not in results:

                print(
                    f"  Not found: "
                    f"{set_code} "
                    f"{collector_number}",
                    flush=True
                )

                total_errors += 1

                # Do not erase an existing price.
                continue

            price_data = results[key]

            card["noFoilValue"] = (
                price_data["usd"]
            )

            card["standardFoilValue"] = (
                price_data["usd_foil"]
            )

            card["surgeFoilValue"] = (
                price_data["usd_foil"]
            )

            card["rainbowFoilValue"] = (
                price_data["usd_foil"]
            )

            total_updated += 1

        if problems:

            print(
                f"  Batch issues: {len(problems)}",
                flush=True
            )

        print(
            f"  Prices updated so far: "
            f"{total_updated}",
            flush=True
        )

        if batch_number < len(batches):

            time.sleep(0.5)

    update_tpip_prices(cards)

    print(
        "",
        flush=True
    )

    print(
        "Saving updated cards.json...",
        flush=True
    )

    with open(
        CARDS_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            cards,
            file,
            ensure_ascii=False,
            indent=2
        )

        file.write("\n")

    print(
        "",
        flush=True
    )

    print(
        "Price update complete.",
        flush=True
    )

    print(
        f"Prices updated: {total_updated}",
        flush=True
    )

    print(
        f"Errors / not found: {total_errors}",
        flush=True
    )

    print(
        f"TPIP cards skipped: {total_skipped}",
        flush=True
    )


if __name__ == "__main__":

    main()
