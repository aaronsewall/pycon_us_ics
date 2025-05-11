import itertools
import os.path
import uuid
from typing import List, Dict

import numpy as np
import pandas as pd
import requests
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

from pycon_us_ics.model import Schedule, ScheduleItem, Speaker

PYCON_YEAR = 2025

resp = requests.get(f"https://us.pycon.org/{PYCON_YEAR}/schedule/conference.json")
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
posters_session_item = next(
    (i for i in schedule_model.schedule if i.name == "Posters Session"), None
)
poster_schedule_items = []
if posters_session_item and posters_session_item.sessions:
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


def construct_event(schedule_item: ScheduleItem) -> Event:
    return Event(
        name=f"[{schedule_item.kind}] {schedule_item.name}",
        begin=schedule_item.start,
        end=schedule_item.end,
        location=schedule_item.room,
        uid=generate_ical_uid(str(schedule_item.conf_key)),
        description=format_description(schedule_item),
        transparent=False,
        status="CANCELLED" if schedule_item.cancelled else "CONFIRMED",
        url=schedule_item.conf_url,
    )


def construct_calendar(events: List[Event], extra_metadata: Dict[str, str]) -> Calendar:
    calendar = Calendar(events=events)
    default_metadata = {"CALSCALE": "GREGORIAN"}
    for name, value in {**default_metadata, **extra_metadata}.items():
        calendar.extra.append(ContentLine(name=name, params={}, value=value))
    return calendar


for key, group in itertools.groupby(
    sorted(schedule_items + poster_schedule_items, key=lambda si: (si.kind, si.conf_key)),
    key=lambda si: si.kind,
):
    with open(os.path.abspath(f"../docs/kind/{key}.ics"), "w") as f:
        f.write(
            construct_calendar(
                events=[construct_event(si) for si in group],
                extra_metadata={"X-WR-CALNAME": f"PyCon {PYCON_YEAR} {key.capitalize()}"},
            ).serialize()
        )

for key, group in itertools.groupby(
    sorted(schedule_items + poster_schedule_items, key=lambda si: (si.section, si.conf_key)),
    key=lambda si: si.section,
):
    with open(os.path.abspath(f"../docs/section/{key}.ics"), "w") as f:
        f.write(
            construct_calendar(
                events=[construct_event(si) for si in group],
                extra_metadata={"X-WR-CALNAME": f"PyCon {PYCON_YEAR} {key.capitalize()}"},
            ).serialize()
        )

with open("../docs/all_events.ics", "w") as f:
    f.write(
        construct_calendar(
            events=[
                construct_event(schedule_item)
                for schedule_item in sorted(
                    schedule_items + poster_schedule_items, key=lambda si: si.conf_key
                )
            ],
            extra_metadata={"X-WR-CALNAME": f"PyCon {PYCON_YEAR} All Events"},
        ).serialize()
    )
