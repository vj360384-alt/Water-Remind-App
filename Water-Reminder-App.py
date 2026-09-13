"""
====================================================================
 PROJECT NAME : Water Reminder App
 LANGUAGE     : Python 3 (Tkinter - built-in GUI library)
 SUBJECT      : Data Structures and Algorithms (DSA) - College Assignment

 MAIN DATA STRUCTURES USED
   1. LIST / DYNAMIC ARRAY  -> self.records
      Stores every water-intake entry made today (time + amount).
      Chosen because we need ordered, indexable, growable storage
      and we frequently need to iterate over it (for totals,
      history display and searching).

   2. STACK (LIFO)          -> self.undo_stack  (implemented with a
      normal Python list using append()/pop(), both O(1))
      Every time water is added, the same record is pushed onto the
      stack. "Undo Last Intake" simply pops the stack, which is
      exactly the last item added -> classic LIFO behaviour.

   3. QUEUE (FIFO)          -> self.reminder_log (collections.deque)
      Every time a reminder pop-up fires, the event is enqueued
      (append). The oldest reminder is dequeued automatically because
      the deque has a fixed maxlen (FIFO: First In First Out), which
      keeps only the most recent N reminders - a natural queue use
      case for an event/notification log.

 MAIN ALGORITHMS
   - Linear Search        -> search_records() filters intake records
                              by amount or by time text.
   - Aggregation/Calculus  -> total consumed, remaining water, glasses
                              count, percentage progress.
   - Event Scheduling      -> Tkinter's after() is used as a
                              non-blocking timer/scheduler that drives
                              the reminder countdown without freezing
                              the GUI (no threads needed).

 DESCRIPTION
   A desktop GUI application that helps a user track daily water
   intake, reminds them at custom intervals to drink water, keeps a
   searchable history of intake records for the day, supports undoing
   the last entry, and persists all data locally using a JSON file so
   progress is not lost when the app is closed and reopened. The app
   also auto-detects a new calendar day and resets the daily counters
   while keeping the user's profile and goal untouched.
====================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from collections import deque

# ---------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "water_reminder_data.json")
GLASS_SIZE_ML = 250          # used to calculate "number of glasses consumed"
REMINDER_LOG_MAXLEN = 15     # queue capacity for the reminder log

# ---------------------------------------------------------------
# COLOUR PALETTE  (blue / cyan water theme)
# ---------------------------------------------------------------
BG_MAIN     = "#EAF6FB"
BG_CARD     = "#FFFFFF"
BLUE_DARK   = "#0B5A86"
BLUE_MED    = "#1E88C7"
BLUE_LIGHT  = "#63B8E5"
CYAN_ACCENT = "#00B4D8"
GREEN_OK    = "#27AE60"
ORANGE_WARN = "#F39C12"
RED_STOP    = "#E74C3C"
GREY_BTN    = "#8FA6B2"
TEXT_DARK   = "#0B3954"
TEXT_MUTED  = "#5B7A8A"

FONT_TITLE   = ("Segoe UI", 22, "bold")
FONT_H2      = ("Segoe UI", 15, "bold")
FONT_H3      = ("Segoe UI", 12, "bold")
FONT_BODY    = ("Segoe UI", 11)
FONT_BIG_NUM = ("Segoe UI", 30, "bold")
FONT_BTN     = ("Segoe UI", 11, "bold")


def make_rounded_button(parent, text, command, bg, fg="white", font=FONT_BTN,
                         width=14, pady=10, padx=6):
    """
    Small helper that returns a flat, borderless tk.Button styled to
    look like a modern "rounded" pill button (Tkinter has no native
    rounded corners, so we simulate the flat/modern look with
    padding, flat relief and a matching hover colour).
    """
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                     font=font, relief="flat", bd=0, cursor="hand2",
                     activebackground=BLUE_DARK, activeforeground="white",
                     padx=padx, pady=pady, width=width)

    def on_enter(e):
        btn["bg"] = BLUE_DARK

    def on_leave(e):
        btn["bg"] = bg

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


class WaterReminderApp:
    """Main application class - holds all data structures, GUI widgets
    and logic for the Water Reminder App."""

    # ------------------------------------------------------------
    # INITIALISATION
    # ------------------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.root.title("💧 Water Reminder App")
        self.root.geometry("880x640")
        self.root.minsize(820, 600)
        self.root.configure(bg=BG_MAIN)

        # ---------------- CORE DATA STRUCTURES ------------------
        self.records = []            # LIST / DYNAMIC ARRAY of {"time":.., "amount":..}
        self.undo_stack = []         # STACK (LIFO) mirrors last-added records
        self.reminder_log = deque(maxlen=REMINDER_LOG_MAXLEN)  # QUEUE (FIFO)

        # ---------------- PROFILE / STATE ------------------------
        self.profile = {"name": "", "age": "", "weight": "", "goal_ml": 2000}
        self.consumed_ml = 0
        self.today_str = datetime.now().strftime("%Y-%m-%d")

        # ---------------- REMINDER TIMER STATE --------------------
        self.reminder_interval_min = 60
        self.reminder_running = False
        self.remaining_seconds = self.reminder_interval_min * 60
        self.after_job = None        # holds id returned by root.after() so we can cancel it

        self.load_data()             # load JSON if it exists (also checks new-day reset)

        self.build_gui()
        self.refresh_all_views()

    # ==============================================================
    # DATA PERSISTENCE (JSON file)
    # ==============================================================
    def load_data(self):
        """Load saved profile/records/consumed data from a local JSON
        file (if present). Also triggers the new-day reset check."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                self.profile = data.get("profile", self.profile)
                self.consumed_ml = data.get("consumed_ml", 0)
                self.records = data.get("records", [])
                self.today_str = data.get("date", self.today_str)
                self.reminder_interval_min = data.get("reminder_interval_min", 60)
                self.remaining_seconds = self.reminder_interval_min * 60

                # rebuild the undo stack so it mirrors the loaded records
                self.undo_stack = list(self.records)
            except (json.JSONDecodeError, OSError):
                messagebox.showwarning("Data Load Warning",
                                        "Saved data file was unreadable. Starting fresh.")
        # After loading, verify whether a new calendar day has started
        self.check_new_day(silent=True)

    def save_data(self):
        """Persist current state to the local JSON file."""
        data = {
            "profile": self.profile,
            "consumed_ml": self.consumed_ml,
            "records": self.records,
            "date": self.today_str,
            "reminder_interval_min": self.reminder_interval_min,
        }
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except OSError:
            messagebox.showerror("Save Error", "Could not save data to disk.")

    def check_new_day(self, silent=False):
        """If the stored date differs from today, reset the DAILY
        counters (consumed water, records, undo stack, reminder log)
        while KEEPING the user's profile and goal untouched."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date != self.today_str:
            self.today_str = current_date
            self.consumed_ml = 0
            self.records = []
            self.undo_stack = []
            self.reminder_log.clear()
            self.save_data()
            if not silent:
                messagebox.showinfo("New Day", "A new day has started! Your daily "
                                                "water count has been reset. 🌅")

    # ==============================================================
    # CORE DSA / CALCULATION LOGIC
    # ==============================================================
    def calculate_total_consumed(self):
        """Aggregation algorithm: sums the 'amount' field over the
        records LIST. (Kept in sync incrementally too, this function
        can always be used to recompute/verify the total.)"""
        return sum(r["amount"] for r in self.records)

    def calculate_remaining(self):
        goal = self.profile.get("goal_ml", 2000)
        remaining = goal - self.consumed_ml
        return max(0, remaining)

    def calculate_progress_percentage(self):
        goal = self.profile.get("goal_ml", 2000)
        if goal <= 0:
            return 0
        pct = (self.consumed_ml / goal) * 100
        return min(100, round(pct, 1))

    def calculate_glasses(self):
        return self.consumed_ml // GLASS_SIZE_ML

    def search_records(self, keyword):
        """LINEAR SEARCH ALGORITHM
        Scans the records list from start to end (O(n)) and returns
        every record whose amount matches the keyword exactly (if it
        is numeric) OR whose time string contains the keyword as a
        substring (case-insensitive). This demonstrates a simple
        linear search over a dynamic array."""
        keyword = keyword.strip().lower()
        if keyword == "":
            return list(self.records)

        results = []
        is_numeric = keyword.isdigit()
        for record in self.records:                 # <-- linear scan
            if is_numeric and str(record["amount"]) == keyword:
                results.append(record)
            elif keyword in record["time"].lower():
                results.append(record)
        return results

    # ==============================================================
    # WATER INTAKE ACTIONS
    # ==============================================================
    def add_water(self, amount):
        """Add a water intake record. Pushes onto the LIST and the
        STACK simultaneously so that Undo (stack.pop()) always removes
        exactly the most-recently-added element from both structures."""
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            messagebox.showerror("Invalid Input", "Please enter a valid whole number.")
            return

        if amount <= 0:
            messagebox.showerror("Invalid Amount", "Water amount must be a positive number.")
            return
        if amount > 5000:
            messagebox.showerror("Invalid Amount", "That seems too large for a single entry (max 5000 ml).")
            return

        self.check_new_day()

        record = {"time": datetime.now().strftime("%I:%M %p"), "amount": amount}
        self.records.append(record)          # LIST push (dynamic array)
        self.undo_stack.append(record)       # STACK push (LIFO)
        self.consumed_ml += amount

        self.save_data()
        self.refresh_all_views()
        self.custom_amount_var.set("")

    def undo_last_intake(self):
        """STACK POP (LIFO) - removes the most recently added intake."""
        if not self.undo_stack:
            messagebox.showinfo("Nothing to Undo", "There is no water intake to undo today.")
            return

        last_record = self.undo_stack.pop()     # STACK pop -> last added item
        # Because records and undo_stack always grow together, the
        # last element of records IS this same record.
        if self.records and self.records[-1] == last_record:
            self.records.pop()
        else:
            # safety fallback (should not normally trigger)
            if last_record in self.records:
                self.records.remove(last_record)

        self.consumed_ml = max(0, self.consumed_ml - last_record["amount"])
        self.save_data()
        self.refresh_all_views()
        messagebox.showinfo("Undo Successful",
                             f"Removed last entry: {last_record['amount']} ml at {last_record['time']}")

    def reset_today(self, ask_confirm=True):
        """Manually reset today's consumption/history while keeping
        the user's profile & goal intact."""
        if ask_confirm:
            if not messagebox.askyesno("Confirm Reset",
                                        "Reset today's water intake and history?\n"
                                        "Your profile and goal will NOT be affected."):
                return
        self.consumed_ml = 0
        self.records = []
        self.undo_stack = []
        self.save_data()
        self.refresh_all_views()

    # ==============================================================
    # REMINDER SYSTEM  (non-blocking, uses Tkinter's after())
    # ==============================================================
    def set_reminder_interval(self, minutes):
        try:
            minutes = int(minutes)
            if minutes <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Interval", "Interval must be a positive whole number of minutes.")
            return
        self.reminder_interval_min = minutes
        self.remaining_seconds = minutes * 60
        self.save_data()
        self.update_reminder_labels()
        messagebox.showinfo("Reminder Interval Set", f"Reminder interval set to {minutes} minute(s).")

    def start_reminder(self):
        if self.reminder_running:
            return
        self.reminder_running = True
        self.status_label.config(text="Status: Running ▶", fg=GREEN_OK)
        self.tick()   # kicks off the recurring after() loop

    def pause_reminder(self):
        self.reminder_running = False
        if self.after_job is not None:
            self.root.after_cancel(self.after_job)
            self.after_job = None
        self.status_label.config(text="Status: Paused ⏸", fg=ORANGE_WARN)

    def reset_reminder(self):
        self.pause_reminder()
        self.remaining_seconds = self.reminder_interval_min * 60
        self.status_label.config(text="Status: Reset ⏹", fg=TEXT_MUTED)
        self.update_reminder_labels()

    def tick(self):
        """Runs once per second via root.after(1000, ...) - this is
        the NON-BLOCKING scheduling mechanism (an event-driven
        algorithm) that keeps the GUI responsive instead of using
        time.sleep() or a background thread."""
        if not self.reminder_running:
            return

        if self.remaining_seconds <= 0:
            self.trigger_reminder()
            self.remaining_seconds = self.reminder_interval_min * 60
        else:
            self.remaining_seconds -= 1

        self.update_reminder_labels()
        self.after_job = self.root.after(1000, self.tick)   # schedule next tick

    def trigger_reminder(self):
        """Fires the actual reminder pop-up and enqueues it into the
        reminder_log QUEUE (deque). Oldest entries drop off
        automatically once maxlen is exceeded -> FIFO behaviour."""
        now_str = datetime.now().strftime("%I:%M:%S %p")
        self.reminder_log.append(f"💧 Reminder shown at {now_str}")   # ENQUEUE
        self.update_reminder_log_view()
        messagebox.showinfo("Water Reminder", "💧 Time to drink water!")

    def update_reminder_labels(self):
        mins, secs = divmod(max(0, self.remaining_seconds), 60)
        self.countdown_label.config(text=f"⏳ Next reminder in: {mins:02d}:{secs:02d}")
        self.interval_display_label.config(text=f"Current interval: {self.reminder_interval_min} min")
        self.dash_next_reminder_label.config(text=f"Next reminder in {mins:02d}:{secs:02d}")

    # ==============================================================
    # GUI CONSTRUCTION
    # ==============================================================
    def build_gui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"),
                         padding=[16, 10], background=BLUE_LIGHT, foreground="white")
        style.map("TNotebook.Tab",
                  background=[("selected", BLUE_DARK)],
                  foreground=[("selected", "white")])
        style.configure("Water.Horizontal.TProgressbar", troughcolor="#D7ECF6",
                         background=CYAN_ACCENT, thickness=26, bordercolor=BG_MAIN,
                         lightcolor=CYAN_ACCENT, darkcolor=CYAN_ACCENT)

        # ---- Header ----
        header = tk.Frame(self.root, bg=BLUE_DARK, height=70)
        header.pack(fill="x", side="top")
        tk.Label(header, text="💧  Water Reminder App", font=FONT_TITLE,
                  bg=BLUE_DARK, fg="white").pack(side="left", padx=20, pady=12)

        # ---- Notebook (tabs) ----
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_dashboard = tk.Frame(self.notebook, bg=BG_MAIN)
        self.tab_addwater  = tk.Frame(self.notebook, bg=BG_MAIN)
        self.tab_reminder  = tk.Frame(self.notebook, bg=BG_MAIN)
        self.tab_history   = tk.Frame(self.notebook, bg=BG_MAIN)
        self.tab_settings  = tk.Frame(self.notebook, bg=BG_MAIN)

        self.notebook.add(self.tab_dashboard, text="🏠 Dashboard")
        self.notebook.add(self.tab_addwater,  text="💧 Add Water")
        self.notebook.add(self.tab_reminder,  text="⏰ Reminder")
        self.notebook.add(self.tab_history,   text="📊 History")
        self.notebook.add(self.tab_settings,  text="⚙️ Settings")

        self.build_dashboard_tab()
        self.build_addwater_tab()
        self.build_reminder_tab()
        self.build_history_tab()
        self.build_settings_tab()

    # ---------------------------- CARD HELPER ----------------------
    def make_card(self, parent, title, value_text, subtitle="", accent=BLUE_MED):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=accent,
                         highlightthickness=2, bd=0)
        tk.Label(card, text=title, font=FONT_H3, bg=BG_CARD, fg=TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(12, 0))
        value_label = tk.Label(card, text=value_text, font=FONT_BIG_NUM, bg=BG_CARD, fg=accent)
        value_label.pack(anchor="w", padx=16, pady=(0, 4))
        sub_label = tk.Label(card, text=subtitle, font=FONT_BODY, bg=BG_CARD, fg=TEXT_MUTED)
        sub_label.pack(anchor="w", padx=16, pady=(0, 12))
        return card, value_label, sub_label

    # ---------------------------- DASHBOARD TAB ---------------------
    def build_dashboard_tab(self):
        t = self.tab_dashboard
        tk.Label(t, text="Welcome back!", font=FONT_H2, bg=BG_MAIN, fg=TEXT_DARK).pack(
            anchor="w", padx=20, pady=(15, 0))
        self.dash_name_label = tk.Label(t, text="", font=FONT_BODY, bg=BG_MAIN, fg=TEXT_MUTED)
        self.dash_name_label.pack(anchor="w", padx=20, pady=(0, 10))

        cards_frame = tk.Frame(t, bg=BG_MAIN)
        cards_frame.pack(fill="x", padx=20)
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)

        self.card_goal, self.lbl_goal_val, _ = self.make_card(
            cards_frame, "🎯 Daily Goal", "0 ml", "Your target for today", BLUE_DARK)
        self.card_consumed, self.lbl_consumed_val, self.lbl_glasses_sub = self.make_card(
            cards_frame, "🥤 Consumed", "0 ml", "0 glasses", GREEN_OK)
        self.card_remaining, self.lbl_remaining_val, _ = self.make_card(
            cards_frame, "📉 Remaining", "0 ml", "To reach your goal", ORANGE_WARN)
        self.card_reminder, self.lbl_reminder_val, _ = self.make_card(
            cards_frame, "⏰ Reminder", "Stopped", "Next reminder in --:--", CYAN_ACCENT)

        self.card_goal.grid(row=0, column=0, padx=8, pady=10, sticky="nsew")
        self.card_consumed.grid(row=0, column=1, padx=8, pady=10, sticky="nsew")
        self.card_remaining.grid(row=0, column=2, padx=8, pady=10, sticky="nsew")
        self.card_reminder.grid(row=0, column=3, padx=8, pady=10, sticky="nsew")
        self.dash_next_reminder_label = self.card_reminder.winfo_children()[2]

        # ---- Progress section ----
        progress_frame = tk.Frame(t, bg=BG_CARD, highlightbackground=BLUE_LIGHT, highlightthickness=2)
        progress_frame.pack(fill="x", padx=20, pady=15)
        tk.Label(progress_frame, text="📊 Today's Progress", font=FONT_H2, bg=BG_CARD,
                  fg=TEXT_DARK).pack(anchor="w", padx=16, pady=(14, 4))

        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal",
                                             style="Water.Horizontal.TProgressbar",
                                             length=100, mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x", padx=16, pady=10)

        self.progress_pct_label = tk.Label(progress_frame, text="0% of daily goal completed",
                                            font=FONT_H3, bg=BG_CARD, fg=BLUE_DARK)
        self.progress_pct_label.pack(anchor="w", padx=16, pady=(0, 16))

        # ---- Quick action buttons ----
        quick_frame = tk.Frame(t, bg=BG_MAIN)
        quick_frame.pack(fill="x", padx=20, pady=(0, 10))
        make_rounded_button(quick_frame, "🔄 Reset Today", self.reset_today,
                             RED_STOP, width=16).pack(side="left", padx=6)
        make_rounded_button(quick_frame, "↩️ Undo Last Intake", self.undo_last_intake,
                             GREY_BTN, width=18).pack(side="left", padx=6)
        make_rounded_button(quick_frame, "➡️ Go Add Water", lambda: self.notebook.select(self.tab_addwater),
                             BLUE_MED, width=16).pack(side="left", padx=6)

    # ---------------------------- ADD WATER TAB ----------------------
    def build_addwater_tab(self):
        t = self.tab_addwater
        tk.Label(t, text="💧 Add Water Intake", font=FONT_H2, bg=BG_MAIN, fg=TEXT_DARK).pack(
            anchor="w", padx=20, pady=(15, 10))

        btn_frame = tk.Frame(t, bg=BG_MAIN)
        btn_frame.pack(padx=20, pady=10, anchor="w")

        amounts = [100, 200, 250, 500]
        colors = [BLUE_LIGHT, BLUE_MED, CYAN_ACCENT, BLUE_DARK]
        for i, (amt, color) in enumerate(zip(amounts, colors)):
            make_rounded_button(btn_frame, f"+{amt} ml", lambda a=amt: self.add_water(a),
                                 color, width=12).grid(row=0, column=i, padx=8, pady=8)

        # ---- Custom amount ----
        custom_frame = tk.Frame(t, bg=BG_CARD, highlightbackground=BLUE_LIGHT, highlightthickness=2)
        custom_frame.pack(fill="x", padx=20, pady=20)
        tk.Label(custom_frame, text="✏️ Custom Amount (ml)", font=FONT_H3, bg=BG_CARD,
                  fg=TEXT_DARK).pack(anchor="w", padx=16, pady=(14, 6))

        entry_row = tk.Frame(custom_frame, bg=BG_CARD)
        entry_row.pack(anchor="w", padx=16, pady=(0, 16))
        self.custom_amount_var = tk.StringVar()
        entry = tk.Entry(entry_row, textvariable=self.custom_amount_var, font=FONT_BODY,
                          width=12, relief="solid", bd=1)
        entry.pack(side="left", padx=(0, 10), ipady=4)
        make_rounded_button(entry_row, "Add Custom", lambda: self.add_water(self.custom_amount_var.get()),
                             GREEN_OK, width=14).pack(side="left")

        # ---- Undo ----
        make_rounded_button(t, "↩️ Undo Last Intake", self.undo_last_intake,
                             RED_STOP, width=18).pack(anchor="w", padx=20, pady=(0, 10))

        # ---- Today snapshot ----
        self.addwater_snapshot_label = tk.Label(t, text="", font=FONT_BODY, bg=BG_MAIN, fg=TEXT_MUTED,
                                                  justify="left")
        self.addwater_snapshot_label.pack(anchor="w", padx=20, pady=10)

    # ---------------------------- REMINDER TAB ----------------------
    def build_reminder_tab(self):
        t = self.tab_reminder
        tk.Label(t, text="⏰ Water Reminder Settings", font=FONT_H2, bg=BG_MAIN,
                  fg=TEXT_DARK).pack(anchor="w", padx=20, pady=(15, 10))

        interval_frame = tk.Frame(t, bg=BG_MAIN)
        interval_frame.pack(anchor="w", padx=20, pady=5)
        tk.Label(interval_frame, text="Choose interval:", font=FONT_BODY, bg=BG_MAIN,
                  fg=TEXT_DARK).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 6))

        intervals = [30, 45, 60, 90]
        for i, mins in enumerate(intervals):
            make_rounded_button(interval_frame, f"{mins} min", lambda m=mins: self.set_reminder_interval(m),
                                 BLUE_MED, width=10).grid(row=1, column=i, padx=6, pady=6)

        self.custom_interval_var = tk.StringVar()
        custom_entry = tk.Entry(interval_frame, textvariable=self.custom_interval_var, font=FONT_BODY,
                                 width=8, relief="solid", bd=1)
        custom_entry.grid(row=1, column=4, padx=(12, 4))
        make_rounded_button(interval_frame, "Set Custom (min)",
                             lambda: self.set_reminder_interval(self.custom_interval_var.get()),
                             CYAN_ACCENT, width=16).grid(row=1, column=5, padx=6)

        self.interval_display_label = tk.Label(t, text="Current interval: 60 min", font=FONT_H3,
                                                 bg=BG_MAIN, fg=TEXT_DARK)
        self.interval_display_label.pack(anchor="w", padx=20, pady=(14, 4))

        self.countdown_label = tk.Label(t, text="⏳ Next reminder in: 60:00", font=FONT_BIG_NUM,
                                          bg=BG_MAIN, fg=BLUE_DARK)
        self.countdown_label.pack(anchor="w", padx=20, pady=(4, 4))

        self.status_label = tk.Label(t, text="Status: Stopped ⏹", font=FONT_H3, bg=BG_MAIN, fg=TEXT_MUTED)
        self.status_label.pack(anchor="w", padx=20, pady=(0, 14))

        control_frame = tk.Frame(t, bg=BG_MAIN)
        control_frame.pack(anchor="w", padx=20, pady=6)
        make_rounded_button(control_frame, "▶ Start Reminder", self.start_reminder,
                             GREEN_OK, width=16).grid(row=0, column=0, padx=6)
        make_rounded_button(control_frame, "⏸ Pause Reminder", self.pause_reminder,
                             ORANGE_WARN, width=16).grid(row=0, column=1, padx=6)
        make_rounded_button(control_frame, "⏹ Reset Reminder", self.reset_reminder,
                             RED_STOP, width=16).grid(row=0, column=2, padx=6)

        # ---- Reminder log (queue view) ----
        tk.Label(t, text="🔔 Recent Reminder Log (FIFO Queue)", font=FONT_H3, bg=BG_MAIN,
                  fg=TEXT_DARK).pack(anchor="w", padx=20, pady=(18, 4))
        log_frame = tk.Frame(t, bg=BG_CARD, highlightbackground=BLUE_LIGHT, highlightthickness=2)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.reminder_log_listbox = tk.Listbox(log_frame, font=FONT_BODY, bg=BG_CARD, fg=TEXT_DARK,
                                                 relief="flat", bd=0, highlightthickness=0)
        self.reminder_log_listbox.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------------------- HISTORY TAB ----------------------
    def build_history_tab(self):
        t = self.tab_history
        tk.Label(t, text="📊 Today's Drinking History", font=FONT_H2, bg=BG_MAIN,
                  fg=TEXT_DARK).pack(anchor="w", padx=20, pady=(15, 10))

        search_frame = tk.Frame(t, bg=BG_MAIN)
        search_frame.pack(fill="x", padx=20, pady=5)
        tk.Label(search_frame, text="🔍 Search (by amount e.g. 250, or time text e.g. 'AM'):",
                  font=FONT_BODY, bg=BG_MAIN, fg=TEXT_DARK).pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=FONT_BODY,
                                 width=18, relief="solid", bd=1)
        search_entry.pack(side="left", padx=8, ipady=3)
        make_rounded_button(search_frame, "Search", self.perform_search,
                             BLUE_MED, width=10, pady=4).pack(side="left", padx=4)
        make_rounded_button(search_frame, "Clear", self.clear_search,
                             GREY_BTN, width=10, pady=4).pack(side="left", padx=4)

        table_frame = tk.Frame(t, bg=BG_CARD, highlightbackground=BLUE_LIGHT, highlightthickness=2)
        table_frame.pack(fill="both", expand=True, padx=20, pady=15)

        columns = ("time", "amount")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.history_tree.heading("time", text="Time")
        self.history_tree.heading("amount", text="Amount (ml)")
        self.history_tree.column("time", anchor="center", width=200)
        self.history_tree.column("amount", anchor="center", width=200)
        self.history_tree.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.configure("Treeview", font=FONT_BODY, rowheight=28, background=BG_CARD,
                         fieldbackground=BG_CARD, foreground=TEXT_DARK)
        style.configure("Treeview.Heading", font=FONT_H3, background=BLUE_MED, foreground="white")

    def perform_search(self):
        keyword = self.search_var.get()
        results = self.search_records(keyword)
        self.populate_history_tree(results)

    def clear_search(self):
        self.search_var.set("")
        self.populate_history_tree(self.records)

    def populate_history_tree(self, records_list):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        # show most recent entry first
        for record in reversed(records_list):
            self.history_tree.insert("", "end", values=(record["time"], record["amount"]))

    # ---------------------------- SETTINGS TAB ----------------------
    def build_settings_tab(self):
        t = self.tab_settings
        tk.Label(t, text="⚙️ User Profile & Settings", font=FONT_H2, bg=BG_MAIN,
                  fg=TEXT_DARK).pack(anchor="w", padx=20, pady=(15, 10))

        form = tk.Frame(t, bg=BG_CARD, highlightbackground=BLUE_LIGHT, highlightthickness=2)
        form.pack(fill="x", padx=20, pady=10)

        self.name_var = tk.StringVar(value=self.profile.get("name", ""))
        self.age_var = tk.StringVar(value=str(self.profile.get("age", "")))
        self.weight_var = tk.StringVar(value=str(self.profile.get("weight", "")))
        self.goal_var = tk.StringVar(value=str(self.profile.get("goal_ml", 2000)))

        fields = [
            ("Name:", self.name_var),
            ("Age:", self.age_var),
            ("Weight (kg):", self.weight_var),
            ("Daily Water Goal (ml):", self.goal_var),
        ]
        for i, (label_text, var) in enumerate(fields):
            tk.Label(form, text=label_text, font=FONT_BODY, bg=BG_CARD, fg=TEXT_DARK).grid(
                row=i, column=0, sticky="w", padx=16, pady=10)
            tk.Entry(form, textvariable=var, font=FONT_BODY, width=25, relief="solid",
                      bd=1).grid(row=i, column=1, sticky="w", padx=10, pady=10, ipady=3)

        make_rounded_button(t, "💾 Save Profile", self.save_profile, GREEN_OK,
                             width=18).pack(anchor="w", padx=20, pady=15)

        # ---- Suggested goal calculator (bonus algorithm) ----
        calc_frame = tk.Frame(t, bg=BG_CARD, highlightbackground=CYAN_ACCENT, highlightthickness=2)
        calc_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(calc_frame, text="💡 Suggested Goal Calculator", font=FONT_H3, bg=BG_CARD,
                  fg=TEXT_DARK).pack(anchor="w", padx=16, pady=(12, 4))
        tk.Label(calc_frame,
                  text="A common rule of thumb: 35 ml of water per kg of body weight.",
                  font=FONT_BODY, bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=16)
        make_rounded_button(calc_frame, "Calculate From Weight", self.suggest_goal_from_weight,
                             CYAN_ACCENT, width=20).pack(anchor="w", padx=16, pady=12)

    def suggest_goal_from_weight(self):
        try:
            weight = float(self.weight_var.get())
            if weight <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Weight", "Please enter a valid positive weight first.")
            return
        suggested = int(weight * 35)     # simple calculation algorithm
        self.goal_var.set(str(suggested))
        messagebox.showinfo("Suggested Goal", f"Based on {weight} kg, a suggested daily goal is "
                                               f"{suggested} ml. You can adjust it before saving.")

    def save_profile(self):
        name = self.name_var.get().strip()
        age_raw = self.age_var.get().strip()
        weight_raw = self.weight_var.get().strip()
        goal_raw = self.goal_var.get().strip()

        if name == "":
            messagebox.showerror("Invalid Input", "Please enter your name.")
            return
        try:
            age = int(age_raw)
            if age <= 0 or age > 120:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid age (1-120).")
            return
        try:
            weight = float(weight_raw)
            if weight <= 0 or weight > 400:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid weight in kg.")
            return
        try:
            goal_ml = int(goal_raw)
            if goal_ml <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid daily goal in ml.")
            return

        self.profile = {"name": name, "age": age, "weight": weight, "goal_ml": goal_ml}
        self.save_data()
        self.refresh_all_views()
        messagebox.showinfo("Profile Saved", "Your profile has been saved successfully! ✅")

    # ==============================================================
    # VIEW REFRESH
    # ==============================================================
    def update_reminder_log_view(self):
        self.reminder_log_listbox.delete(0, tk.END)
        # deque is FIFO; show most recent at top for readability
        for entry in reversed(self.reminder_log):
            self.reminder_log_listbox.insert(tk.END, entry)

    def update_dashboard(self):
        name = self.profile.get("name") or "Guest"
        goal = self.profile.get("goal_ml", 2000)
        consumed = self.consumed_ml
        remaining = self.calculate_remaining()
        glasses = self.calculate_glasses()
        pct = self.calculate_progress_percentage()

        self.dash_name_label.config(text=f"👤 {name}  |  🎯 Goal: {goal} ml")
        self.lbl_goal_val.config(text=f"{goal} ml")
        self.lbl_consumed_val.config(text=f"{consumed} ml")
        self.lbl_glasses_sub.config(text=f"{glasses} glass(es) (250ml each)")
        self.lbl_remaining_val.config(text=f"{remaining} ml")

        self.progress_bar["value"] = pct
        # colour feedback based on progress
        style = ttk.Style()
        if pct >= 100:
            style.configure("Water.Horizontal.TProgressbar", background=GREEN_OK)
        elif pct >= 50:
            style.configure("Water.Horizontal.TProgressbar", background=CYAN_ACCENT)
        else:
            style.configure("Water.Horizontal.TProgressbar", background=ORANGE_WARN)
        self.progress_pct_label.config(text=f"{pct}% of daily goal completed")

        self.lbl_reminder_val.config(text="Running" if self.reminder_running else "Stopped")

        self.addwater_snapshot_label.config(
            text=f"Consumed so far: {consumed} ml  |  Remaining: {remaining} ml  |  "
                 f"Glasses: {glasses}  |  Progress: {pct}%")

    def refresh_all_views(self):
        self.update_dashboard()
        self.update_reminder_labels()
        self.update_reminder_log_view()
        self.populate_history_tree(self.records)

    # ==============================================================
    # CLEAN SHUTDOWN
    # ==============================================================
    def on_close(self):
        if self.after_job is not None:
            self.root.after_cancel(self.after_job)
        self.save_data()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WaterReminderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
