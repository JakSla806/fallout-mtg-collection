import json

CARDS_FILE = "cards.json"

PRICE_FIELDS = [
    "noFoilValue",
    "standardFoilValue",
    "surgeFoilValue",
    "rainbowFoilValue"
]


def main():

    print("Loading cards.json...", flush=True)

    with open(
        CARDS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        cards = json.load(file)

    cleared = 0
    preserved = 0

    for card in cards:

        # Preserve all TPIP prices because those
        # are supplied by the separate TCGplayer
        # pricing system.

        if str(card.get("set", "")).upper() == "TPIP":

            preserved += 1
            continue

        for field in PRICE_FIELDS:

            card[field] = ""

        cleared += 1

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
        f"Cleared prices for {cleared} non-TPIP cards.",
        flush=True
    )

    print(
        f"Preserved prices for {preserved} TPIP cards.",
        flush=True
    )


if __name__ == "__main__":
    main()
