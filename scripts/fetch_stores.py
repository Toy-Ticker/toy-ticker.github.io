#!/usr/bin/env python3
"""Build data/stores.json: every US McDonald's on OpenStreetMap, for the toy sightings map (sightings.html).

The map reads this file instead of querying OpenStreetMap live, so it works when the public Overpass servers
are busy and visitors' map moves aren't sent anywhere. Restaurants change slowly; rerun every month or so.

    python3 scripts/fetch_stores.py                  # writes data/stores.json
    python3 scripts/fetch_stores.py --from us.json   # use an Overpass response saved earlier

Output: {"updated": "YYYY-MM-DD", "source": ..., "fields": [...], "stores": [[id, lat, lon, name, address], ...]}
id is "osm:" + n/w/r + the OpenStreetMap id, so reports keep pointing at the same restaurant across refreshes.
"""
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "stores.json"
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
QUERY = """[out:json][timeout:300];
area["ISO3166-1"="US"][admin_level=2]->.us;
(
  nwr["brand:wikidata"="Q38076"](area.us);
  nwr["amenity"="fast_food"]["name"~"^McDonald",i](area.us);
);
out center tags;"""


def fetch():
    # curl rather than urllib: some Python builds (older LibreSSL on macOS) fail the TLS handshake with Overpass.
    wait = 15
    for attempt in range(6):
        for ep in ENDPOINTS:
            r = subprocess.run(["curl", "-sS", "-m", "400", "-A", "toy-ticker-stores/1.0 (+https://toy-ticker.github.io/)",
                                "-w", "\\n%{http_code}", ep, "--data-urlencode", "data=" + QUERY],
                               capture_output=True, text=True)
            body, _, code = r.stdout.rpartition("\n")
            if r.returncode == 0 and code == "200":
                return json.loads(body)
            # Busy servers answer 429/502/504; try the next one, then back off.
            print(f"  {ep}: {code or r.stderr.strip()}", file=sys.stderr)
        print(f"  all busy, retrying in {wait}s", file=sys.stderr)
        time.sleep(wait)
        wait *= 2
    sys.exit("Overpass didn't answer; try again later.")


def address(t):
    street = " ".join(x for x in (t.get("addr:housenumber"), t.get("addr:street")) if x)
    return ", ".join(x for x in (street, t.get("addr:city"), t.get("addr:state")) if x)


def main():
    d = json.load(open(sys.argv[2])) if sys.argv[1:2] == ["--from"] else fetch()
    rows = []
    for el in d.get("elements", []):
        t = el.get("tags", {})
        lat = el.get("lat", el.get("center", {}).get("lat"))
        lon = el.get("lon", el.get("center", {}).get("lon"))
        if lat is None or lon is None:
            continue
        # Skip things that only mention McDonald's (play places inside a Walmart are fine; closed ones aren't).
        if t.get("disused:amenity") or t.get("was:amenity") or t.get("amenity") not in (None, "fast_food", "restaurant"):
            continue
        name = t.get("name") or "McDonald's"
        rows.append([f"osm:{el['type'][0]}{el['id']}", round(lat, 5), round(lon, 5),
                     "" if name == "McDonald's" else name, address(t)])
    rows.sort(key=lambda r: r[0])
    out = {"updated": date.today().isoformat(), "source": "OpenStreetMap contributors (ODbL)",
           "fields": ["id", "lat", "lon", "name (blank = McDonald's)", "address"], "stores": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(rows)} restaurants -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
