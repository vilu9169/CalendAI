# ai_call.py
from openai import OpenAI
import os, json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


def _format_recent_events(events: list[dict]) -> str:
    """
    Turn a short list of events into concise bullet lines for a system note.
    Expected keys: title, start_date, start_time (optional), location (optional).
    """
    lines = []
    for e in (events or [])[:10]:
        title = (e.get("title") or "(Untitled)").strip()
        sd    = (e.get("start_date") or "").strip()
        st    = (e.get("start_time") or "").strip()
        loc   = (e.get("location") or "").strip()
        line = f"- {title} on {sd}" + (f" at {st}" if st else "") + (f" ({loc})" if loc else "")
        lines.append(line)
    return "\n".join(lines)


def build_messages(user_history: list[dict], recent_events: list[dict] | None = None):
    """
    Prepend the current date/time, and (optionally) a short memory of recent events.
    """
    now = datetime.now(ZoneInfo("Europe/Stockholm"))
    sys_date = {
    "role": "system",
    "content": (
        f"Today is {now:%Y-%m-%d} and the local time is {now:%H:%M} (Europe/Stockholm). "
        "Interpret relative dates (today/tomorrow/this Monday/next Friday) relative to this. "
        "Always output dates in ISO YYYY-MM-DD and 24h time HH:MM. "
        "Only create or modify calendar events if the MOST RECENT user message explicitly asks for it. "
        "Do NOT act on older requests in the conversation."
    ),
}

    messages = [sys_date]

    if recent_events:
        messages.append({
        "role": "system",
        "content":
            "Already scheduled (next 30 days):\n"
            + _format_recent_events(recent_events)
            + "\nDo NOT create duplicates. If the latest user message sounds similar to any of these, ask for confirmation."
            })


    return messages + user_history


# ---- tool call ----
TOOLS = [{
    "type": "function",
    "function": {
        "name": "create_calendar_event",
        "description": "Create a structured calendar event based on user input when asked.",
        "parameters": {
            "type": "object",
            "properties": {
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "start_date":  {"type": "string"},
                "end_date":    {"type": "string"},
                "start_time":  {"type": "string"},
                "end_time":    {"type": "string"},
                "location":    {"type": "string"} # optional
            },
            "required": ["title","description","start_date","end_date","start_time","end_time"],
            "additionalProperties": False
        }
    }
}]


# ai_call.py
import re

INTENT_RE = re.compile(
    r"\b(add|schedule|create|set up|book|put|make|log|plan|calendar|event|remind|reminder|"
    r"i (want|need) to|let'?s|please)\b", re.I)

TIME_HINT_RE = re.compile(
    r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"next|this|on \d{1,2}(st|nd|rd|th)?|at \d{1,2}(:\d{2})?\s?(am|pm)?|"
    r"\d{4}-\d{2}-\d{2})\b", re.I)

def _has_schedule_intent(text: str) -> bool:
    t = text.strip().lower()
    return bool(INTENT_RE.search(t) or TIME_HINT_RE.search(t))

def function_call(user_text: str,
                  history_sanitized: list[dict],
                  recent_events: list[dict] | None = None,
                  *,
                  has_pending: bool = False):
    if not api_key:
        raise ValueError("API key is not set.")
    client = OpenAI(api_key=api_key)

    core = [{
        "role": "system",
        "content": (
            "You help schedule calendars and reminders. "
            "Base actions ONLY on the latest user message. "
            "If there is a pending event awaiting user confirmation, do NOT call tools again—ask for confirmation or adjustments. "
            "When the latest user message requests or implies scheduling (natural language like "
            "'I want to ... on Sunday at 14' counts), you MUST call the create_calendar_event tool. "
            "Do not say you'll create an event unless you actually call the tool."
        )
    }]

    messages = build_messages(core + history_sanitized + [{"role": "user", "content": user_text}],
                              recent_events=recent_events)

    # 🎯 Key change: allow tools by default; if intent is clear, REQUIRE the specific tool
    if has_pending:
        tool_choice = "none"
    elif _has_schedule_intent(user_text):
        tool_choice = {"type": "function", "function": {"name": "create_calendar_event"}}  # force
    else:
        tool_choice = "auto"

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOLS,
        tool_choice=tool_choice
    )

    msg = completion.choices[0].message
    ai_text = msg.content or ""

    # Debug (super useful)
    if getattr(msg, "tool_calls", None):
        print("DEBUG tool_calls:", [tc.function.name for tc in msg.tool_calls])
        print("DEBUG tool_args:", msg.tool_calls[0].function.arguments)
    else:
        print("DEBUG no tool call; ai_text:", repr(ai_text))

    event = None
    if msg.tool_calls:
        try:
            tool_call = msg.tool_calls[0]
            event = json.loads(tool_call.function.arguments)
        except Exception as e:
            print("DEBUG: failed to parse tool args:", e)

    return ai_text, event

