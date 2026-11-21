#!/usr/bin/env python3
"""Retrieve public Chicago AA meeting facts from Recovery Starts.
One directory request per run, no bot-protection bypass. Validate Chicago in-person
location and meeting data before atomically updating the last known good file.
"""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.robotparser
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen

URL="https://recoverystarts.com/meetings/aa/chicago/"
UA="ChicagoRecoveryMeetings/0.5 (+https://github.com/TonyAChicago/chicago-recovery-meetings)"
DEST=Path(__file__).resolve().parents[1]/"data"/"aa.json"
VALID_TIME=re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
CHICAGO=re.compile(r",\s*Chicago\s*,\s*IL(?:\s+\d{5})?\s*,?\s*USA?\s*$",re.I)

class Cards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards=[]
        self.current=None
        self.depth=0
        self.field=None
        self.fieldtag=None
    def handle_starttag(self,tag,attrs):
        attr=dict(attrs)
        classes=attr.get("class","").split()
        if self.current is None:
            if tag=="div" and "card" in classes and "m" in classes:
                self.current={"day":attr.get("data-d",""),"start":attr.get("data-t",""),
                              "end":attr.get("data-e",""),"name":"","location":"","tags":[],
                              "link":""}
                self.depth=1
            return
        if tag=="div":self.depth+=1
        if tag in ("span","div"):
            if "nm" in classes:
                self.field="name";self.fieldtag=tag
            elif "loc" in classes:
                self.field="location";self.fieldtag=tag
            elif tag=="span" and "tag" in classes:
                self.field="tag";self.fieldtag=tag
                self.current["tags"].append("")
        if tag=="a" and self.field=="name":
            target=attr.get("href","")
            href=urljoin(URL,target)
            if href.startswith("https://recoverystarts.com/meetings/aa/chicago/"):
                self.current["link"]=href.split("?")[0].split("#")[0]
    def handle_data(self,data):
        if self.current is None or not self.field:return
        if self.field=="tag":
            if self.current["tags"]:self.current["tags"][-1]+=data
        else:self.current[self.field]+=data
    def handle_endtag(self,tag):
        if self.current is None:return
        if tag==self.fieldtag:
            self.field=None;self.fieldtag=None
        if tag=="div":
            self.depth-=1
            if self.depth==0:
                self.cards.append(self.current)
                self.current=None;self.field=None;self.fieldtag=None

def normalize(card,checked):
    try:day=int(card["day"])
    except (ValueError,TypeError):return None
    start=card["start"]
    if day<0 or day>6 or not VALID_TIME.fullmatch(start):return None
    end=card["end"] if VALID_TIME.fullmatch(card["end"]) else ""
    title=" ".join(card["name"].split())
    loc=" ".join(card["location"].split())
    link=card["link"]
    if not title or not loc or not link:return None
    if " · " in loc:
        venue,address=loc.rsplit(" · ",1)
    else:venue,address="",loc
    if not CHICAGO.search(address):return None
    street=address.split(", Chicago",1)[0].strip()
    # City-only or zipcode-only records cannot route someone to a room.
    if not re.search(r"\d",street):return None
    tags=[t.strip() for t in card["tags"] if t.strip()]
    folded={t.casefold() for t in tags}
    hybrid=any("in person + online" in t or "in-person and online" in t for t in folded)
    if ("online" in folded or "virtual" in folded or "online only" in folded) and not hybrid:
        return None
    if "online only" in title.lower() or "zoom only" in title.lower():
        return None
    mode="hybrid" if hybrid else "in-person"
    group_key=f"{link}|{day}|{start}".encode("utf-8")
    id_="aa-rs-"+hashlib.sha1(group_key).hexdigest()[:16]
    postal=re.search(r"\b(\d{5})(?:-\d{4})?\b",address)
    return {
      "id":id_, "program":"Alcoholics Anonymous", "title":title,"day":day,
      "start":start,"end":end,"venue":venue,"address":street,"city":"Chicago",
      "state":"IL","postal_code":postal.group(1) if postal else "","mode":mode,
      "is_open":True if "open to all" in folded or "open" in folded else
                False if "closed" in folded else None,
      "wheelchair_access":True if any("wheelchair" in t for t in folded) else None,
      "source_url":link,"source_name":"Recovery Starts (AA local directory aggregation)",
      "last_checked":checked,"source_updated":"",
      "verification":"third-party source-listed; not independently verified","notes":""
    }

def main():
    robot=urllib.robotparser.RobotFileParser()
    robot.set_url("https://recoverystarts.com/robots.txt")
    robot.read()
    if not robot.can_fetch(UA,URL):
        raise RuntimeError("AA directory is not allowed by robots policy; preserving existing records")
    req=Request(URL,headers={"User-Agent":UA,"Accept":"text/html"})
    with urlopen(req,timeout=35) as resp:
        if resp.status!=200:raise ValueError("Source returned HTTP "+str(resp.status))
        content=resp.read(2500000).decode("utf-8","replace")
    parser=Cards();parser.feed(content)
    checked=dt.datetime.now(dt.timezone.utc).date().isoformat()
    unique={}
    for card in parser.cards:
        row=normalize(card,checked)
        if row:unique[row["id"]]=row
    rows=sorted(unique.values(),key=lambda r:(r["day"],r["start"],r["title"]))
    # Avoid publishing a partial page or a design change interpreted as meetings.
    if not 250<=len(rows)<=2500:
        raise ValueError(f"Only {len(rows)} Chicago physical AA sessions from {len(parser.cards)} cards; preserving last good file")
    DEST.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix="aa-",suffix=".json",dir=DEST.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(rows,f,ensure_ascii=False,indent=2);f.write("\n")
        os.replace(tmp,DEST)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print(f"Imported {len(rows)} Chicago in-person/hybrid AA sessions from {len(parser.cards)} source cards")

if __name__=="__main__":
    try:main()
    except Exception as exc:
        import sys
        print(f"AA import failed, retained last good file: {exc}",file=sys.stderr)
        sys.exit(1)
