#!/usr/bin/env python3
"""Import Chicago-only, physically attendable NA meetings from the Chicagoland BMLT server.

Uses only Python standard library. On any fetch / parsing / validation failure, exits
nonzero BEFORE overwriting existing data/na.json. Designed for GitHub Actions.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = "https://bmlt.chicagona.org/main_server/client_interface/json/"
SOURCE = "https://chicagona.org/meetings/"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "na.json"
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$")


def request_url():
    # Center and radius cover the full city; municipality and coordinates are
    # filtered AGAIN locally so neighboring suburbs cannot be included.
    query = urlencode({
        "switcher": "GetSearchResults",
        "lat_val": "41.8781",
        "long_val": "-87.6298",
        "geo_width": "30",
    })
    return ROOT + "?" + query


def as_str(value):
    return str(value).strip() if value is not None else ""


def fmt_codes(row):
    result = set()
    formats = row.get("formats", [])
    if isinstance(formats, list):
        for item in formats:
            if isinstance(item, dict):
                code = as_str(item.get("key_string")).upper()
                if code: result.add(code)
    return result


def time_hhmm(value):
    v = as_str(value)
    return v[:5] if HHMM.fullmatch(v) else ""


def end_time(start, duration):
    d = time_hhmm(duration)
    if not start or not d: return ""
    h, m = map(int, start.split(":"))
    dh, dm = map(int, d.split(":"))
    total = (h * 60 + m + dh * 60 + dm) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def import_row(row, checked):
    if not isinstance(row, dict): return None
    municipality = as_str(row.get("location_municipality"))
    if municipality.lower() != "chicago": return None
    # BMLT venue_type: 1 = physical, 2 = virtual only, 3 = hybrid.
    # Do not infer physical attendance if the type is missing or unrecognized.
    venue_type = as_str(row.get("venue_type"))
    if venue_type not in ("1", "3"): return None
    try:
        day = int(row["weekday_tinyint"]) - 1
    except (KeyError, TypeError, ValueError): return None
    if not 0 <= day <= 6: return None
    start = time_hhmm(row.get("start_time"))
    street = as_str(row.get("location_street"))
    name = as_str(row.get("meeting_name"))
    venue = as_str(row.get("location_text"))
    source_id = as_str(row.get("id_bigint"))
    if not (start and street and name and source_id.isdigit()): return None
    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        # Broad Chicago bounds. Municipality name must ALSO be "Chicago".
        if not (41.62 <= lat <= 42.04 and -87.95 <= lon <= -87.50): return None
    except (KeyError, TypeError, ValueError):
        # Some BMLT records lack geocodes but still have an explicit municipality.
        pass
    codes = fmt_codes(row)
    is_open = True if "O" in codes else False if "C" in codes else None
    # Never assume wheelchair accessibility without an explicit format code.
    wheelchair = True if ("WC" in codes or "W" in codes) else None
    state = as_str(row.get("location_province")) or "IL"
    if state.lower() == "illinois": state = "IL"
    if state.upper() != "IL": return None
    return {
        "id": "na-bmlt-" + source_id,
        "program": "Narcotics Anonymous",
        "title": name,
        "day": day,
        "start": start,
        "end": end_time(start, row.get("duration_time")),
        "venue": venue,
        "address": street,
        "city": "Chicago",
        "state": "IL",
        "postal_code": as_str(row.get("location_postal_code_1")),
        "mode": "hybrid" if venue_type == "3" else "in-person",
        "is_open": is_open,
        "wheelchair_access": wheelchair,
        "source_url": SOURCE,
        "source_name": "Chicagoland Region of NA (BMLT)",
        "source_updated": "",
        "last_checked": checked,
        "verification": "source-listed; not independently verified",
        "notes": "",
    }


def import_rows(payload, checked, min_count=10):
    if not isinstance(payload, list): raise ValueError("Expected a JSON array from BMLT")
    output = {}
    for row in payload:
        m = import_row(row, checked)
        if m: output[m["id"]] = m
    if len(output) < min_count:
        raise ValueError(f"Only {len(output)} valid Chicago physical meetings returned (<{min_count}); keeping last successful file")
    return sorted(output.values(), key=lambda m: (m["day"], m["start"], m["title"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Offline BMLT response fixture for local testing")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--min-count", type=int, default=10)
    args = parser.parse_args()
    checked = dt.date.today().isoformat()
    if args.input:
        payload = json.loads(Path(args.input).read_text())
        records = import_rows(payload, checked, args.min_count)
    else:
        # First request a wide circle around downtown. Fall back to a full
        # search in case the source version handles geospatial fields differently.
        candidates = [request_url(), ROOT + "?switcher=GetSearchResults"]
        errors = []
        records = None
        for url in candidates:
            try:
                req = Request(url, headers={"User-Agent": "ChicagoRecoveryMeetings/0.3 (noncommercial public-meeting index)", "Accept": "application/json"})
                with urlopen(req, timeout=35) as response:
                    payload = json.load(response)
                records = import_rows(payload, checked, args.min_count)
                break
            except Exception as exc:
                errors.append(str(exc))
        if records is None:
            raise RuntimeError("All BMLT retrieval attempts failed: " + " | ".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement: old records remain intact on any upstream error.
    fd, tmp = tempfile.mkstemp(prefix="na-", suffix=".json", dir=args.output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, args.output)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print(f"Imported {len(records)} Chicago in-person/hybrid NA meeting sessions")


if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"NA import failed without changing the published file: {exc}", file=sys.stderr)
        sys.exit(1)
