import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ics import Calendar, Event
import re
from ics.grammar.parse import ContentLine

URL_MAIN = "https://us.pycon.org/2025/schedule/open-spaces/"
URL_SIGNUP = "https://us.pycon.org/2025/schedule/open-spaces/signup/"


def normalize_time(timestr):
    # Clean up: remove dots, change to uppercase, remove spaces.
    timestr = timestr.strip().replace(".", "").replace(" ", "").upper()
    # Expand NOON/MIDNIGHT
    timestr = timestr.replace("NOON", "12:00PM").replace("MIDNIGHT", "12:00AM")
    # Ensure minutes are present.
    m = re.match(r"^(\d{1,2})([AP]M)$", timestr)  # 1PM
    if m:
        timestr = f"{m.group(1)}:00{m.group(2)}"  # → 1:00PM
    return timestr


def normalize_time_range(time_range):
    tr = time_range.strip()
    tr = tr.replace("a.m.", "AM").replace("p.m.", "PM").replace("A.M.", "AM").replace("P.M.", "PM")
    tr = re.sub(r"\s+", "", tr)
    if "-" not in tr:
        raise ValueError(f"Malformed time range: '{time_range}'")
    t1, t2 = tr.split("-", 1)
    t1 = normalize_time(t1)
    t2 = normalize_time(t2)
    t1_dt = datetime.strptime(t1, "%I:%M%p")
    t2_dt = datetime.strptime(t2, "%I:%M%p")
    return f"{t1_dt.strftime('%H:%M')}-{t2_dt.strftime('%H:%M')}"


def parse_time(day, time_string):
    """Given day ('2025-05-16') and e.g. 'noon - 1 p.m.', return two datetimes."""

    def to_24h(t):
        t = t.strip().replace("noon", "12:00 pm").replace("midnight", "12:00 am")
        # Remove dots for easier matching
        t = t.replace(".", "")
        match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", t, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            ampm = match.group(3).lower()
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


def parse_slots_from_signup(soup):
    """Returns a dict as {(day, room, normalized_time): {'reserved': True/False, ...}}"""
    import bisect

    def guess_time_for_row(row_to_time, target_row):
        keys = sorted(row_to_time.keys())
        if target_row in row_to_time:
            return row_to_time[target_row]
        idx = bisect.bisect_right(keys, target_row)
        if idx == 0 or idx == len(keys):
            return None
        k1, k2 = keys[idx - 1], keys[idx]
        t1 = datetime.strptime(normalize_time(row_to_time[k1]), "%I:%M %p")
        t2 = datetime.strptime(normalize_time(row_to_time[k2]), "%I:%M %p")
        delta = t2 - t1
        frac = (target_row - k1) / (k2 - k1)
        interpolated = t1 + frac * delta
        return interpolated.strftime("%I:%M%p")

    grid_info = {}
    for day_div in soup.find_all("div", id=re.compile(r"\d{4}-\d{2}-\d{2}")):
        day = day_div["id"]
        calendar_div = day_div.find_next_sibling(class_="calendar")
        if not calendar_div:
            continue

        # Get room labels
        rooms = []
        for d in calendar_div.find_all("div", class_="calendar-room"):
            txt = d.get_text(separator="|", strip=True)
            room = txt.split("Capacity")[0].replace("|", " ").strip()
            rooms.append(room)
        room_for_col = {idx + 2: room for idx, room in enumerate(rooms)}

        # Map grid-row-start to time string
        row_to_time = {}
        for time_tag in calendar_div.find_all("time", class_="calendar-time"):
            style = time_tag.get("style", "")
            m_row = re.search(r"grid-row-start:\s*(\d+)", style)
            if m_row:
                grid_row = int(m_row.group(1))
                time_str = time_tag.get_text().strip()
                row_to_time[grid_row] = time_str

        # Parse slot sections
        for section in calendar_div.find_all("section", class_=re.compile("slot")):
            style = section.get("style", "")
            m_col = re.search(r"grid-column-start:\s*(\d+)", style)
            m_row_start = re.search(r"grid-row-start:\s*(\d+)", style)
            m_row_end = re.search(r"grid-row-end:\s*(\d+)", style)
            if not (m_col and m_row_start and m_row_end):
                continue
            col = int(m_col.group(1))
            row_start = int(m_row_start.group(1))
            row_end = int(m_row_end.group(1))
            room = room_for_col.get(col, None)

            t_start_str = guess_time_for_row(row_to_time, row_start)
            t_end_str = guess_time_for_row(row_to_time, row_end)
            if not (t_start_str and t_end_str):
                continue

            # Normalize times for the key
            t_start_str = normalize_time(t_start_str)
            t_end_str = normalize_time(t_end_str)
            time_range = f"{t_start_str} - {t_end_str}"
            norm_time = normalize_time_range(f"{t_start_str}-{t_end_str}")
            reserved = bool(section.find("div", class_="open-space-reserved"))
            slot_key = (day, room.strip().lower(), norm_time)
            grid_info[slot_key] = {"reserved": reserved, "time": time_range}
    return grid_info


def fetch_and_convert(url_main, url_signup):
    soup_main = BeautifulSoup(requests.get(url_main).text, "html.parser")
    soup_signup = BeautifulSoup(requests.get(url_signup).text, "html.parser")

    calendar = Calendar()
    existing_events = set()  # (day, normalized_room, normalized_time)

    # 1. Parse Open Spaces main schedule for filled events
    for daydiv in soup_main.find_all("div", id=re.compile(r"\d{4}-\d{2}-\d{2}")):
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
                # Normalize key for deduplication (room name and time range)
                norm_room = where.lower().strip()
                try:
                    norm_time = normalize_time_range(time)
                except Exception as e:
                    print(f"Skipping event (couldn't normalize time): {title} ({time}) - {e}")
                    continue
                key = (day_str, norm_room, norm_time)
                existing_events.add(key)

                # Create the event as before
                try:
                    dt_start, dt_end = parse_time(day_str, time)
                except Exception as e:
                    print(f"Skipping event (couldn't parse time): {title} ({time}) - {e}")
                    continue

                event = Event()
                event.name = f"[open-spaces] {title}"
                event.begin = dt_start
                event.end = dt_end
                event.location = where
                event.description = description
                calendar.events.add(event)
            nxt = nxt.find_next_sibling()

    # 2. Parse the signup grid for reserved slots
    slots = parse_slots_from_signup(soup_signup)
    for (day, room, norm_time), slot in slots.items():
        # Check key for deduplication; skip if already exists as a published open space
        if slot.get("reserved") and (day, room.lower().strip(), norm_time) not in existing_events:
            # Unpublished reserved slot: add placeholder event
            # Must convert norm_time back into a time range string for parsing
            try:
                t1_24, t2_24 = norm_time.split("-")
                tformat = "%H:%M"
                t1_hrm = (
                    datetime.strptime(t1_24, tformat)
                    .strftime("%I:%M %p")
                    .lstrip("0")
                    .replace(" 0", " ")
                )
                t2_hrm = (
                    datetime.strptime(t2_24, tformat)
                    .strftime("%I:%M %p")
                    .lstrip("0")
                    .replace(" 0", " ")
                )
                grid_time_range_str = f"{t1_hrm} - {t2_hrm}"
                dt_start, dt_end = parse_time(day, grid_time_range_str)
            except Exception as e:
                print(
                    f"Couldn't parse grid slot time {norm_time}, skipping placeholder event ({e})"
                )
                continue

            event = Event()
            event.name = "[open-spaces] Reserved Slot"
            event.begin = dt_start
            event.end = dt_end
            event.location = room
            event.description = "This slot is reserved, but the event has not been published yet."
            calendar.events.add(event)

    # Calendar metadata
    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": "PyCon 2025 Open Spaces"}
    for name, value in metadata.items():
        calendar.extra.append(ContentLine(name=name, params={}, value=value))

    with open("../docs/open_spaces.ics", "w") as f:
        f.writelines(calendar)
    print("ICS file created: open_spaces.ics")


if __name__ == "__main__":
    fetch_and_convert(URL_MAIN, URL_SIGNUP)
