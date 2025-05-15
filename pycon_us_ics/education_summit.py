import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from datetime import datetime, timedelta
import pytz
from ics import Calendar, Event
import re

from ics.grammar.parse import ContentLine

from pycon_us_ics.pycon import PYCON_YEAR, generate_ical_uid

# ---- CONFIG ----
URL = "https://us.pycon.org/2025/events/education-summit/"
DATE = "2025-05-15"
LOCATION = "Room 403/404"
TIMEZONE = "US/Eastern"


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def parse_all_talks(soup):
    schedule = []
    tz = pytz.timezone(TIMEZONE)

    # Helper to find next li with a time label in all_li_list after position i
    def get_next_time_li(li_list, i):
        for j in range(i + 1, len(li_list)):
            text = li_list[j].get_text(" ", strip=True)
            time_match = re.match(r"^(\d{1,2})(:?):{0,2}(\d{2})", text)
            if time_match:
                return li_list[j], text, j
        return None, None, None

    def parse_time_label(text):
        m = re.match(r"^(\d{1,2})(:?):{0,2}(\d{2})\s*-?\s*(.*)", text)
        if m:
            hour, _, minute, label = m.groups()
            hour = int(hour)
            if 1 <= hour < 5:
                hour += 12
            minute = int(minute)
            label = label.strip() or "Session"
            start_dt = tz.localize(
                datetime.strptime(f"{DATE} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
            )
            return start_dt, label
        return None, None

    summary_p = soup.find("b", string=re.compile("schedule", re.I))
    timeblocks = summary_p.find_all_next("ul", limit=2)

    # 1. Collect ALL top-level <li> items into a single in-order list
    all_li_list = []
    for ul in timeblocks:
        all_li_list.extend(ul.find_all("li", recursive=False))

    all_events_unsorted = []

    i = 0
    while i < len(all_li_list):
        li = all_li_list[i]
        text = li.get_text(" ", strip=True)

        # Lightning Talks
        if re.match(r"(?i).*lightning talk", text):
            light_ul = li.find("ul")
            if light_ul:
                time_base = "13:45"
                d = dtparser.parse(f"{DATE} {time_base}")
                for idx, sli in enumerate(light_ul.find_all("li")):
                    t1 = d + timedelta(minutes=idx * 5)
                    t2 = t1 + timedelta(minutes=5)
                    all_events_unsorted.append(
                        {
                            "title": f"Lightning Talk: {sli.get_text(' ', strip=True)}",
                            "start": tz.localize(t1),
                            "end": tz.localize(t2),
                            "location": LOCATION,
                        }
                    )
            i += 1
            continue

        # Block slot with a nested list (Workshops)
        if li.find("ul"):
            block_start, block_label = parse_time_label(text)
            if block_start:
                # Find block end using the flat li list!
                next_time_li, next_text, j = get_next_time_li(all_li_list, i)
                if next_time_li:
                    block_end, _ = parse_time_label(next_text)
                else:
                    block_end = block_start + timedelta(minutes=60)  # Fallback: 1 hour

                inner_ul = li.find("ul")
                workshop_items = []
                for item in inner_ul.find_all("li", recursive=False):
                    if item.find("ul"):
                        # There is another ul; get those lis
                        sub_ul = item.find("ul")
                        for subitem in sub_ul.find_all("li", recursive=False):
                            workshop_items.append(subitem.get_text(" ", strip=True))
                    else:
                        workshop_items.append(item.get_text(" ", strip=True))
                n = len(workshop_items)
                if n == 0:
                    i += 1
                    continue
                slot_mins = int((block_end - block_start).total_seconds()) // 60
                per_event = slot_mins // n
                for idx2, wtitle in enumerate(workshop_items):
                    wstart = block_start + timedelta(minutes=idx2 * per_event)
                    wend = (
                        block_start + timedelta(minutes=(idx2 + 1) * per_event)
                        if idx2 < n - 1
                        else block_end
                    )
                    all_events_unsorted.append(
                        {
                            "title": f"Workshop: {wtitle}",
                            "start": wstart,
                            "end": wend,
                            "location": LOCATION,
                        }
                    )
            i += 1
            continue

        # Remaining slots: match times
        slot_start, label = parse_time_label(text)
        if slot_start:
            next_time_li, next_text, j = get_next_time_li(all_li_list, i)
            if next_time_li:
                slot_end, _ = parse_time_label(next_text)
            else:
                # fallback (last session): 25/20 min
                if "break" in label.lower() or "lunch" in label.lower():
                    slot_end = slot_start + timedelta(minutes=20)
                else:
                    slot_end = slot_start + timedelta(minutes=25)
            all_events_unsorted.append(
                {"title": label, "start": slot_start, "end": slot_end, "location": LOCATION}
            )
        i += 1

    # Final: sort by start time for correct order
    all_events_unsorted.sort(key=lambda x: x["start"])
    return all_events_unsorted


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    all_talks = parse_all_talks(soup)
    print(f"Found {len(all_talks)} sessions/talks.")

    cal = Calendar()
    for ev in all_talks:
        event = Event()
        event.name = f'[education-summit] {ev["title"]}'
        event.begin = ev["start"]
        event.end = ev["end"]
        event.location = ev["location"]
        event.uid = generate_ical_uid(event.name)
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
