"""
====================================================================
 PROJECT NAME : Water Reminder Web App
 FRAMEWORK    : Streamlit (Cloud/Browser Ready)
 SUBJECT      : Data Structures and Algorithms (DSA) - College Assignment

 MAIN DATA STRUCTURES USED
   1. LIST / DYNAMIC ARRAY  -> st.session_state.records
      Stores every water-intake entry (time + amount).
   2. STACK (LIFO)          -> st.session_state.undo_stack
      Used with append() and pop() to undo the last entry.
   3. QUEUE (FIFO)          -> st.session_state.reminder_log (deque)
      Stores notification history up to maxlen entries.

 MAIN ALGORITHMS
   - Linear Search (search_records)
   - Aggregation / Arithmetic metrics (Total, Remaining, Glasses)
====================================================================
"""

import streamlit as st
from datetime import datetime
from collections import deque
import pandas as pd

# ---------------------------------------------------------------
# CONSTANTS & SETUP
# ---------------------------------------------------------------
GLASS_SIZE_ML = 250
REMINDER_LOG_MAXLEN = 15

st.set_page_config(
    page_title="💧 Water Reminder App",
    page_icon="💧",
    layout="wide"
)

# ---------------------------------------------------------------
# STATE INITIALISATION (DSA Structures in Session Memory)
# ---------------------------------------------------------------
if "records" not in st.session_state:
    st.session_state.records = []  # LIST / DYNAMIC ARRAY

if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []  # STACK (LIFO)

if "reminder_log" not in st.session_state:
    st.session_state.reminder_log = deque(maxlen=REMINDER_LOG_MAXLEN)  # QUEUE (FIFO)

if "profile" not in st.session_state:
    st.session_state.profile = {"name": "Guest", "age": 20, "weight": 60, "goal_ml": 2000}

if "last_reminder_time" not in st.session_state:
    st.session_state.last_reminder_time = datetime.now()


# ---------------------------------------------------------------
# CORE ALGORITHMS
# ---------------------------------------------------------------
def calculate_total():
    return sum(r["amount"] for r in st.session_state.records)


def search_records(keyword):
    """Linear Search (O(n)) across records."""
    keyword = keyword.strip().lower()
    if not keyword:
        return list(st.session_state.records)

    results = []
    is_numeric = keyword.isdigit()
    for record in st.session_state.records:
        if is_numeric and str(record["amount"]) == keyword:
            results.append(record)
        elif keyword in record["time"].lower():
            results.append(record)
    return results


def add_water(amount):
    if amount <= 0:
        st.error("Amount must be positive.")
        return
    record = {"time": datetime.now().strftime("%I:%M %p"), "amount": int(amount)}
    st.session_state.records.append(record)      # Dynamic Array append
    st.session_state.undo_stack.append(record)   # Stack push (LIFO)
    st.toast(f"Added {amount} ml successfully!", icon="💧")


def undo_intake():
    """Stack pop (LIFO)."""
    if not st.session_state.undo_stack:
        st.warning("Nothing to undo!")
        return
    last_record = st.session_state.undo_stack.pop()
    if st.session_state.records and st.session_state.records[-1] == last_record:
        st.session_state.records.pop()
    elif last_record in st.session_state.records:
        st.session_state.records.remove(last_record)
    st.toast(f"Removed: {last_record['amount']} ml at {last_record['time']}", icon="↩️")


def trigger_reminder():
    """Enqueue event into FIFO Queue."""
    now_str = datetime.now().strftime("%I:%M:%S %p")
    st.session_state.reminder_log.append(f"💧 Drink water check at {now_str}")


# ---------------------------------------------------------------
# USER INTERFACE
# ---------------------------------------------------------------
st.title("💧 Water Reminder App")
user_name = st.session_state.profile.get("name", "Guest")
goal = st.session_state.profile.get("goal_ml", 2000)
consumed = calculate_total()
remaining = max(0, goal - consumed)
glasses = consumed // GLASS_SIZE_ML
pct = min(100.0, round((consumed / goal) * 100, 1)) if goal > 0 else 0.0

st.caption(f"Welcome, **{user_name}** | Daily Target: **{goal} ml**")

# Top Navigation Tabs
tab_dash, tab_add, tab_history, tab_reminder, tab_settings = st.tabs([
    "🏠 Dashboard", "💧 Add Water", "📊 History & Search", "⏰ Reminder Log", "⚙️ Settings"
])

# 1. DASHBOARD
with tab_dash:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Daily Goal", f"{goal} ml")
    col2.metric("🥤 Consumed", f"{consumed} ml", f"{glasses} glasses")
    col3.metric("📉 Remaining", f"{remaining} ml")
    col4.metric("📈 Progress", f"{pct}%")

    st.progress(pct / 100)
    if pct >= 100:
        st.success("🎉 Goal completed! Great job staying hydrated today.")

    st.divider()
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("↩️ Undo Last Entry", use_container_width=True):
        undo_intake()
        st.rerun()
    if c2.button("🔄 Reset Today", use_container_width=True):
        st.session_state.records.clear()
        st.session_state.undo_stack.clear()
        st.rerun()

# 2. ADD WATER
with tab_add:
    st.subheader("Quick Add Water")
    q1, q2, q3, q4 = st.columns(4)
    if q1.button("+100 ml", use_container_width=True):
        add_water(100)
        st.rerun()
    if q2.button("+200 ml", use_container_width=True):
        add_water(200)
        st.rerun()
    if q3.button("+250 ml (1 Glass)", use_container_width=True):
        add_water(250)
        st.rerun()
    if q4.button("+500 ml", use_container_width=True):
        add_water(500)
        st.rerun()

    st.write("---")
    st.subheader("Custom Amount")
    custom_ml = st.number_input("Enter amount in ml:", min_value=10, max_value=5000, value=250, step=50)
    if st.button("Add Custom Water", type="primary"):
        add_water(custom_ml)
        st.rerun()

# 3. HISTORY (LINEAR SEARCH & DYNAMIC ARRAY)
with tab_history:
    st.subheader("Intake History (Dynamic Array)")
    query = st.text_input("🔍 Search history (by ml or AM/PM):", placeholder="e.g. 250 or PM")
    results = search_records(query)

    if results:
        df = pd.DataFrame(list(reversed(results)))
        df.columns = ["Time", "Amount (ml)"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No records match your search.")

# 4. REMINDER LOG (FIFO QUEUE)
with tab_reminder:
    st.subheader("Reminder Queue (FIFO - Last 15 events)")
    if st.button("🔔 Trigger Manual Reminder", type="primary"):
        trigger_reminder()
        st.rerun()

    if st.session_state.reminder_log:
        for item in reversed(st.session_state.reminder_log):
            st.write(f"- {item}")
    else:
        st.info("No reminder events in the queue yet.")

# 5. SETTINGS
with tab_settings:
    st.subheader("Profile & Target Setup")
    name = st.text_input("Name", value=st.session_state.profile["name"])
    age = st.number_input("Age", min_value=1, max_value=120, value=int(st.session_state.profile["age"]))
    weight = st.number_input("Weight (kg)", min_value=10.0, max_value=250.0, value=float(st.session_state.profile["weight"]))

    suggested = int(weight * 35)
    st.info(f"💡 Recommended Goal: **{suggested} ml** (based on 35 ml/kg rule).")

    goal_input = st.number_input("Daily Water Goal (ml)", min_value=500, max_value=10000, value=int(st.session_state.profile["goal_ml"]))

    if st.button("💾 Save Profile", type="primary"):
        st.session_state.profile = {"name": name, "age": age, "weight": weight, "goal_ml": goal_input}
        st.success("Profile saved!")
        st.rerun()
       
      
