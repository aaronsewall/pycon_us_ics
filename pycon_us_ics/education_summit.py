import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from datetime import datetime, timedelta
import pytz
from ics import Calendar, Event
import re

from ics.grammar.parse import ContentLine

from pycon_us_ics.pycon import PYCON_YEAR

# ---- CONFIG ----
URL = "https://us.pycon.org/2025/events/education-summit/"
DATE = "2025-05-15"
LOCATION = "Room 403/404"
TIMEZONE = "US/Eastern"


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def parse_timeslot(timestr, curdate=None):
    # Typical inputs: "9:15 - Teaching..." or "3:00"
    m = re.match(r"^(\d{1,2}):(\d\d)(?:\s*-\s*(.*))?$", timestr.strip())
    if not m:
        # Might be "3::00" typo seen in sample
        m = re.match(r"^(\d{1,2})::(\d\d)(?:\s*-\s*(.*))?$", timestr.strip())

    if m:
        hour, minute, rest = m.groups()
        hour = int(hour)
        minute = int(minute)
        d = dtparser.parse(curdate)
        dt = datetime(year=d.year, month=d.month, day=d.day, hour=hour, minute=minute)
        return dt, rest
    m = re.match(r"^(\d{1,2}):(\d\d)\s*-\s*(\d{1,2}):(\d\d)", timestr.strip())
    if m:
        h1, m1, h2, m2 = map(int, m.groups())
        d = dtparser.parse(curdate)
        dt1 = datetime(year=d.year, month=d.month, day=d.day, hour=h1, minute=m1)
        dt2 = datetime(year=d.year, month=d.month, day=d.day, hour=h2, minute=m2)
        return (dt1, dt2)
    return None, None


def parse_all_talks(soup):
    schedule = []
    tz = pytz.timezone(TIMEZONE)
    summary_p = soup.find("b", string=re.compile("schedule", re.I))
    for ul in summary_p.find_all_next("ul", limit=2):
        for li in ul.find_all("li", recursive=False):
            text = li.get_text(" ", strip=True)
            # Lightning talks: next <ul> are grouped under this
            if re.match(r"(?i).*lightning talk", text):
                light_ul = li.find("ul")
                if light_ul:
                    time_base = "13:45"
                    d = dtparser.parse(f"{DATE} {time_base}")
                    for idx, sli in enumerate(light_ul.find_all("li")):
                        t1 = d + timedelta(minutes=idx * 5)
                        t2 = t1 + timedelta(minutes=5)
                        schedule.append(
                            {
                                "title": f"Lightning Talk: {sli.get_text(' ', strip=True)}",
                                "start": tz.localize(t1),
                                "end": tz.localize(t2),
                                "location": LOCATION,
                            }
                        )
                continue
            # Afternoon workshop: nested <ul> under time slot
            if re.match(r"(?i).*workshop", text):
                tmatch = re.search(r"(\d{1,2}:\d{2})", text)
                if tmatch:
                    t_start = tmatch.group(1)
                    ul2 = li.find("ul")
                    if ul2:
                        d = dtparser.parse(f"{DATE} {t_start}")
                        for idx, sli in enumerate(ul2.find_all("li")):
                            t1 = d + timedelta(minutes=idx * 30)
                            t2 = t1 + timedelta(minutes=30)
                            schedule.append(
                                {
                                    "title": f"Workshop: {sli.get_text(' ', strip=True)}",
                                    "start": tz.localize(t1),
                                    "end": tz.localize(t2),
                                    "location": LOCATION,
                                }
                            )
                continue
            # Try to match slots with time at start, dash optional, label after
            time_match = re.match(r"^(\d{1,2})(:?):(\d{2})\s*-?\s*(.*)", text)
            if time_match:
                hour, colon, minute, label = time_match.groups()
                hour = int(hour)
                minute = int(minute)
                # Fix for possible "3::00"
                if colon == ":" or colon == "":
                    label = label.strip() or "Session"
                    start_dt = tz.localize(
                        datetime.strptime(f"{DATE} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
                    )
                    if "break" in label.lower() or "lunch" in label.lower():
                        end_dt = start_dt + timedelta(minutes=20)
                    else:
                        end_dt = start_dt + timedelta(minutes=25)
                    schedule.append(
                        {"title": label, "start": start_dt, "end": end_dt, "location": LOCATION}
                    )
                continue
            # e.g. "4:30 - Closing"
            if "-" in text:
                tbit, label = text.split("-", 1)
                tbit = tbit.strip()
                label = label.strip() or "Session"
                if re.match(r"\d{1,2}:\d{2}", tbit):
                    start_dt = tz.localize(dtparser.parse(f"{DATE} {tbit}"))
                    end_dt = start_dt + timedelta(minutes=20)
                    schedule.append(
                        {"title": label, "start": start_dt, "end": end_dt, "location": LOCATION}
                    )
    return schedule


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    all_talks = parse_all_talks(soup)
    print(f"Found {len(all_talks)} sessions/talks.")

    cal = Calendar()
    for ev in all_talks:
        event = Event()
        event.name = ev["title"]
        event.begin = ev["start"]
        event.end = ev["end"]
        event.location = ev["location"]
        cal.events.add(event)
        print(
            f"Added: {event.name} ({ev['start'].strftime('%I:%M%p')}–{ev['end'].strftime('%I:%M%p')}) {LOCATION}"
        )
    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": f"PyCon {PYCON_YEAR} Education Summit"}
    for name, value in metadata.items():
        cal.extra.append(ContentLine(name=name, params={}, value=value))

    with open("../docs/education_summit.ics", "w") as f:
        f.writelines(cal)
    print("ICS written to education_summit.ics")


if __name__ == "__main__":
    main()
