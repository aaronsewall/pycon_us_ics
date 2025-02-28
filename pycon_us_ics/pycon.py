import numpy as np
import uuid
import pandas as pd
import requests
from ics import Calendar, Event

from pycon_us_ics.model import Schedule, ScheduleItem, Speaker

resp = requests.get("https://us.pycon.org/2025/schedule/conference.json")
schedule_model = Schedule.model_validate(resp.json())
schedule_df = (
    pd.json_normalize(s.model_dump() for s in schedule_model.schedule)
    .replace({None: np.nan})
    .assign(
        speaker_ids=lambda df: df.speakers.apply(
            lambda xs: [] if isinstance(xs, float) and pd.isna(xs) else [x["id"] for x in xs]
        )
    )
)
posters_session_item = next(i for i in schedule_model.schedule if i.name == "Posters Session")
poster_schedule_items = []
if posters_session_item.sessions:
    posters_df = pd.json_normalize(schedule_df.sessions.dropna().explode()).assign(
        speaker_ids=lambda df: df.speakers.apply(
            lambda xs: [] if isinstance(xs, float) and pd.isna(xs) else [x["id"] for x in xs]
        ),
        start=posters_session_item.start,
        end=posters_session_item.end,
        duration=posters_session_item.duration,
        room=posters_session_item.room,
        rooms=lambda df: len(df) * [posters_session_item.rooms],
        list_render=False,
        released=True,
        tags="",
        license="CC BY",
        kind=posters_session_item.kind,
        section=posters_session_item.section,
    )
    poster_schedule_items = [
        ScheduleItem.model_validate(schedule_item)
        for schedule_item in posters_df.replace(np.nan, None).to_dict(orient="records")
    ]

schedule_items = [
    ScheduleItem.model_validate(schedule_item)
    for schedule_item in schedule_df.replace(np.nan, None).to_dict(orient="records")
]


# TODO we can double check duration but can't provide both that and end


def format_speaker(speaker: Speaker) -> str:
    return f"{speaker.name}\n{speaker.bio}"


def format_description(schedule_item: ScheduleItem) -> str:
    desc = f"Section: {schedule_item.section}\nKind: {schedule_item.kind}\nName: {schedule_item.name}\n"
    if schedule_item.conf_url is not None:
        desc += schedule_item.conf_url + "\n"
    desc += schedule_item.description + "\n"
    if schedule_item.speakers is not None:
        desc += "Speakers:\n" + "\n".join([format_speaker(s) for s in schedule_item.speakers])
    return desc


def generate_ical_uid(short_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, short_id))


events = [
    Event(
        name=f"[{schedule_item.kind}] {schedule_item.name}",
        begin=schedule_item.start,
        end=schedule_item.end,
        location=schedule_item.room,
        uid=generate_ical_uid(str(schedule_item.conf_key)),
        categories=[schedule_item.section, schedule_item.kind],
        description=format_description(schedule_item),
        transparent=False,
        status="CANCELLED" if schedule_item.cancelled else "CONFIRMED",
        url=schedule_item.conf_url,
    )
    for schedule_item in schedule_items
    + (poster_schedule_items if posters_session_item.sessions else [])
]
c = Calendar(events=events)
with open("../docs/events.ics", "w") as f:
    f.write(c.serialize())
