import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import pytz
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

from pycon_us_ics.pycon import PYCON_YEAR

URL = "https://us.pycon.org/2025/events/language-summit/#schedule"

TIMEZONE = "US/Eastern"
DATE = "2025-05-14"
LOCATION = "403+404"
DEFAULT_LAST_DURATION_MINUTES = 15


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def parse_schedule_section(soup):
    schedule_anchor = soup.find("a", id="schedule")
    p = schedule_anchor.find_next("p")
    # Some PyCon HTML puts everything in one <p> with embedded <br/>
    if not p:
        print("No <p> found after 'schedule' anchor!")
        return []
    # Use BeautifulSoup to split on <br> tags properly
    # The .children generator yields NavigableStrings and Tag (<br>)
    lines = []
    current = ""
    for child in p.children:
        if isinstance(child, str):
            current += child
        elif getattr(child, "name", None) == "br":
            if current.strip():
                lines.append(current.strip())
            current = ""
        elif getattr(child, "name", None):
            # for any other tag, add its text
            current += child.get_text()
    if current.strip():
        lines.append(current.strip())

    tz = pytz.timezone(TIMEZONE)
    events_raw = []

    for idx, line in enumerate(lines):
        # Strip HTML tags from the line for text parsing, but keep info for <b> and <i>.
        texthtml = BeautifulSoup(line, "html.parser")
        plain = texthtml.get_text(" ", strip=True)
        m = re.match(r"^(\d{1,2}:\d{2}\s*[APap][mM])\s*(.*)", plain)
        if m:
            cur_time_str, rest = m.groups()
            try:
                start = tz.localize(
                    datetime.strptime(f"{DATE} {cur_time_str.upper()}", "%Y-%m-%d %I:%M %p")
                )
            except Exception as e:
                print(f"DEBUG: Failed to parse datetime for '{cur_time_str}': {e}")
                continue
            # Title
            title_tag = texthtml.find("b")
            title = title_tag.get_text(" ", strip=True) if title_tag else rest
            # Speaker(s)
            speaker_elem = texthtml.find("i")
            if speaker_elem:
                speaker = speaker_elem.get_text(" ", strip=True)
            elif "with" in rest:
                speaker = rest.split("with", 1)[-1].strip(" -")
            else:
                speaker = ""
            events_raw.append(
                {
                    "start": start,
                    "title": title,
                    "speaker": speaker,
                    "location": LOCATION,
                    "line": line,
                }
            )
        else:
            print(f"DEBUG: Skipping line {idx} (no time parse): {repr(line)}")

    # Infer end times
    events = []
    for idx, event in enumerate(events_raw):
        this_start = event["start"]
        if idx + 1 < len(events_raw):
            next_start = events_raw[idx + 1]["start"]
            end = next_start
        else:
            end = this_start + timedelta(minutes=DEFAULT_LAST_DURATION_MINUTES)
        # Tag breaks/info events
        lower_title = event["title"].lower()
        is_break = any(word in lower_title for word in ("break", "lunch", "photo", "done"))
        events.append(
            {
                "start": this_start,
                "end": end,
                "title": event["title"],
                "speaker": event["speaker"],
                "location": LOCATION,
                "is_break": is_break,
            }
        )
    return events


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    events = parse_schedule_section(soup)
    print(f"\nFound {len(events)} scheduled events.")
    cal = Calendar()
    for ev in events:
        e = Event()
        e.begin = ev["start"]
        e.end = ev["end"]
        e.name = ev["title"].replace("--", "").strip()
        e.location = ev["location"]
        if ev["speaker"] and not ev["is_break"]:
            e.description = ev["speaker"]
        if ev["is_break"]:
            e.categories = {"Break"}
        cal.events.add(e)
        print(f"Added: {e.begin.strftime('%I:%M%p')}–{e.end.strftime('%I:%M%p')} {e.name}")
    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": f"PyCon {PYCON_YEAR} Language Summit"}
    for name, value in metadata.items():
        cal.extra.append(ContentLine(name=name, params={}, value=value))

    with open("../docs/language_summit.ics", "w") as f:
        f.writelines(cal)
    print("ICS written to language_summit.ics")


if __name__ == "__main__":
    main()
