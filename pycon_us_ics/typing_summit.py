import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ics import Calendar, Event
import pytz
from ics.grammar.parse import ContentLine

from pycon_us_ics.pycon import PYCON_YEAR

# ---- CONFIG ----
URL = "https://us.pycon.org/2025/events/typing-summit/#agenda"
DATE = "2025-05-16"  # Friday, May 16th, 2025
START_TIME = "14:00"  # 2pm (24h format)
EVENT_LENGTH_MINUTES = 30
LOCATION = "Room 319"
TIMEZONE = "US/Eastern"


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def parse_agenda_list(soup):
    anchor = soup.find("a", id="agenda")
    if not anchor:
        raise Exception("Agenda anchor not found!")
    ul = anchor.find_next("ul")
    return [li.get_text(strip=True) for li in ul.find_all("li")]


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    agenda_items = parse_agenda_list(soup)
    print(f"Found {len(agenda_items)} agenda items.")

    # Set up timing
    tz = pytz.timezone(TIMEZONE)
    start_time = tz.localize(datetime.strptime(f"{DATE} {START_TIME}", "%Y-%m-%d %H:%M"))

    cal = Calendar()
    for idx, item in enumerate(agenda_items):
        event = Event()
        # Calculate event timing
        ev_start = start_time + timedelta(minutes=idx * EVENT_LENGTH_MINUTES)
        ev_end = ev_start + timedelta(minutes=EVENT_LENGTH_MINUTES)
        event.name = f"[typing-summit] {item}"
        event.begin = ev_start
        event.end = ev_end
        event.location = LOCATION
        cal.events.add(event)
        print(
            f"Added: {event.name} ({ev_start.strftime('%I:%M%p')}–{ev_end.strftime('%I:%M%p')}) {LOCATION}"
        )
    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": f"PyCon {PYCON_YEAR} Typing Summit"}
    for name, value in metadata.items():
        cal.extra.append(ContentLine(name=name, params={}, value=value))

    with open("../docs/typing_summit.ics", "w") as f:
        f.writelines(cal)
    print("ICS written to typing_summit.ics")


if __name__ == "__main__":
    main()
