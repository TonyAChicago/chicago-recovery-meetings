#!/usr/bin/env python3
"""Refresh source-listed Chicago LifeRing in-person meetings from official detail pages.

This importer intentionally contains only a confirmed Chicago city-limits meeting.
Nearby Evanston meetings and Chicago-labeled online-only meetings are excluded.
Failure leaves the previous file intact; no attendee/convenor contacts are copied.
"""
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
import urllib.robotparser

BASE = "https://meetings.lifering.org"
URL = BASE + "/meetings/1022/"
DEST = Path(__file__).resolve().parents[1] / "data" / "lifering.json"
UA = "ChicagoRecoveryMeetings/0.5 (+https://github.com/TonyAChicago/chicago-recovery-meetings)"

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignore = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"): self.ignore += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"): self.ignore = max(0, self.ignore-1)
    def handle_data(self, data):
        if not self.ignore: self.parts.append(data)

def validate_and_parse(page):
    if not re.search(r"Kindred Hospital LifeRing Meeting", page, re.I):
        raise ValueError("Meeting title missing; source may have changed")
    text_parser=TextOnly()
    text_parser.feed(page)
    text=" ".join(" ".join(text_parser.parts).split())
    if not re.search(r"Kindred Hospital Chicago North", text, re.I):
        raise ValueError("Physical venue missing; retaining previous data")
    if not re.search(r"2544\s+W(?:est)?\.?\s+Montrose", text, re.I):
        raise ValueError("Physical address missing; retaining previous data")
    if not re.search(r"Chicago,\s*IL,?\s*60618", text, re.I):
        raise ValueError("Source city or ZIP differs; retaining previous data")
    # Source publishes UTC meeting event timestamps as tz-convert attributes.
    # Convert to America/Chicago instead of trusting browser-timezone labels.
    fields = re.findall(
        r'data-utc="([^"]+)"\s+data-format="(date|time|weekday)"',
        page, re.I)
    stamps = list(dict.fromkeys(t for t,fmt in fields))
    if len(stamps)!=2:
        raise ValueError("Expected one UTC event start and end timestamp")
    start_utc,end_utc=[dt.datetime.fromisoformat(t.replace("Z","+00:00")) for t in stamps]
    if start_utc.tzinfo is None or end_utc.tzinfo is None:
        raise ValueError("Event timestamps missing UTC timezone")
    local=ZoneInfo("America/Chicago")
    start_local=start_utc.astimezone(local)
    end_local=end_utc.astimezone(local)
    day=(start_local.weekday()+1)%7
    hour,minute=start_local.hour,start_local.minute
    finish=end_local.strftime("%H:%M")
    if end_utc-start_utc!=dt.timedelta(minutes=90):
        raise ValueError("Meeting duration changed; review before updating")
    if day!=3 or (hour,minute)!=(19,0) or finish!="20:30":
        raise ValueError("Meeting day or time changed; manual review needed")
    return {
        "id": "lifering-official-1022-wed-1900",
        "program": "LifeRing Secular Recovery",
        "title": "Kindred Hospital LifeRing Meeting",
        "day": day, "start": f"{hour:02d}:{minute:02d}", "end": finish,
        "venue": "Kindred Hospital Chicago North",
        "address": "2544 W Montrose Ave", "city": "Chicago", "state": "IL",
        "postal_code": "60618", "mode": "in-person",
        "is_open": True, "wheelchair_access": None,
        "source_url": URL, "source_name": "LifeRing Secular Recovery (official meeting finder)",
        "last_checked": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "source_updated": "", "verification": "source-listed; not independently verified",
        "notes": "Check in at the front desk for the sixth-floor meeting room. Verify directly before attending."
    }

def main():
    policy_req=Request(BASE+"/robots.txt",headers={"User-Agent": UA, "Accept": "text/plain"})
    with urlopen(policy_req, timeout=15) as resp:
        if resp.status!=200:
            raise ValueError("Unable to confirm source robots policy")
        policy=resp.read(120000).decode("utf-8","replace")
    robot=urllib.robotparser.RobotFileParser()
    robot.parse(policy.splitlines())
    if not robot.can_fetch(UA, URL):
        raise ValueError("Source robots policy prohibits this retrieval")
    req=Request(URL,headers={"User-Agent": UA,"Accept":"text/html"})
    with urlopen(req,timeout=25) as resp:
        if resp.status!=200:raise ValueError("LifeRing source HTTP "+str(resp.status))
        page=resp.read(1200000).decode("utf-8","replace")
    record=validate_and_parse(page)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix="lifering-",suffix=".json",dir=DEST.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump([record],f,indent=2,ensure_ascii=False);f.write("\n")
        os.replace(temp,DEST)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    print("Imported 1 source-listed in-person Chicago LifeRing meeting")

if __name__=="__main__":
    try:main()
    except Exception as exc:
        import sys
        print("LifeRing import failed; retaining previous file:",str(exc),file=sys.stderr)
        sys.exit(1)
