#!/usr/bin/env python3
"""Import Chicago in-person SMART facts from a public independent search index.
No access to SMART Recovery's restricted website. Uses public SobaSearch links,
extracts factual schedule/location metadata only, and attributes every record.
All network failures preserve the last known good JSON file.
"""
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import urllib.robotparser

BASE="https://sobasearch.com"
INDEX=BASE+"/meetings/us/illinois/smart"
UA="ChicagoRecoveryMeetings/0.5 (+https://github.com/TonyAChicago/chicago-recovery-meetings)"
DEST=Path(__file__).resolve().parents[1]/"data"/"smart.json"
CHICAGO_PATH=re.compile(r"^/meetings/us/illinois/smart/[a-z0-9-]*chicago-illinois/?$")
TIME=re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$")

class DetailLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag!="a":return
        path=dict(attrs).get("href","").split("?")[0]
        if CHICAGO_PATH.fullmatch(path):
            url=urljoin(BASE,path)
            if url not in self.links:self.links.append(url)

def fetch(url):
    req=Request(url,headers={"User-Agent":UA,"Accept":"text/html"})
    with urlopen(req,timeout=20) as r:
        if r.status!=200:raise ValueError(f"{url}: HTTP {r.status}")
        return r.read(600000).decode("utf-8","replace")

def fmt_time(raw):
    m=TIME.fullmatch(str(raw).strip())
    return f"{m.group(1)}:{m.group(2)}" if m else ""

def parse_detail(page,source_url,checked):
    m=re.search(r'data-meeting-resource="([^"]+)"',page)
    if not m:raise ValueError("Missing structured meeting data at "+source_url)
    record=json.loads(html.unescape(m.group(1)))
    if not isinstance(record,dict):raise ValueError("Bad structured record")
    if str(record.get("program_type","")).upper()!="SMART":
        raise ValueError("Unexpected non-SMART record at "+source_url)
    attendance=str(record.get("attendance_mode","")).lower()
    if attendance not in ("in_person","hybrid","in-person"):
        return []
    if str(record.get("city","")).strip().lower()!="chicago":
        return []
    if str(record.get("state","")).strip().upper()!="IL":
        return []
    street=str(record.get("address","")).strip()
    if not re.search(r"\d",street):return []
    start=fmt_time(record.get("starts_at",""))
    end=fmt_time(record.get("ends_at",""))
    title=str(record.get("name","")).strip()
    sid=str(record.get("id","")).strip()
    if not (start and title and sid):return []
    try:
        lat=float(record["latitude"]);lon=float(record["longitude"])
        if not (41.62<=lat<=42.04 and -87.95<=lon<=-87.50):return []
    except (ValueError,KeyError,TypeError):return []
    codes={str(x).strip().upper() for x in record.get("type_codes",[]) if x}
    days=record.get("days",[])
    if not isinstance(days,list):return []
    rows=[]
    for rawday in days:
        try:day=int(rawday)
        except (ValueError,TypeError):continue
        if not 0<=day<=6:continue
        rows.append({
            "id":"smart-soba-"+sid+"-"+str(day),
            "program":"SMART Recovery","title":title,"day":day,"start":start,
            "end":end,"venue":"","address":street,"city":"Chicago","state":"IL",
            "postal_code":str(record.get("postal_code","") or "").strip(),
            "mode":"hybrid" if attendance=="hybrid" else "in-person",
            "is_open":True if "O" in codes else False if "C" in codes else None,
            "wheelchair_access":True if ("WC" in codes or "W" in codes) else None,
            "source_url":source_url,"source_name":"SobaSearch (independent SMART meeting directory)",
            "last_checked":checked,"source_updated":"",
            "verification":"third-party source-listed; not independently verified","notes":""
        })
    return rows

def main():
    policy_req=Request(BASE+"/robots.txt",headers={"User-Agent":UA,"Accept":"text/plain"})
    with urlopen(policy_req,timeout=15) as r:
        if r.status!=200:raise ValueError("Robots policy unavailable")
        policy=r.read(150000).decode("utf-8","replace")
    robot=urllib.robotparser.RobotFileParser()
    robot.parse(policy.splitlines())
    if not robot.can_fetch(UA,INDEX):
        raise RuntimeError("Index access disallowed; preserving existing SMART data")
    index=fetch(INDEX)
    parsed=DetailLinks()
    parsed.feed(index)
    links=parsed.links
    if not 8<=len(links)<=75:
        raise ValueError(f"Expected 8-75 Chicago SMART source links, got {len(links)}")
    checked=dt.datetime.now(dt.timezone.utc).date().isoformat()
    found={}
    for url in links:
        if not robot.can_fetch(UA,url):
            raise RuntimeError("Detail access disallowed by source robots policy")
        for row in parse_detail(fetch(url),url,checked):
            found[row["id"]]=row
        time.sleep(0.12)
    rows=sorted(found.values(),key=lambda r:(r["day"],r["start"],r["title"]))
    if not 2<=len(rows)<=90:
        raise ValueError(f"Only {len(rows)} physical Chicago SMART sessions; keeping old data")
    DEST.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix="smart-",suffix=".json",dir=DEST.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(rows,f,indent=2,ensure_ascii=False);f.write("\n")
        os.replace(tmp,DEST)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print(f"Imported {len(rows)} Chicago SMART weekly physical/hybrid meetings from {len(links)} source listings")

if __name__=="__main__":
    try:main()
    except Exception as e:
        import sys
        print(f"SMART import failed, preserving previous file: {e}",file=sys.stderr)
        sys.exit(1)
