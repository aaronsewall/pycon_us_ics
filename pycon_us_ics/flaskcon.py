import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from ics import Calendar, Event
import re

from ics.grammar.parse import ContentLine

from pycon_us_ics.pycon import PYCON_YEAR

URL = "https://us.pycon.org/2025/events/flaskcon/"
DATE = "2025-05-16"  # <-- UPDATE to the actual FlaskCon date if you know it!
TIMEZONE = "US/Eastern"
LOCATION = "Room 317"  # Set a room if you know it


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def parse_time(timestr):
    """Parses time like '14:45 - 15:15' and returns (start, end) as hour/minute ints."""
    timestr = timestr.strip()
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", timestr)
    if not m:
        return None, None
    h1, m1, h2, m2 = map(int, m.groups())
    return (h1, m1, h2, m2)


def parse_schedule_table(soup):
    table = soup.find("caption", string=re.compile("Schedule", re.I)).find_parent("table")
    tz = pytz.timezone(TIMEZONE)
    events = []

    # Skip the first <tr> (header)
    rows = table.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        time_str = cells[0].get_text(" ", strip=True)
        event_str = cells[1].get_text(" ", strip=True)

        res = parse_time(time_str)
        if not res or not event_str:
            print(f"Skipping row: {time_str} / {event_str}")
            continue

        h1, m1, h2, m2 = res
        start = tz.localize(datetime.strptime(f"{DATE} {h1:02}:{m1:02}", "%Y-%m-%d %H:%M"))
        end = tz.localize(datetime.strptime(f"{DATE} {h2:02}:{m2:02}", "%Y-%m-%d %H:%M"))

        events.append({"start": start, "end": end, "title": event_str})
    return events


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    events = parse_schedule_table(soup)
    print(f"Found {len(events)} events.")

    cal = Calendar()
    for ev in events:
        e = Event()
        e.name = ev["title"]
        e.begin = ev["start"]
        e.end = ev["end"]
        e.location = LOCATION
        cal.events.add(e)
        print(f"Added: {e.name} ({ev['start'].strftime('%I:%M')}–{ev['end'].strftime('%I:%M')})")

    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": f"PyCon {PYCON_YEAR} Hatchery: FlaskCon"}
    for name, value in metadata.items():
        cal.extra.append(ContentLine(name=name, params={}, value=value))

    with open("../docs/flaskcon.ics", "w") as f:
        f.writelines(cal)
    print("ICS written to flaskcon.ics")


if __name__ == "__main__":
    main()
