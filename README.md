# PyCon US hosted calendar 

Conference info is available at https://us.pycon.org/2025/schedule/conference.json

All calendar files are tested to work and are importable by google calendar.

There are some other events that are not included in this conference.json (but most are at this 
point), which I manually made calendar entries for inside google calendar. This calendar is 
available here (it doesn't follow the  same format as the generated calendars, and isn't as well 
maintained, but it helps to know about  other things that are happening). 

https://calendar.google.com/calendar/u/0?cid=OTg5ODFiZmMyZWQ5ZTQ2YWNjZDYwMWY5MGNhZDBmYzJiODA5NmUyYmIzNjAyZDJiODQyZDRmNjBmNDBiZTU2Y0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t

all_events contains every event for the conference that are available in conference.json, but does 
not include open spaces, and summit/hatchery agendas.

You can also select based on the sections you're interested in or the kinds of events.

My preferred way is to use https://github.com/derekantrican/GAS-ICS-Sync to get updates hourly.
If using the normal google sync, updates come every 8, or 12-24 hours (sources vary). GAS-ICS-Sync 
allows for updates hourly, and the github actions cronjob is also configured to run hourly at *:55.
I also prefer to subscribe individually to each calendar in the `kind` area so the colors look 
better in google calendar.

Add them to google calendar manually here:

https://calendar.google.com/calendar/u/0/r/settings/addbyurl

The current URLs for all generated calendars are:

ALL

* https://aaronsewall.github.io/pycon_us_ics/all_events.ics

Section

* https://aaronsewall.github.io/pycon_us_ics/section/events.ics
* https://aaronsewall.github.io/pycon_us_ics/section/posters.ics
* https://aaronsewall.github.io/pycon_us_ics/section/sponsor-presentations.ics
* https://aaronsewall.github.io/pycon_us_ics/section/talks.ics
* https://aaronsewall.github.io/pycon_us_ics/section/tutorials.ics

Kind

* https://aaronsewall.github.io/pycon_us_ics/kind/break.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/charla.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/event.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/informational.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/lightning-talks.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/plenary.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/poster.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/sponsor-workshop.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/summit.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/talk.ics
* https://aaronsewall.github.io/pycon_us_ics/kind/tutorial.ics

Open Spaces

This calendar includes open spaces from this page, but does not include all possible (usually empty)
slots:
https://us.pycon.org/2025/schedule/open-spaces/

To see all open spaces at any given time (depending on when the image was last uploaded), see

* https://aaronsewall.github.io/pycon_us_ics/open_spaces.ics

Summits/Hatchery Agendas

These are individually parsed from the subpages on https://us.pycon.org/2025/events/

Not all events had a schedule, notable exclusions as of 5-14-25 are: 

* WebAssembly Summit

ICS Links

* https://aaronsewall.github.io/pycon_us_ics/community_organizers_summit.ics
* https://aaronsewall.github.io/pycon_us_ics/education_summit.ics
* https://aaronsewall.github.io/pycon_us_ics/flaskcon.ics
* https://aaronsewall.github.io/pycon_us_ics/hometown_heroes.ics
* https://aaronsewall.github.io/pycon_us_ics/language_summit.ics
* https://aaronsewall.github.io/pycon_us_ics/maintainers_summit.ics
* https://aaronsewall.github.io/pycon_us_ics/packaging_summit.ics
* https://aaronsewall.github.io/pycon_us_ics/typing_summit.ics

To subscribe via Google Calendar you can use the following links (note the webcal:// in the urls):

ALL (does not include Open spaces or Summit/Hatchery Agendas)

* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/all_events.ics

Section

* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/section/events.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/section/posters.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/section/sponsor-presentations.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/section/talks.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/section/tutorials.ics

Kind

* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/break.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/charla.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/event.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/informational.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/lightning-talks.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/plenary.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/poster.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/sponsor-workshop.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/summit.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/talk.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/kind/tutorial.ics

Open Spaces

* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/open_spaces.ics

Summit/Hatchery Agendas

* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/community_organizers_summit.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/education_summit.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/flaskcon.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/hometown_heroes.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/language_summit.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/maintainers_summit.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/packaging_summit.ics
* https://calendar.google.com/calendar/r?cid=webcal://aaronsewall.github.io/pycon_us_ics/typing_summit.ics