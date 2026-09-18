#!/usr/bin/env python3
"""Télécharge dans sources/ les photos Unsplash listées dans sources.json.

Chaque entrée porte deux adresses : `url` pointe sur le CDN Unsplash en pleine
résolution, `mirror` sur le miroir S3 (400 px de large) qui reste joignable
derrière un proxy filtrant. On tente la première, on retombe sur la seconde.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
SOURCES = HERE / "sources"
HEADERS = {"User-Agent": "mask-experiment/1.0"}


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> int:
    photos = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    SOURCES.mkdir(exist_ok=True)
    failures = 0

    for photo in photos:
        target = SOURCES / photo["file"]
        if target.exists():
            print(f"déjà là : {target.name}")
            continue

        data = None
        for key in ("url", "mirror"):
            url = photo.get(key)
            if not url:
                continue
            try:
                data = download(url)
                break
            except (urllib.error.URLError, OSError) as error:
                print(f"  {key} indisponible pour {photo['file']} : {error}", file=sys.stderr)

        if data is None:
            failures += 1
            continue

        target.write_bytes(data)
        print(f"{target.name}  ({len(data) // 1024} Ko)  © {photo['author']}")

    if failures:
        print(f"{failures} photo(s) non téléchargée(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
