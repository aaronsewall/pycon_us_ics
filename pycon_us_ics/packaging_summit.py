import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from dateutil import parser as dtparser
import pytz
import re

# ---- CONFIG ----
URL = "https://us.pycon.org/2025/events/packaging-summit/#schedule"
DATE = "2025-05-17"  # You may want to confirm/change this date.
LOCATION = "Room 319"
TIMEZONE = "US/Eastern"


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def parse_packaging_schedule(soup):
    import re
    from dateutil import parser as dtparser

    tz = pytz.timezone(TIMEZONE)
    schedule = []

    # Step 1: Find the <h3> with text 'Schedule'
    h3s = soup.find_all("h3")
    target_h3 = None
    for h3 in h3s:
        # Try using get_text().strip(), ignore case, equals 'Schedule'
        if h3.get_text(strip=True).lower() == "schedule":
            target_h3 = h3
            break
    if not target_h3:
        print('[DEBUG] No <h3> with text "Schedule" found in the document.')
        return []

    # Step 2: Find the next <ul> after the Schedule header
    schedule_ul = target_h3.find_next("ul")
    if not schedule_ul:
        print("[DEBUG] No <ul> after the Schedule <h3> found.")
        return []

    for idx, li in enumerate(schedule_ul.find_all("li", recursive=False)):
        btag = li.find("b")
        if not btag:
            print("[DEBUG] Skipping: No <b> tag found.")
            continue
        timestr = btag.get_text(strip=True)
        desc = li.get_text(" ", strip=True)
        desc = re.sub(r"^" + re.escape(timestr) + r"\s*:\s*", "", desc)
        times_match = re.match(
            r"(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)", timestr, re.I
        )
        if not times_match:
            print(f"[DEBUG] Skipping: Could not parse times from {timestr}")
            continue
        start_raw, end_raw = times_match.groups()
        try:
            # Remember to update the date!
            start_dt = dtparser.parse(f"{DATE} {start_raw}")
            end_dt = dtparser.parse(f"{DATE} {end_raw}")
            start_dt = tz.localize(start_dt)
            end_dt = tz.localize(end_dt)
        except Exception as e:
            print(f"[DEBUG] Exception parsing datetimes: {e}")
            continue
        schedule.append({"title": desc, "start": start_dt, "end": end_dt, "location": LOCATION})
    return schedule


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    all_sessions = parse_packaging_schedule(soup)
    print(f"Found {len(all_sessions)} sessions.")

    cal = Calendar()
    for ev in all_sessions:
        event = Event()
        event.name = f'[packaging-summit] {ev["title"]}'
        event.begin = ev["start"]
        event.end = ev["end"]
        event.location = ev["location"]
        cal.events.add(event)
        print(
            f"Added: {event.name} ({ev['start'].strftime('%I:%M%p')}–{ev['end'].strftime('%I:%M%p')}) {LOCATION}"
        )

    # Calendar metadata
    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": "PyCon 2025 Packaging Summit"}
    for name, value in metadata.items():
        cal.extra.append(ContentLine(name=name, params={}, value=value))

    # Write to file
    with open("../docs/packaging_summit.ics", "w") as f:
        f.writelines(cal)
    print("ICS written to packaging_summit.ics")


if __name__ == "__main__":
    main()
