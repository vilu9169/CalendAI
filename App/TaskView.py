import PyQt6.QtCore as qtc
import PyQt6.QtWidgets as qtw
import PyQt6.QtGui as qtg

from DB.sqlite import CalendarDB
from datetime import datetime, date, timedelta


class TaskView(qtw.QWidget):
    """
    A chronological list of events (“tasks”), with search and quick filters.
    - Sorted by start (YYYY-MM-DD HH:MM).
    - Works with or without user_id.
    - Times are optional; missing times sort as 00:00.
    """
    def __init__(self, palette, user_id=None):
        super().__init__()
        self.second_color = palette[1]
        self.third_color  = palette[2]
        self.fourth_color = palette[3]

        self.db = CalendarDB()
        self.user_id = user_id
        self._rows_raw = []     # raw events from DB (list[dict])
        self._rows_view = []    # filtered/sorted rows currently rendered

        # ---------- UI ----------
        main = qtw.QVBoxLayout(self)

        title = qtw.QLabel("✅ Tasks & Events")
        title.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; padding: 8px;")
        main.addWidget(title)

        # Controls row
        controls = qtw.QHBoxLayout()
        self.search = qtw.QLineEdit()
        self.search.setPlaceholderText("Search title, description, location...")
        self.search.textChanged.connect(self._render)

        self.filter = qtw.QComboBox()
        self.filter.addItems(["All", "Upcoming", "Today", "This Week", "Past"])
        self.filter.currentIndexChanged.connect(self._render)

        self.refresh_btn = qtw.QPushButton("↻ Refresh")
        self.refresh_btn.clicked.connect(self.refresh_from_db)

        for w in (self.search, self.filter, self.refresh_btn):
            w.setStyleSheet(f"background-color: {self.second_color}; color: white; padding: 6px; border-radius: 6px;")
        controls.addWidget(self.search, 2)
        controls.addWidget(self.filter, 0)
        controls.addWidget(self.refresh_btn, 0)
        main.addLayout(controls)

        # Table
        self.table = qtw.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["When", "End", "Title", "Time", "Location", "Description"])
        self.table.setEditTriggers(qtw.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(qtw.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)  # we sort manually for full control
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {self.third_color}; color: white; border-radius: 6px; }}"
            f"QHeaderView::section {{ background-color: {self.fourth_color}; padding: 6px; border: none; }}"
            f"QTableWidget::item {{ padding: 6px; }}"
        )
        main.addWidget(self.table)

        # Initial load
        self.refresh_from_db()

    # ---------- Data ----------
    def refresh_from_db(self):
        """Reload events from DB and redraw."""
        self._rows_raw = self._fetch_events()
        self._render()

    def _fetch_events(self) -> list[dict]:
        """
        Get events (for a user if provided; else all).
        Returns unified dict rows.
        """
        try:
            if self.user_id is not None:
                rows = self.db.get_events(self.user_id)  # likely tuples
                cols = ["id", "user_id", "title", "description", "start_date", "end_date", "start_time", "end_time"]
                if rows and not isinstance(rows[0], dict):
                    rows = [dict(zip(cols, r)) for r in rows]
                return rows

            # If you added get_all_events(), prefer it:
            if hasattr(self.db, "get_all_events"):
                return self.db.get_all_events()

            # Fallback direct query without changing DB class
            import sqlite3
            conn = sqlite3.connect("calendai.db")
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_id, title, description, start_date, end_date, start_time, end_time, NULL as location
                FROM events
                ORDER BY start_date, start_time
            """)
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print("TaskView: failed to fetch events:", e)
            return []

    # ---------- Rendering / Filtering ----------
    def _render(self):
        """Apply filters + search, sort chronologically, and fill the table."""
        q = (self.search.text() or "").strip().lower()
        mode = self.filter.currentText()

        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week   = start_of_week + timedelta(days=6)

        def norm_time(t: str | None) -> str:
            t = (t or "").strip()
            return t if t else "00:00"

        def parse_date(d: str | None) -> date | None:
            try:
                return datetime.strptime((d or "").strip(), "%Y-%m-%d").date()
            except Exception:
                return None

        # Filter + normalize
        filtered = []
        for r in self._rows_raw:
            title = (r.get("title") or "").strip()
            desc  = (r.get("description") or "").strip()
            loc   = (r.get("location") or "").strip()

            sd = parse_date(r.get("start_date"))
            ed = parse_date(r.get("end_date")) or sd
            st = norm_time(r.get("start_time"))
            et = norm_time(r.get("end_time"))

            if sd is None:
                continue  # ignore invalid dates

            # Quick filters
            if mode == "Upcoming" and ed < today:
                continue
            if mode == "Past" and sd > today:
                continue
            if mode == "Today" and not (sd <= today <= ed):
                continue
            if mode == "This Week":
                # intersects the week range
                if ed < start_of_week or sd > end_of_week:
                    continue

            # Search
            hay = " ".join([title.lower(), desc.lower(), loc.lower()])
            if q and q not in hay:
                continue

            # Build display + sort key
            start_iso = f"{sd.isoformat()} {st}"
            end_iso   = f"{(ed or sd).isoformat()} {et}"
            when_txt  = sd.strftime("%Y-%m-%d")
            end_txt   = ed.strftime("%Y-%m-%d") if ed and ed != sd else ""

            time_txt  = f"{st}–{et}" if (st or et) and (st != "00:00" or et != "00:00") else ""
            filtered.append({
                "when_sort": start_iso,      # primary sort
                "when": when_txt,
                "end": end_txt,
                "title": title or "(Untitled)",
                "time": time_txt,
                "location": loc,
                "desc": desc
            })

        # Sort by start datetime asc
        filtered.sort(key=lambda r: r["when_sort"])
        self._rows_view = filtered

        # Fill table
        self.table.setRowCount(len(filtered))
        for row, r in enumerate(filtered):
            self._set_row(row, r)

        # Resize nicely
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def _set_row(self, row: int, r: dict):
        def make_item(text: str, bold=False, sort_key: str | None = None):
            it = qtw.QTableWidgetItem(text)
            if bold:
                f = it.font(); f.setBold(True); it.setFont(f)
            if sort_key:
                it.setData(qtc.Qt.ItemDataRole.UserRole, sort_key)
            return it

        self.table.setItem(row, 0, make_item(r["when"], bold=True, sort_key=r["when_sort"]))  # When
        self.table.setItem(row, 1, make_item(r["end"]))                                       # End
        self.table.setItem(row, 2, make_item(r["title"]))                                     # Title
        self.table.setItem(row, 3, make_item(r["time"]))                                      # Time
        self.table.setItem(row, 4, make_item(r["location"]))                                  # Location
        self.table.setItem(row, 5, make_item(r["desc"]))                                      # Description
