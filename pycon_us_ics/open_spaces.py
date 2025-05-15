import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
import re
from ics.grammar.parse import ContentLine
from pycon_us_ics.pycon import generate_ical_uid

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo

URL = "https://us.pycon.org/2025/schedule/open-spaces/"


try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo

CONFERENCE_TZ = ZoneInfo("America/New_York")


def parse_time(day, time_string):
    def to_24h(t):
        t = t.strip().replace("noon", "12:00 pm").replace("midnight", "12:00 am")
        match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)", t, re.IGNORECASE)
        if not match:
            match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", t, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            ampm = match.group(3).replace(".", "").lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            return hour, minute
        raise ValueError("Could not parse time: " + t)

    rng = time_string.split("-")
    start, end = rng[0].strip(), rng[1].strip()
    start_h, start_m = to_24h(start)
    end_h, end_m = to_24h(end)
    dt_start = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=start_h, minute=start_m, tzinfo=CONFERENCE_TZ
    )
    dt_end = datetime.strptime(day, "%Y-%m-%d").replace(
        hour=end_h, minute=end_m, tzinfo=CONFERENCE_TZ
    )
    if dt_end <= dt_start:
        dt_end += timedelta(days=1)
    dt_start_utc = dt_start.astimezone(timezone.utc)
    dt_end_utc = dt_end.astimezone(timezone.utc)
    print(f"  Local:  {dt_start} to {dt_end}")
    print(f"  In UTC: {dt_start_utc} to {dt_end_utc}")
    return dt_start_utc, dt_end_utc


def fetch_and_convert(url):
    response = requests.get(url)
    response.raise_for_status()
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    calendar = Calendar()
    for daydiv in soup.find_all("div", id=re.compile(r"\d{4}-\d{2}-\d{2}")):
        day_str = daydiv["id"]
        nxt = daydiv.find_next_sibling()
        while nxt and (not nxt.has_attr("id") or not re.match(r"\d{4}-\d{2}-\d{2}", nxt["id"])):
            for card in nxt.find_all("div", class_="open-space-card"):
                title = card.find("b", class_="open-space-name").get_text(strip=True)
                where_time = card.find("small", class_="open-space-where").get_text(strip=True)
                description = card.find("div", class_="open-space-info").get_text(" ", strip=True)
                try:
                    where, time = where_time.split("|")
                except ValueError:
                    print(f"Skipping event (couldn't parse location/time): {title}")
                    continue
                where = where.strip()
                time = time.strip()
                print(f"[EVENT] {title} @ {where} [{day_str}]")
                print(f"  Desc: {description[:60]!r}...")
                print(f"  Time string: '{time}'")
                dt_start, dt_end = parse_time(day_str, time)
                print(f"  Parsed Start: {dt_start.isoformat()}  End: {dt_end.isoformat()}")
                print("-" * 50)
                event = Event()
                event.name = f"[open-spaces] {title}"
                event.begin = dt_start
                event.end = dt_end
                event.location = where
                event.description = description
                event.uid = generate_ical_uid(event.name)
                calendar.events.add(event)
            nxt = nxt.find_next_sibling()
    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": "PyCon 2025 Open Spaces"}
    for name, value in metadata.items():
        calendar.extra.append(ContentLine(name=name, params={}, value=value))
    with open("../docs/open_spaces.ics", "w") as f:
        f.writelines(calendar)
    print("ICS file created: open_spaces.ics")


if __name__ == "__main__":
    fetch_and_convert(URL)
