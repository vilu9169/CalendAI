import PyQt6.QtCore as qtc
import PyQt6.QtWidgets as qtw
import PyQt6.QtGui as qtg

from DB.sqlite import CalendarDB  # uses your existing class


class CalendarView(qtw.QWidget):
    def __init__(self, palette, user_id=None):
        super().__init__()
        self.second_color = palette[1]
        self.third_color = palette[2]
        self.fourth_color = palette[3]

        self.db = CalendarDB()
        self.user_id = user_id  # pass a user_id to only show their events
        self.events_by_date: dict[str, list[str]] = {}
        self._formatted_dates: list[qtc.QDate] = []

        main_layout = qtw.QVBoxLayout(self)

        label = qtw.QLabel("📅 My Calendar")
        label.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(label)

        self.calendar = qtw.QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {self.third_color};
                color: white;
                border-radius: 10px;
                padding: 10px;
            }}
            QCalendarWidget QTableView {{
                selection-background-color: {self.third_color};
                color: white;
                border-radius: 5px;
            }}
            QWidget#qt_calendar_navigationbar {{
                color: white;
            }}
            QCalendarWidget QHeaderView {{
                background-color: {self.fourth_color};
                color: #FFFFFF;
                padding: 5px;
                border: none;
            }}
            QCalendarWidget QTableView::item {{
                padding: 5px;
                border: 1px solid {self.second_color};
            }}
            QCalendarWidget QTableView::item:selected {{
                background-color: {self.third_color};
                color: white;
            }}
        """)
        main_layout.addWidget(self.calendar)

        events_label = qtw.QLabel("📌 Events for Selected Date:")
        events_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; margin-top: 10px; "
            f"background-color: {self.second_color}; padding: 5px; border-radius: 5px;"
        )
        main_layout.addWidget(events_label)

        self.events_list = qtw.QListWidget()
        self.events_list.setStyleSheet(
            f"background-color: {self.second_color}; padding: 10px; border-radius: 5px;"
        )
        main_layout.addWidget(self.events_list)

        # Signals
        self.calendar.selectionChanged.connect(self.update_events)
        self.calendar.currentPageChanged.connect(lambda _y, _m: self._apply_date_formats())

        # Initial load
        self.refresh_from_db()

    def refresh_from_db(self):
        """Reload events from DB and refresh UI."""
        rows = self._fetch_events()
        self._index_events_by_date(rows)
        self._apply_date_formats()
        self.update_events()

    def _fetch_events(self) -> list[dict]:
        """Get events (for a user if provided; otherwise all events)."""
        try:
            if self.user_id is not None:
                # Uses your existing method
                # returns tuples, so convert to dicts if needed
                rows = self.db.get_events(self.user_id)
                # guess columns order from your schema
                cols = ["id", "user_id", "title", "description", "start_date", "end_date", "start_time", "end_time"]
                if rows and not isinstance(rows[0], dict):
                    rows = [dict(zip(cols, r)) for r in rows]
                return rows

            # If you added get_all_events() (as I suggested earlier), prefer it:
            if hasattr(self.db, "get_all_events"):
                return self.db.get_all_events()

            # Fallback: raw query (avoids changing your DB class)
            import sqlite3
            conn = sqlite3.connect("calendai.db")
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_id, title, description, start_date, end_date, start_time, end_time
                FROM events
                ORDER BY start_date, start_time
            """)
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print("Failed to fetch events:", e)
            return []

    def _index_events_by_date(self, rows: list[dict]):
        """Build a dict: 'YYYY-MM-DD' -> [display strings] and include multi-day spans."""
        self.events_by_date.clear()
        for r in rows:
            title = (r.get("title") or "").strip() or "(Untitled)"
            desc = (r.get("description") or "").strip()
            sd = (r.get("start_date") or "").strip()
            ed = (r.get("end_date") or "").strip()
            st = (r.get("start_time") or "").strip()
            et = (r.get("end_time") or "").strip()

            # Build a nice one-line label
            when = f"{st}–{et}" if st and et else (st or et or "")
            label = f"{title}" + (f"  ({when})" if when else "")
            if desc:
                label += f"\n    📝 {desc}"

            # Parse dates and expand range
            try:
                qd_start = qtc.QDate.fromString(sd, "yyyy-MM-dd")
                qd_end = qtc.QDate.fromString(ed, "yyyy-MM-dd") if ed else qd_start
                if not qd_start.isValid():
                    continue
                if not qd_end.isValid():
                    qd_end = qd_start
            except Exception:
                continue

            days = qd_start.daysTo(qd_end)
            for i in range(max(0, days) + 1):
                d = qd_start.addDays(i)
                key = d.toString("yyyy-MM-dd")
                self.events_by_date.setdefault(key, []).append(label)

    def update_events(self):
        """Refresh list for the currently selected date."""
        selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.events_list.clear()
        items = self.events_by_date.get(selected_date, [])
        if items:
            for text in items:
                self.events_list.addItem(text)
        else:
            self.events_list.addItem("No events for this day.")

    def _apply_date_formats(self):
        """Highlight all dates that have events."""
        # Clear previous formatting
        for d in self._formatted_dates:
            self.calendar.setDateTextFormat(d, qtg.QTextCharFormat())
        self._formatted_dates.clear()

        # Prepare highlight format
        fmt = qtg.QTextCharFormat()
        fmt.setFontWeight(qtg.QFont.Weight.Bold)
        fmt.setForeground(qtg.QBrush(qtg.QColor("#ffffff")))
        fmt.setBackground(qtg.QBrush(qtg.QColor(self.second_color)))

        # Apply to all event dates visible in the month (or all; QCalendarWidget handles off-month cells)
        for key in self.events_by_date.keys():
            qd = qtc.QDate.fromString(key, "yyyy-MM-dd")
            if qd.isValid():
                self.calendar.setDateTextFormat(qd, fmt)
                self._formatted_dates.append(qd)
