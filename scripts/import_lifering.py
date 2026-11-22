#!/usr/bin/env python3
"""Refresh source-listed Chicago LifeRing in-person meetings from official detail pages.

This importer intentionally contains only a confirmed Chicago city-limits meeting.
Nearby Evanston meetings and Chicago-labeled online-only meetings are excluded.
Failure leaves the previous file intact; no attendee/convenor contacts are copied.
"""
import datetime as dt
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen
import urllib.robotparser

BASE = "https://meetings.lifering.org"
URL = BASE + "/meetings/1022/"
DEST = Path(__file__).resolve().parents[1] / "data" / "lifering.json"
UA = "ChicagoRecoveryMeetings/0.5 (+https://github.com/TonyAChicago/chicago-recovery-meetings)"
DAY_CODES = {"SU": 0, "MO": 1, "TU": 2, "WE": 3, "TH": 4, "FR": 5, "SA": 6}

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
    # The source's calendar export is expressed in America/Chicago time,
    # unlike visitor-timezone "Next meeting" text, which may display a different day.
    combined=unescape(page) + " " + text
    cal=re.search(
        r"20\d{2}-\d{2}-\d{2}\s+(\d{1,2}:\d{2})\s+"
        r"20\d{2}-\d{2}-\d{2}\s+(\d{1,2}:\d{2})\s+America/Chicago",
        combined, re.I)
    weekly=re.search(r"FREQ=WEEKLY;\s*BYDAY=(SU|MO|TU|WE|TH|FR|SA)\b", combined, re.I)
    if not (cal and weekly):
        raise ValueError("Local-time calendar schedule unavailable; retaining previous data")
    hour,minute=map(int,cal.group(1).split(":"))
    finish=cal.group(2)
    if hour>23 or minute>59:
        raise ValueError("Invalid start time")
    day=DAY_CODES[weekly.group(1).upper()]
    if day!=3 or (hour,minute)!=(19,0):
        raise ValueError(f"Meeting schedule changed to weekday {day} {hour:02d}:{minute:02d}; review before publishing")
    if finish!="20:30":
        raise ValueError("Meeting end time changed; review before publishing")
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
