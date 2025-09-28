import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}

def _next_weekday(start: datetime, weekday: int, include_today=False) -> datetime:
    days_ahead = (weekday - start.weekday()) % 7
    if days_ahead == 0 and not include_today:
        days_ahead = 7
    return start + timedelta(days=days_ahead)

def resolve_relative_dates(user_text: str, tz: str = "Europe/Stockholm") -> dict | None:
    """
    Returns a dict with start_date/end_date strings if it can confidently resolve,
    else None (caller keeps model’s dates).
    """
    text = user_text.lower()
    now = datetime.now(ZoneInfo(tz))

    # tomorrow
    if re.search(r"\btomorrow\b", text):
        d = now + timedelta(days=1)
        iso = d.strftime("%Y-%m-%d")
        return {"start_date": iso, "end_date": iso}

    # today
    if re.search(r"\btoday\b", text):
        iso = now.strftime("%Y-%m-%d")
        return {"start_date": iso, "end_date": iso}

    # this/next + weekday
    m = re.search(r"\b(this|next)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text)
    if m:
        when, wd = m.groups()
        target = WEEKDAYS[wd]
        if when == "this":
            # if weekday has passed this week, go to next week
            d = _next_weekday(now, target, include_today=True)
            if d.date() < now.date():
                d = d + timedelta(days=7)
        else:  # next
            d = _next_weekday(now, target, include_today=False)
        iso = d.strftime("%Y-%m-%d")
        return {"start_date": iso, "end_date": iso}

    return None
