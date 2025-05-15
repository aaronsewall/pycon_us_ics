import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ics import Calendar, Event
import re

from ics.grammar.parse import ContentLine

URL = "https://us.pycon.org/2025/schedule/open-spaces/"


def parse_time(day, time_string):
    # e.g. 'noon - 1 p.m.', '2:15 p.m. - 5 p.m.'
    def to_24h(t):
        t = t.strip().replace("noon", "12:00 pm").replace("midnight", "12:00 am")
        # Accept am, pm with or without periods/spaces
        match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)", t, re.IGNORECASE)
        if not match:
            # Try with space between hour and am/pm
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
    dt_start = datetime.strptime(day, "%Y-%m-%d").replace(hour=start_h, minute=start_m)
    dt_end = datetime.strptime(day, "%Y-%m-%d").replace(hour=end_h, minute=end_m)
    if dt_end <= dt_start:
        dt_end += timedelta(days=1)
    return dt_start, dt_end


def fetch_and_convert(url):
    # Download page
    response = requests.get(url)
    response.raise_for_status()
    html = response.text

    soup = BeautifulSoup(html, "html.parser")
    calendar = Calendar()

    # For each day section
    for daydiv in soup.find_all("div", id=re.compile(r"\d{4}-\d{2}-\d{2}")):
        day_str = daydiv["id"]
        nxt = daydiv.find_next_sibling()
        while nxt and (not nxt.has_attr("id") or not re.match(r"\d{4}-\d{2}-\d{2}", nxt["id"])):
            for card in nxt.find_all("div", class_="open-space-card"):
                title = card.find("b", class_="open-space-name").get_text(strip=True)
                where_time = card.find("small", class_="open-space-where").get_text(strip=True)
                description = card.find("div", class_="open-space-info").get_text(" ", strip=True)
                # 'Room 315 | noon - 1 p.m.'
                try:
                    where, time = where_time.split("|")
                except ValueError:
                    print(f"Skipping event (couldn't parse location/time): {title}")
                    continue
                where = where.strip()
                time = time.strip()
                dt_start, dt_end = parse_time(day_str, time)
                event = Event()
                event.name = f"[open-spaces] {title}"
                event.begin = dt_start
                event.end = dt_end
                event.location = where
                event.description = description
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
