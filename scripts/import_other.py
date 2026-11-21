#!/usr/bin/env python3
"""Import public Chicago in-person listings from official HTML meeting directories.
No external dependencies. Never overwrite a source on a failed/undersized import.
"""
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "ca": ("https://www.illinoisareaca.org/locations", "Cocaine Anonymous", "Illinois Area of Cocaine Anonymous", ROOT / "data" / "ca.json", 2),
    "rd": ("https://recoverydharmachicago.org/meetings/?tsml-day=any", "Recovery Dharma", "Recovery Dharma Chicago", ROOT / "data" / "rd_live.json", 5),
    "s": ("https://smeetingschicago.com/meetings/?tsml-region=chicago&tsml-day=any", "S fellowships", "S Meetings Chicago", ROOT / "data" / "s_fellowships.json", 2),
}
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = {"attrs": attrs, "cells": [], "links": []}
        elif self.row is not None and tag in ("td", "th"):
            self.cell = {"attrs": attrs, "text": ""}
        elif self.row is not None and tag == "a":
            href = attrs.get("href", "")
            if href.startswith("https://"):
                self.row["links"].append(href)
    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data + " "
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.cell["text"] = " ".join(self.cell["text"].split())
            self.row["cells"].append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row["cells"]:
                self.rows.append(self.row)
            self.row = None

def get_rows(url):
    req = Request(url, headers={"User-Agent": "ChicagoRecoveryMeetings/0.4 (community meeting index)", "Accept": "text/html"})
    with urlopen(req, timeout=35) as response:
        html = response.read(2500000).decode("utf-8", "replace")
    parser = TableParser()
    parser.feed(html)
    return parser.rows

def parse_clock(s):
    m = re.search(r"\b(1[0-2]|0?[1-9]):([0-5]\d)\s*(am|pm)\b", s, re.I)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(3).lower()=="pm" else 0)
        return f"{h:02d}:{m.group(2)}"
    if re.search(r"\bnoon\b", s, re.I):
        return "12:00"
    return ""

def source_link(row, domain):
    for link in row["links"]:
        parsed = urlparse(link)
        if parsed.hostname and parsed.hostname.lower().endswith(domain) and "/meetings/" in parsed.path:
            return link.split("?")[0]
    return ""

def common(source, name, day, time, venue, address, url, checked, mode, types):
    if not (name and address and url and time):
        return None
    identifier = re.sub(r"[^a-z0-9]+", "-", urlparse(url).path.lower()).strip("-")
    if not identifier:
        return None
    if source == "ca":
        program, origin = "Cocaine Anonymous", "Illinois Area of Cocaine Anonymous"
    else:
        program, origin = "Recovery Dharma", "Recovery Dharma Chicago"
    return {
      "id": source + "-" + identifier + "-" + str(day), "program": program,
      "title": name, "day": day, "start": time, "end": "",
      "venue": venue, "address": address, "city": "Chicago", "state": "IL",
      "postal_code": "", "mode": mode,
      "is_open": True if re.search(r"\bopen\b",types,re.I) else (False if re.search(r"\bclosed\b",types,re.I) else None),
      "wheelchair_access": True if re.search(r"\bwheelchair\b",types,re.I) else None,
      "source_url": url, "source_name": origin, "last_checked": checked,
      "source_updated": "", "verification": "source-listed; not independently verified", "notes": ""
    }

def convert_ca(row, checked):
    c=[x["text"] for x in row["cells"]]
    if len(c)<8 or c[0] not in DAYS:
        return None
    day=DAYS.index(c[0])
    time=parse_clock(c[1])
    name,venue,address,types=c[2],c[3],c[4],c[7]
    # City must be explicitly in the postal address; no online/inactive venue.
    if not re.search(r",\s*Chicago\s*,\s*IL\b",address,re.I):
        return None
    if re.search(r"\b(online|virtual|inactive|telephone|zoom)\b",venue+" "+address,re.I):
        return None
    if len(c)>9:
        try:
            lat,lon=float(c[8]),float(c[9])
            if not (41.62<=lat<=42.04 and -87.95<=lon<=-87.50):return None
        except ValueError: return None
    url=source_link(row, "illinoisareaca.org")
    return common("ca", name, day,time,venue,address,url,checked,"in-person",types)

def convert_rd(row, checked):
    attrs=row["attrs"]
    cls=attrs.get("class","")
    mode="hybrid" if "attendance-hybrid" in cls else "in-person" if "attendance-in_person" in cls else ""
    if not mode:return None
    c=row["cells"]
    if len(c)<8:return None
    dsort=c[0]["attrs"].get("data-sort","")
    match=re.match(r"([0-6])-(\d{2}:\d{2})-",dsort)
    if not match:return None
    day=int(match.group(1))
    time=match.group(2)
    name,venue,address,region,types=(c[2]["text"],c[3]["text"],c[4]["text"],c[5]["text"],c[7]["text"])
    if not re.search(r"^Chicago\s*,\s*IL$",region,re.I):return None
    if not address or re.search(r"\b(online only|zoom only|virtual only)\b",venue+" "+address,re.I):return None
    url=source_link(row,"recoverydharmachicago.org")
    return common("rd",name,day,time,venue,address,url,checked,mode,types)

def convert_s(row, checked):
    attrs=row["attrs"]
    cls=attrs.get("class","")
    mode="hybrid" if "attendance-hybrid" in cls else "in-person" if "attendance-in_person" in cls else ""
    if not mode:return None
    c=row["cells"]
    if len(c)<8:return None
    match=re.match(r"([0-6])-(\d{2}:\d{2})-",c[0]["attrs"].get("data-sort",""))
    if not match:return None
    day,time=int(match.group(1)),match.group(2)
    name,venue,address,region,types=(c[2]["text"],c[3]["text"],c[4]["text"],c[5]["text"],c[7]["text"])
    if region.strip().lower() not in ("chicago","chicago, il"):return None
    if not address or re.search(r"\b(online only|virtual only|zoom only)\b",venue+" "+address,re.I):return None
    if re.search(r"\bintergroup\b",name,re.I):return None
    if name.upper().startswith("SLAA"):
        label="Sex and Love Addicts Anonymous"
    elif name.upper().startswith("SAA"):
        label="Sex Addicts Anonymous"
    else:
        return None
    url=source_link(row,"smeetingschicago.com")
    record=common("s",name,day,time,venue,address,url,checked,mode,types)
    if record:
        record["program"]=label
        record["source_name"]="S Meetings Chicago"
    return record

def atomic_write(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix="import-",suffix=".json")
    try:
        with os.fdopen(fd,"w",encoding="utf8") as fp:
            json.dump(rows,fp,indent=2,ensure_ascii=False)
            fp.write("\n")
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def main():
    checked=dt.datetime.now(dt.timezone.utc).date().isoformat()
    failures=[]
    for slug,(url,_,_,output,minimum) in SOURCES.items():
        try:
            rows=get_rows(url)
            result={}
            for row in rows:
                item=(convert_ca if slug=="ca" else convert_rd if slug=="rd" else convert_s)(row,checked)
                if item: result[item["id"]]=item
            if len(result)<minimum:
                raise ValueError(f"Only {len(result)} valid Chicago in-person sessions, expected at least {minimum}; preserving last data")
            records=sorted(result.values(),key=lambda m:(m["day"],m["start"],m["title"]))
            atomic_write(output,records)
            print(f"Imported {len(records)} {slug.upper()} Chicago in-person/hybrid weekly sessions")
        except Exception as exc:
            failures.append(slug)
            print(f"WARNING: {slug} import failed, preserving prior file: {exc}")
    if failures:
        print("WARNING: import incomplete for "+", ".join(failures))
        # Nonzero to flag data quality in workflow; independent sources may still succeed.
        raise SystemExit(1)

if __name__=="__main__":main()
