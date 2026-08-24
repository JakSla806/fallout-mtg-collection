import json
import time
import urllib.request

CARDS_FILE = "cards.json"

BATCH_SIZE = 75

HEADERS = {
    "User-Agent": "JakeFalloutTracker/1.0",
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
        if set_code.upper() == "SLD" and collector_number in {
            "790",
            "795",
            "796"
        }:
            collector_number += "★"

        # TPIP tokens use the separate TCGplayer
        # pricing system from your original Apps Script.
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
                    "usd":
                        prices.get("usd") or "",

                    "usd_foil":
                        prices.get("usd_foil") or ""
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
                    f"Waiting {wait_time} seconds..."
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


def main():

    print("Loading cards.json...", flush=True)


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
            f"",
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


            # TPIP is handled separately by the
            # TCGplayer token updater.
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
                    f"{set_code} {collector_number}",
                    flush=True
                )

                total_errors += 1

                # IMPORTANT:
                # Do not erase the existing price.
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


        # Give Scryfall a little breathing room
        # between collection requests.
        if batch_number < len(batches):

            time.sleep(0.5)


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
