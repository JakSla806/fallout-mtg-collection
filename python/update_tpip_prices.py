import json
import time
import urllib.error
import urllib.request

CARDS_FILE = "cards.json"
LOOKUP_FILE = "tpip_lookup.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}


def get_product_details(product_id):

    url = (
        "https://mp-search-api.tcgplayer.com/v2/product/"
        + str(product_id)
        + "/details"
    )

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    try:

        with urllib.request.urlopen(request) as response:

            if response.status != 200:
                return None

            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        print(
            f"    Product details HTTP {error.code}",
            flush=True
        )

        return None

    except Exception as error:

        print(
            f"    Product details error: {error}",
            flush=True
        )

        return None


def get_skus(details):

    normal_sku = None
    foil_sku = None

    for sku in details.get("skus", []):

        if (
            sku.get("language") == "English"
            and sku.get("condition") == "Near Mint"
        ):

            if sku.get("variant") == "Normal":
                normal_sku = sku.get("sku")

            if sku.get("variant") == "Foil":
                foil_sku = sku.get("sku")

    return normal_sku, foil_sku


def get_market_prices(sku_ids):

    if not sku_ids:
        return {}


    url = (
        "https://mpgateway.tcgplayer.com/"
        "v1/pricepoints/marketprice/skus/search"
    )


    payload = json.dumps({
        "skuIds": sku_ids
    }).encode("utf-8")


    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        method="POST"
    )


    try:

        with urllib.request.urlopen(request) as response:

            if response.status != 200:
                return {}

            prices = json.loads(
                response.read().decode("utf-8")
            )


        results = {}

        for price in prices:

            sku_id = price.get("skuId")
            market_price = price.get("marketPrice")

            if sku_id is not None and market_price is not None:

                results[str(sku_id)] = market_price


        return results


    except urllib.error.HTTPError as error:

        print(
            f"    Price lookup HTTP {error.code}",
            flush=True
        )

        return {}


    except Exception as error:

        print(
            f"    Price lookup error: {error}",
            flush=True
        )

        return {}


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
        "Loading TPIP lookup...",
        flush=True
    )


    with open(
        LOOKUP_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        lookup = json.load(file)


    tpip_cards = []

    for card in cards:

        if (
            str(card.get("set", "")).upper()
            == "TPIP"
        ):

            tpip_cards.append(card)


    print(
        f"Found {len(tpip_cards)} TPIP cards.",
        flush=True
    )


    updated = 0
    no_product_id = 0
    errors = 0


    for index, card in enumerate(
        tpip_cards,
        start=1
    ):

        number = str(
            card.get("number", "")
        ).strip()


        print(
            f"[{index}/{len(tpip_cards)}] "
            f"TPIP {number}",
            flush=True
        )


        lookup_entry = lookup.get(number)


        if not lookup_entry:

            print(
                "    No lookup entry.",
                flush=True
            )

            no_product_id += 1

            continue


        product_id = lookup_entry.get(
            "product_id"
        )


        if not product_id:

            print(
                "    No TCGplayer Product ID.",
                flush=True
            )

            no_product_id += 1

            continue


        print(
            f"    Product ID: {product_id}",
            flush=True
        )


        details = get_product_details(
            product_id
        )


        if not details:

            errors += 1

            continue


        normal_sku, foil_sku = get_skus(
            details
        )


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

            errors += 1

            continue


        prices = get_market_prices(
            sku_ids
        )


        normal_price = None
        foil_price = None


        if normal_sku:

            normal_price = prices.get(
                str(normal_sku)
            )


        if foil_sku:

            foil_price = prices.get(
                str(foil_sku)
            )


        if normal_price is not None:

            card["noFoilValue"] = (
                normal_price
            )


        if foil_price is not None:

            card["standardFoilValue"] = (
                foil_price
            )

            card["surgeFoilValue"] = (
                foil_price
            )

            card["rainbowFoilValue"] = (
                foil_price
            )


        if (
            normal_price is not None
            or foil_price is not None
        ):

            updated += 1

            print(
                f"    Normal: {normal_price}",
                flush=True
            )

            print(
                f"    Foil: {foil_price}",
                flush=True
            )

        else:

            errors += 1

            print(
                "    No market prices returned.",
                flush=True
            )


        # Give TCGplayer a little breathing room.
        time.sleep(0.25)


    print(
        "",
        flush=True
    )


    print(
        "Saving cards.json...",
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
        "TPIP price update complete.",
        flush=True
    )

    print(
        f"Cards updated: {updated}",
        flush=True
    )

    print(
        f"No Product ID: {no_product_id}",
        flush=True
    )

    print(
        f"Errors: {errors}",
        flush=True
    )


if __name__ == "__main__":

    main()
