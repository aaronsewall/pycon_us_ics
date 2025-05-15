import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from ics import Calendar, Event
import re
from ics.grammar.parse import ContentLine

URL_MAIN = "https://us.pycon.org/2025/schedule/open-spaces/"
URL_SIGNUP = "https://us.pycon.org/2025/schedule/open-spaces/signup/"


def parse_time(day, time_string):
    # e.g. 'noon - 1 p.m.', '2:15 p.m. - 5 p.m.'
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
    dt_start = datetime.strptime(day, "%Y-%m-%d").replace(hour=start_h, minute=start_m)
    dt_end = datetime.strptime(day, "%Y-%m-%d").replace(hour=end_h, minute=end_m)
    if dt_end <= dt_start:
        dt_end += timedelta(days=1)
    return dt_start, dt_end


def guess_time_for_row(row_to_time, target_row):
    from bisect import bisect_right
    from datetime import datetime, timedelta

    keys = sorted(row_to_time.keys())
    if target_row in row_to_time:
        return row_to_time[target_row]
    idx = bisect_right(keys, target_row)
    if idx == 0 or idx == len(keys):
        return None
    k1, k2 = keys[idx - 1], keys[idx]
    t1 = datetime.strptime(row_to_time[k1], "%I:%M %p")
    t2 = datetime.strptime(row_to_time[k2], "%I:%M %p")
    dt = t2 - t1
    frac = (target_row - k1) / (k2 - k1)
    interpolated = t1 + frac * dt
    return interpolated.strftime("%-I:%M %p")


def normalize_time(timestr):
    # Adds a space before last two letters if needed
    return re.sub(r"(\d)([AP]M)$", r"\1 \2", timestr.upper())


def parse_slots_from_signup(soup):
    """Returns a dict as {(day, room, time): {'reserved': True/False, ...}}"""
    import bisect

    def guess_time_for_row(row_to_time, target_row):
        keys = sorted(row_to_time.keys())
        if target_row in row_to_time:
            print(f"  Interpolated (exact match) row {target_row} -> {row_to_time[target_row]}")
            return row_to_time[target_row]
        idx = bisect.bisect_right(keys, target_row)
        if idx == 0 or idx == len(keys):
            print(f"  Interpolated row {target_row} out of bounds, cannot map")
            return None
        k1, k2 = keys[idx - 1], keys[idx]
        t1 = datetime.strptime(row_to_time[k1], "%I:%M %p")
        t2 = datetime.strptime(row_to_time[k2], "%I:%M %p")
        delta = t2 - t1
        frac = (target_row - k1) / (k2 - k1)
        interpolated = t1 + frac * delta
        print(
            f"  Interpolating row {target_row}: {k1}={row_to_time[k1]}, {k2}={row_to_time[k2]}, frac={frac:.2f} => {interpolated.strftime('%-I:%M %p')}"
        )
        return interpolated.strftime("%-I:%M %p")

    grid_info = {}
    for day_div in soup.find_all("div", id=re.compile(r"\d{4}-\d{2}-\d{2}")):
        day = day_div["id"]
        print(f"Day div found: {day}")
        calendar_div = day_div.find_next_sibling(class_="calendar")
        if not calendar_div:
            print(f" No calendar found after day {day}")
            continue

        # Get rooms
        rooms = []
        print("\n  Room DOM texts:")
        for d in calendar_div.find_all("div", class_="calendar-room"):
            txt = d.get_text(separator="|", strip=True)
            print(f"    RAW: {txt!r}")
            # Pure extraction
            room = txt.split("Capacity")[0].replace("|", " ").strip()
            print(f"    CLEANED: {room!r}")
            rooms.append(room)
        print(f"  Rooms for calendar: {rooms}")
        room_for_col = {idx + 2: room for idx, room in enumerate(rooms)}
        print(f"  room_for_col mapping: {room_for_col}")

        # Map grid-row-start to time string
        row_to_time = {}
        print("\n  <time> DOM texts and their grid-row values:")
        for time_tag in calendar_div.find_all("time", class_="calendar-time"):
            style = time_tag.get("style", "")
            print(f"    time_tag style={style!r} text={time_tag.get_text()!r}")
            m_row = re.search(r"grid-row-start:\s*(\d+)", style)
            if m_row:
                grid_row = int(m_row.group(1))
                time_str = time_tag.get_text().strip()
                row_to_time[grid_row] = time_str
                print(f"    row_to_time[{grid_row}] = {time_str}")
        print(f"  FULL row_to_time mapping: {row_to_time}")

        # Parse slot sections
        slot_count = 0
        for section in calendar_div.find_all("section", class_=re.compile("slot")):
            style = section.get("style", "")
            m_col = re.search(r"grid-column-start:\s*(\d+)", style)
            m_row_start = re.search(r"grid-row-start:\s*(\d+)", style)
            m_row_end = re.search(r"grid-row-end:\s*(\d+)", style)
            if not (m_col and m_row_start and m_row_end):
                print(f"      Unable to parse slot's style: {style}")
                continue
            col = int(m_col.group(1))
            row_start = int(m_row_start.group(1))
            row_end = int(m_row_end.group(1))
            room = room_for_col.get(col, None)
            print(f"    + Found slot: col={col} ({room}), rows={row_start}-{row_end}")
            t_start_str = guess_time_for_row(row_to_time, row_start)
            t_end_str = guess_time_for_row(row_to_time, row_end)
            if not (t_start_str and t_end_str):
                print(f"      No time mapping found for rows {row_start}, {row_end}")
                continue
            print(f"      --> start {row_start} = {t_start_str}; end {row_end} = {t_end_str}")
            try:
                t_start = datetime.strptime(normalize_time(t_start_str), "%I:%M %p")
                t_end = datetime.strptime(normalize_time(t_end_str), "%I:%M %p")
            except Exception as e:
                print(f"      Failed to parse times: '{t_start_str}' '{t_end_str}' ({e})")
                continue
            time_range = f"{t_start.strftime('%-I:%M %p')} - {t_end.strftime('%-I:%M %p')}"
            reserved = bool(section.find("div", class_="open-space-reserved"))
            print(f"      Reserved? {reserved}")
            slot_key = (day, room, time_range)
            grid_info[slot_key] = {"reserved": reserved, "time": time_range}
            slot_count += 1
        print(f"  Found {slot_count} slots for this calendar.")

    print(f"Total slots parsed: {len(grid_info)}")
    return grid_info


def fetch_and_convert(url_main, url_signup):
    # Download/parse both pages
    soup_main = BeautifulSoup(requests.get(url_main).text, "html.parser")
    soup_signup = BeautifulSoup(requests.get(url_signup).text, "html.parser")

    calendar = Calendar()
    existing_events = set()  # (day, room, time_range)

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
                dt_start, dt_end = parse_time(day_str, time)
                event = Event()
                event.name = f"[open-spaces] {title}"
                event.begin = dt_start
                event.end = dt_end
                event.location = where
                event.description = description
                calendar.events.add(event)
                key = (day_str, where, time)
                existing_events.add(key)
            nxt = nxt.find_next_sibling()

    # 2. Parse the signup grid for reserved slots
    slots = parse_slots_from_signup(soup_signup)
    # For slots that are reserved but not in existing_events, add placeholder event
    for (day, room, time_range), slot in slots.items():
        if slot.get("reserved") and (day, room, time_range) not in existing_events:
            try:
                dt_start, dt_end = parse_time(day, time_range)
            except Exception as e:
                print(
                    f"Couldn't parse grid slot time {time_range}, skipping placeholder event ({e})"
                )
                continue
            event = Event()
            event.name = "[open-spaces] Reserved Slot"
            event.begin = dt_start
            event.end = dt_end
            event.location = room
            event.description = "This slot is reserved, but the event has not been published yet."
            calendar.events.add(event)

    # Add calendar metadata
    metadata = {"CALSCALE": "GREGORIAN", "X-WR-CALNAME": "PyCon 2025 Open Spaces"}
    for name, value in metadata.items():
        calendar.extra.append(ContentLine(name=name, params={}, value=value))
    with open("../docs/open_spaces.ics", "w") as f:
        f.writelines(calendar)
    print("ICS file created: open_spaces.ics")


if __name__ == "__main__":
    fetch_and_convert(URL_MAIN, URL_SIGNUP)
