import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
from ics import Calendar, Event
import re

from ics.grammar.parse import ContentLine

from pycon_us_ics.pycon import PYCON_YEAR, generate_ical_uid

URL = "https://us.pycon.org/2025/events/community-organizers-summit/#cfp-for-show-amp-tell"

DATE = "2025-05-17"  # UPDATE as needed!
TIMEZONE = "US/Eastern"
LOCATION = "Room 317"  # Update if/when you know the room/venue
DEFAULT_LAST_DURATION_MINUTES = 30


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def clean_time(timestr):
    # Fixes things like "1135am" -> "11:35am"
    timestr = timestr.strip().lower()
    if re.match(r"^\d{3,4}am|pm$", timestr):
        # e.g., 1135am or 1245pm
        base = timestr[:-2]
        if len(base) == 3:
            base = "0" + base  # 935am -> 0935am
        hour = base[:-2]
        minute = base[-2:]
        ampm = timestr[-2:]
        return f"{hour}:{minute}{ampm}"
    return timestr


def parse_schedule_table(soup):
    table = soup.find("caption", string=re.compile("Summit Schedule", re.I)).find_parent("table")
    rows = table.find("tbody").find_all("tr")
    entries = []
    tz = pytz.timezone(TIMEZONE)

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        rawtime = cells[0].get_text(strip=True)
        time_str = clean_time(rawtime)
        title = cells[1].get_text(" ", strip=True)
        try:
            t = tz.localize(datetime.strptime(f"{DATE} {time_str}", "%Y-%m-%d %I:%M%p"))
        except ValueError as e:
            print(f"Skipping row, unparseable time '{time_str}': {title} ({e})")
            continue
        entries.append({"start": t, "title": title, "rawtime": time_str, "row": row})

    # Infer end time as the next entry's start
    events = []
    for idx, entry in enumerate(entries):
        start = entry["start"]
        if idx + 1 < len(entries):
            end = entries[idx + 1]["start"]
        else:
            # Last event duration is a guess
            end = start + timedelta(minutes=DEFAULT_LAST_DURATION_MINUTES)
        events.append({"start": start, "end": end, "title": entry["title"]})
    return events


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    events = parse_schedule_table(soup)
    print(f"Found {len(events)} events.")

    cal = Calendar()
    for ev in events:
        e = Event()
        e.name = f'[community-organizers-summit] {ev["title"]}'
        e.begin = ev["start"]
        e.end = ev["end"]
        e.location = LOCATION
        e.uid = generate_ical_uid(e.name)
        cal.events.add(e)
        print(
            f"Added: {e.name} ({ev['start'].strftime('%I:%M %p')}–{ev['end'].strftime('%I:%M %p')})"
        )
    metadata = {
        "CALSCALE": "GREGORIAN",
        "X-WR-CALNAME": f"PyCon {PYCON_YEAR} Hatchery: Community Organizers Summit",
    }
    for name, value in metadata.items():
        cal.extra.append(ContentLine(name=name, params={}, value=value))

    with open("../docs/community_organizers_summit.ics", "w") as f:
        f.writelines(cal)
    print("ICS written to community_organizers_summit.ics")


if __name__ == "__main__":
    main()
