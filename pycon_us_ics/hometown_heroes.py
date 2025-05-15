import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser as dtparser
import pytz
from ics import Calendar, Event
import re

from pycon_us_ics.pycon import construct_calendar, generate_ical_uid, PYCON_YEAR

URL = "https://us.pycon.org/2025/events/hometown-heroes/#talk-schedule"


def fetch_html():
    resp = requests.get(URL)
    resp.raise_for_status()
    return resp.text


def get_talk_blocks(soup):
    # Seek the <a id="talk-schedule">, then iterate following <div class="block-paragraph">
    anchor = soup.find("a", id="talk-schedule")
    blocks = []
    # Following siblings from anchor
    d = (
        anchor.parent.parent.parent
    )  # Find the <div class="block-paragraph"><div class="text-left"><h3>...</h3>
    # Next blocks until next h3 (bios)
    cur = d.find_next_sibling("div")
    while cur:
        h3 = cur.find("h3")
        # Stop at bios section
        if h3 and h3.text.strip().upper().startswith("SPEAKER BIOS"):
            break
        # Only add blocks that are a talk (contain h4 with i)
        h4 = cur.find("h4")
        if h4 and h4.find("i"):
            blocks.append(cur)
        cur = cur.find_next_sibling("div")
    return blocks


def parse_time(timestr):
    # "1:45pm - 2:15pm"
    match = re.match(r"(\d+\:\d+\s*[aApP][mM])\s*-\s*(\d+\:\d+\s*[aApP][mM])", timestr)
    if not match:
        raise Exception(f"Could not parse times: {timestr}")
    start_str, end_str = match.groups()
    # Known date for event: Saturday, May 17th, 2025 (from context)
    date_str = "May 17 2025"
    # PyCon US is US/Eastern tz
    eastern = pytz.timezone("US/Eastern")
    start_dt = dtparser.parse(f"{date_str} {start_str}")
    end_dt = dtparser.parse(f"{date_str} {end_str}")
    start_dt = eastern.localize(start_dt)
    end_dt = eastern.localize(end_dt)
    return start_dt, end_dt


def parse_talk_div(div):
    title_tag = div.find("h4")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)

    ps = div.find_all("p")
    # Time
    time_p = next((p for p in ps if p.get_text(strip=True).startswith("Time:")), None)
    time_str = time_p.get_text(strip=True).replace("Time:", "").strip() if time_p else ""
    # Speakers
    speaker_p = next((p for p in ps if "Speaker:" in p.get_text()), None)
    speakers = ""
    if speaker_p:
        # Remove label
        txt = speaker_p.get_text(separator=" ").strip()
        idx = txt.find("Speaker:")
        if idx == -1:
            idx = txt.find("Speakers:")
        speakers = txt[idx + 8 :].strip()
    # Description (all <p>'s after the speakers line, excluding Time and Speaker)
    desc_ps = []
    found_speaker = False
    for p in ps:
        txt = p.get_text(strip=True)
        if txt.startswith("Time:") or "Speaker:" in txt or "Speakers:" in txt:
            if "Speaker" in txt:
                found_speaker = True
            continue
        if found_speaker:
            desc_ps.append(p)
    description = "\n\n".join(p.get_text(" ", strip=True) for p in desc_ps)
    # Parse times
    try:
        start_dt, end_dt = parse_time(time_str)
    except Exception as e:
        start_dt = end_dt = None
    return dict(title=title, start=start_dt, end=end_dt, speakers=speakers, description=description)


def main():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    talk_blocks = get_talk_blocks(soup)
    print(f"Found {len(talk_blocks)} talks")
    talks = []
    for block in talk_blocks:
        talk = parse_talk_div(block)
        if not talk or not talk["start"]:
            print(f"Skipping (unparseable): {talk}")
            continue
        talks.append(talk)

    with open("../docs/hometown_heroes.ics", "w") as f:
        f.write(
            construct_calendar(
                events=[
                    Event(
                        name=f'[hometown-heroes] {talk["title"]}',
                        begin=talk["start"],
                        end=talk["end"],
                        location="Room 317",
                        uid=generate_ical_uid(talk["title"]),
                        description=f"Speakers: {talk['speakers']}\n\n{talk['description']}",
                        transparent=False,
                        status="CONFIRMED",
                        url="https://us.pycon.org/2025/events/hometown-heroes/#talk-schedule",
                    )
                    for talk in talks
                ],
                extra_metadata={"X-WR-CALNAME": f"PyCon {PYCON_YEAR} Hatchery: Hometown Heroes"},
            ).serialize()
        )


if __name__ == "__main__":
    main()
