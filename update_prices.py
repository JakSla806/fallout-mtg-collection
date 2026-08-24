import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

CARDS_FILE = "cards.json"

HEADERS = {
    "User-Agent": "JakeFalloutTracker/1.0",
    "Accept": "application/json"
}


def get_scryfall_card(set_code, collector_number):

    query = (
        "https://api.scryfall.com/cards/search?q=set:"
        + urllib.parse.quote(set_code.lower())
        + "+cn:"
        + urllib.parse.quote(collector_number)
    )

    request = urllib.request.Request(
        query,
        headers=HEADERS
    )

    try:

        with urllib.request.urlopen(request) as response:

            if response.status != 200:
                return None, f"HTTP {response.status}"

            data = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        if error.code == 429:

            print(
                f"Rate limited for {set_code} {collector_number}. "
                "Waiting 1.5 seconds..."
            )

            time.sleep(1.5)

            try:

                with urllib.request.urlopen(request) as response:

                    if response.status != 200:
                        return None, f"HTTP {response.status}"

                    data = json.loads(
                        response.read().decode("utf-8")
                    )

            except Exception as retry_error:

                return None, str(retry_error)

        else:

            return None, f"HTTP {error.code}"

    except Exception as error:

        return None, str(error)


    if not data.get("data"):

        return None, "Card Not Found"


    card = data["data"][0]

    prices = card.get("prices", {})

    return {
        "name": card.get("name", ""),
        "usd": prices.get("usd") or "",
        "usd_foil": prices.get("usd_foil") or ""
    }, None


def main():

    print("Loading cards.json...")

    with open(
        CARDS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        cards = json.load(file)


    print(
        f"Found {len(cards)} cards."
    )


    updated = 0
    errors = 0


    for index, card in enumerate(cards, start=1):

        set_code = str(
            card.get("set", "")
        ).strip()

        collector_number = str(
            card.get("number", "")
        ).strip()


        if not set_code or not collector_number:

            print(
                f"[{index}/{len(cards)}] "
                "Missing set or collector number. Skipping."
            )

            errors += 1
            continue


        print(
            f"[{index}/{len(cards)}] "
            f"Updating {set_code} {collector_number}..."
        )


        result, error = get_scryfall_card(
            set_code,
            collector_number
        )


        if error:

            print(
                f"    ERROR: {error}"
            )

            errors += 1

            time.sleep(0.1)

            continue


        card["noFoilValue"] = result["usd"]

        card["standardFoilValue"] = result["usd_foil"]

        card["surgeFoilValue"] = result["usd_foil"]

        card["rainbowFoilValue"] = result["usd_foil"]


        updated += 1


        print(
            f"    Normal: {result['usd']}"
        )

        print(
            f"    Foil:   {result['usd_foil']}"
        )


        time.sleep(0.1)


    print()
    print("Saving updated cards.json...")


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


    print()
    print("Price update complete.")
    print(f"Cards updated: {updated}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
