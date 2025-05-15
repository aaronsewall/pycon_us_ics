import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from ics import Event
import datetime
import pytz
import re

from pycon_us_ics.pycon import construct_calendar, generate_ical_uid, PYCON_YEAR

URL = "https://us.pycon.org/2025/events/maintainers-summit/"


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def parse_schedule_table(soup):
    table = soup.find("caption", string=re.compile("EVENT SCHEDULE", re.I)).find_parent("table")
    rows = table.find("tbody").find_all("tr")

    event_date = "May 17 2025"
    tz = pytz.timezone("US/Eastern")

    # Gather all real scheduled events (with a parseable time)
    events_raw = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        timecell = cells[0].get_text(strip=True)
        titlecell = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        speakercell = cells[2].get_text(strip=True) if len(cells) > 2 else ""

        # Only match rows that are an actual time
        m = re.match(r"(\d{1,2}:\d\d ?[ap]m)", timecell, re.I)
        if m:
            # Parse start time for use in ordering & duration calc
            start_dt = dtparser.parse(event_date + " " + m.group(1))
            start_dt = tz.localize(start_dt)
            events_raw.append({"title": titlecell, "speaker": speakercell, "start": start_dt})
        else:
            continue

    # Now assign end-times from the next event's start
    events = []
    for idx, event in enumerate(events_raw):
        start = event["start"]
        # Last event: guess 30 min unless title indicates closing remarks (set end=None)
        if idx + 1 < len(events_raw):
            end = events_raw[idx + 1]["start"]
        else:
            # last event, default to 30min
            end = start + datetime.timedelta(minutes=30)
        events.append(
            {"title": event["title"], "speaker": event["speaker"], "start": start, "end": end}
        )

    return events


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    schedule = parse_schedule_table(soup)
    print(f"Found {len(schedule)} timed events.")

    with open("../docs/maintainers_summit.ics", "w") as f:
        f.write(
            construct_calendar(
                events=[
                    Event(
                        name=f'[maintainers-summit] {ev["title"]}',
                        begin=ev["start"],
                        end=ev["end"],
                        location="Room 402",
                        uid=generate_ical_uid(ev["title"]),
                        description=f"Speaker(s): {ev['speaker']}",
                        transparent=False,
                        status="CONFIRMED",
                        url="https://us.pycon.org/2025/events/maintainers-summit/",
                    )
                    for ev in schedule
                ],
                extra_metadata={"X-WR-CALNAME": f"PyCon {PYCON_YEAR} Maintainers Summit"},
            ).serialize()
        )


if __name__ == "__main__":
    main()
