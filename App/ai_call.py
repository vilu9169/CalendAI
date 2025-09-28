from openai import OpenAI
import os
import json
from DB.sqlite import CalendarDB
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

from utils.dates import resolve_relative_dates

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


def build_messages(user_history):
    now = datetime.now(ZoneInfo("Europe/Stockholm"))
    sys = {
        "role": "system",
        "content": (
            f"Today is {now:%Y-%m-%d} and the local time is {now:%H:%M} "
            f"(Europe/Stockholm). When users say things like 'today', "
            f"'tomorrow', 'this Monday', interpret dates relative to this."
            " Output dates in ISO format: YYYY-MM-DD and 24h time HH:MM."
        ),
    }
    return [sys] + user_history

def ai_call(message: str):
    if not api_key:
        raise ValueError("API key is not set.")
    client = OpenAI(api_key=api_key)

    messages = build_messages([
        {"role": "system", "content": "You help schedule calendars and tasks. Keep it relevant."},
        {"role": "user", "content": message}  # this is a string from ChatView
    ])

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return completion.choices[0].message.content or ""

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
                "start_date":  {"type": "string"},  # YYYY-MM-DD
                "end_date":    {"type": "string"},  # YYYY-MM-DD
                "start_time":  {"type": "string"},  # HH:MM
                "end_time":    {"type": "string"},  # HH:MM
                "location":    {"type": "string"}   # optional
            },
            "required": ["title", "description", "start_date", "end_date", "start_time", "end_time"],
            "additionalProperties": False
        }
        # <- no "strict": True
    }
}]


def function_call(user_text: str, history_sanitized: list[dict]):
    if not api_key:
        raise ValueError("API key is not set.")
    client = OpenAI(api_key=api_key)

    # history_sanitized must already be only {"role","content"} with non-empty strings
    messages = build_messages(
        [{"role": "system",
          "content": "You help schedule calendars and reminders. Keep responses relevant."}]
        + history_sanitized
        + [{"role": "user", "content": user_text}]
    )

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOLS
    )

    msg = completion.choices[0].message
    ai_text = msg.content or "[no text content]"

    event = None
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        event = json.loads(tool_call.function.arguments)

    return ai_text, event

