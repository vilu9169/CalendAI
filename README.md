# CalendAI  
**Work In Progress**  
A personal project exploring the integration of a conversational AI assistant with a calendar system.

---

## Overview
CalendAI is an experimental application that combines a chatbot interface with a calendar and task management system.  
The goal is to create an intelligent assistant that can understand natural language, schedule events, and interact dynamically with your agenda.

---

## Chat View
<img width="1905" height="1023" alt="Screenshot from 2025-10-06 17-40-29" src="https://github.com/user-attachments/assets/914568c7-3bf3-46f9-a3e9-145bd6c3f162" />

### Current Functionality
- Create events directly through chat using natural language.  
- Maintains awareness of:
  - Current date and time  
  - Conversation context  
  - Existing events  
### Known issues:
- Sometimes keeps trying to create the same event
---

## Calendar View
<img width="894" height="599" alt="Screenshot from 2025-10-06 17-42-14" src="https://github.com/user-attachments/assets/048edafd-213e-4bac-8514-973c0c49c982" />

### Current Functionality
- Displays all events created through the chat interface.  
- Provides a clear, date-based view of upcoming events.

### Known Issue
- The calendar does not update in real time.  
  Reopening or refreshing the app is currently required to display new events.

---

## Tasks View (to be renamed)
<img width="894" height="599" alt="Screenshot from 2025-10-06 17-41-12" src="https://github.com/user-attachments/assets/7e7bde7f-cc94-46e9-95c4-a25d7fe48605" />

### Current Functionality
- Lists all current events in a concise format.  
- Serves as a foundation for future task management features.

---

## Planned Improvements
- Real-time synchronization between chat and calendar views.  
-**Fix functionality within chatview so that it can access (in DB) and prvoide ansers to questions about current events**
- **Integration with external calendars (Google Calendar, Outlook, etc.).**
- Improved task management, including renaming and prioritization.  
- UI refinements and a potential dark mode.

---

## Tech Stack (Current / Planned)
- **Frontend:** React, TailwindCSS
- **Backend:** Node.js (Express)
- **Database:** SQLite (for local testing)
- **AI Logic:** OpenAI API

---

## Current Status
CalendAI is in active development.  
Current focus areas include event handling, synchronization between views, and refining the AI’s conversational behavior.

---

## About the Project
CalendAI is both a technical exploration and a personal learning project.  
It experiments with how conversational AI can be used to manage real-world tasks like scheduling, reminders, and event organization.
