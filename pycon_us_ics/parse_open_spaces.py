import requests
from bs4 import BeautifulSoup
import re
from dateutil import parser as dtparser
import pytz
from ics import Event

from pycon_us_ics.pycon import construct_calendar, PYCON_YEAR, generate_ical_uid

URL = "https://us.pycon.org/2025/events/open-spaces/#planned-open-spaces-so-far"


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def get_planned_open_spaces_ul(soup):
    anchor = soup.find("a", id="planned-open-spaces")
    if not anchor:
        raise Exception("Anchor for open spaces not found!")
    return anchor.find_next("ul")


def get_first_text(li):
    """Return the text content from the <li>, up to the first <ul> (not in <ul>)."""
    pieces = []
    for el in li.contents:
        if getattr(el, "name", None) == "ul":
            break
        if isinstance(el, str):
            pieces.append(el.strip())
        elif getattr(el, "name", None) == "b":
            pieces.append(el.get_text().strip())
    return " ".join(pieces).strip()


def parse_event(li):
    bold = li.find("b")
    if not bold:
        return None
    title = bold.get_text().strip(" –-:")

    eventline = get_first_text(li)
    rest = eventline.replace(bold.get_text(), "", 1).strip(" –-:")

    desc = ""
    child_ul = li.find("ul")
    if child_ul:
        desc_li = child_ul.find("li")
        if desc_li:
            desc = desc_li.get_text(separator=" ", strip=True)
    return title, rest, desc


def parse_time_string(time_str):
    # Ex: "Friday, May 16th; 12:00 PM - 1:00 PM EST" or other variants
    # Remove MDY suffix
    time_str = time_str.replace("\u200b", "").replace("\u200e", "").strip()
    match1 = re.match(r".*?, (.*?)\; (.*?)\s*-\s*(.*?) ?(EST|EDT)?$", time_str)
    match2 = re.match(r".*?, (.*?)\; (.*?) (.*?) (EST|EDT)?$", time_str)
    match3 = re.match(r".*?, (.*?)\; (.*?)\s*–\s*(.*?) ?(EST|EDT)?$", time_str)

    if match1:
        date_str, start, end, tz = match1.groups()
    elif match3:
        date_str, start, end, tz = match3.groups()
    elif match2:  # e.g., "Sunday, May 18th; 11:00 AM 12:00 PM EST"
        date_str, start, end, tz = match2.groups()
    else:
        raise ValueError(f"Unrecognized time string: {time_str}")

    tz = tz or "EST"
    # May 16th -> May 16
    date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str)
    # 2025 is hardcoded for now
    year = 2025
    start_str = f"{date_str} {year} {start} {tz}"
    end_str = f"{date_str} {year} {end} {tz}"
    eastern = pytz.timezone("US/Eastern")

    start_dt = dtparser.parse(start_str, ignoretz=True)
    start_dt = eastern.localize(start_dt)
    end_dt = dtparser.parse(end_str, ignoretz=True)
    end_dt = eastern.localize(end_dt)
    return start_dt, end_dt


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    event_ul = get_planned_open_spaces_ul(soup)

    events = []
    for li in event_ul.find_all("li", recursive=False):
        ev = parse_event(li)
        if not ev:
            continue
        title, time_str, desc = ev
        if ";" not in time_str:
            continue
        try:
            start, end = parse_time_string(time_str)
        except Exception as e:
            print(f"Skipping '{title}' due to time parsing: {e}")
            continue
        events.append({"title": title, "start": start, "end": end, "desc": desc})
    with open("../docs/open_spaces.ics", "w") as f:
        f.write(
            construct_calendar(
                events=[
                    Event(
                        name=f'[open-spaces] {ev["title"]}',
                        begin=ev["start"],
                        end=ev["end"],
                        location="TBD",
                        uid=generate_ical_uid(ev["title"]),
                        description=ev["desc"],
                        transparent=False,
                        status="CONFIRMED",
                        url="https://us.pycon.org/2025/events/open-spaces/",
                    )
                    for ev in events
                ],
                extra_metadata={"X-WR-CALNAME": f"PyCon {PYCON_YEAR} Open Spaces"},
            ).serialize()
        )


if __name__ == "__main__":
    main()
