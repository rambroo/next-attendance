"""
Creates the Kiosk Attendance Dashboard with Number Cards and Charts.
Run via: bench --site yoursite.local execute next_attendance.dashboard.create_dashboard
Safe to run multiple times — updates existing records.
"""
import frappe
import json


NUMBER_CARDS = [
    {
        "name":          "Kiosk Present Today",
        "label":         "Present Today",
        "document_type": "Person Attendance",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  "[]",
        "type":          "Custom",
        "method":        "next_attendance.dashboard.get_present_today",
        "color":         "#3CC88F",
    },
    {
        "name":          "Kiosk Absent Today",
        "label":         "Absent Today",
        "document_type": "Person",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  "[]",
        "type":          "Custom",
        "method":        "next_attendance.dashboard.get_absent_today",
        "color":         "#E53935",
    },
    {
        "name":          "Kiosk Checked In Only",
        "label":         "Checked In (No OUT)",
        "document_type": "Person Attendance",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  "[]",
        "type":          "Custom",
        "method":        "next_attendance.dashboard.get_partial_today",
        "color":         "#F59E0B",
    },
    {
        "name":          "Kiosk Total Persons",
        "label":         "Total Registered",
        "document_type": "Person",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  '[["status","=","Active"]]',
        "color":         "#1A6B47",
    },
]

CHARTS = [
    {
        "name":           "Kiosk Monthly Attendance Trend",
        "chart_name":     "Monthly Attendance Trend",
        "chart_type":     "Count",
        "document_type":  "Person Attendance",
        "based_on":       "attendance_date",
        "filters_json":   '[["log_type","=","IN"]]',
        "type":           "Bar",
        "color":          "#3CC88F",
        "time_interval":  "Daily",
        "timespan":       "Last Month",
    },
    {
        "name":          "Kiosk Group Attendance Today",
        "chart_name":    "Group Attendance Today",
        "chart_type":    "Custom",
        "document_type": "Person Attendance",
        "based_on":      "attendance_date",
        "filters_json":  "[]",
        "type":          "Bar",
        "color":         "#1A6B47",
        "method":        "next_attendance.dashboard.get_group_attendance_today",
        "time_interval": "Daily",
        "timespan":      "Last Month",
    },
]


# ── Custom metric methods (called by number cards) ────────────────────────────

@frappe.whitelist()
def get_present_today():
    today = frappe.utils.today()
    punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": today},
        fields=["person", "log_type"],
    )
    by_person = {}
    for p in punches:
        by_person.setdefault(p.person, set()).add(p.log_type)
    return sum(1 for t in by_person.values() if "IN" in t and "OUT" in t)


@frappe.whitelist()
def get_absent_today():
    total   = frappe.db.count("Person", {"status": "Active"})
    present = get_present_today()
    partial = get_partial_today()
    return max(0, total - present - partial)


@frappe.whitelist()
def get_partial_today():
    today = frappe.utils.today()
    punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": today},
        fields=["person", "log_type"],
    )
    by_person = {}
    for p in punches:
        by_person.setdefault(p.person, set()).add(p.log_type)
    return sum(1 for t in by_person.values() if "IN" in t and "OUT" not in t)


@frappe.whitelist()
def get_group_attendance_today(**kwargs):
    today = frappe.utils.today()
    punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": today},
        fields=["person", "log_type"],
    )
    by_person = {}
    for p in punches:
        by_person.setdefault(p.person, set()).add(p.log_type)
    present_set = {pid for pid, t in by_person.items() if "IN" in t and "OUT" in t}

    persons = frappe.db.get_all("Person", filters={"status": "Active"}, fields=["name", "group"])
    group_map = {}
    for p in persons:
        grp = p.get("group") or "No Group"
        group_map.setdefault(grp, {"present": 0, "total": 0})
        group_map[grp]["total"] += 1
        if p.name in present_set:
            group_map[grp]["present"] += 1

    labels  = list(group_map.keys())
    return {
        "labels":   labels,
        "datasets": [
            {"name": "Present", "values": [group_map[g]["present"] for g in labels]},
            {"name": "Total",   "values": [group_map[g]["total"]   for g in labels]},
        ],
    }


# ── Dashboard creation ────────────────────────────────────────────────────────

def _upsert(doctype, data):
    """Insert or update a document — never fails on duplicates."""
    name = data["name"]
    try:
        if frappe.db.exists(doctype, name):
            doc = frappe.get_doc(doctype, name)
            doc.update(data)
            doc.save(ignore_permissions=True)
            print(f"  Updated {doctype}: {name}")
        else:
            doc = frappe.new_doc(doctype)
            doc.update(data)
            doc.insert(ignore_permissions=True)
            print(f"  Created {doctype}: {name}")
        frappe.db.commit()
    except Exception as e:
        print(f"  ERROR {doctype} '{name}': {e}")


def create_dashboard():
    print("\n── Number Cards ──")
    for card in NUMBER_CARDS:
        _upsert("Number Card", card)

    print("\n── Charts ──")
    for chart in CHARTS:
        _upsert("Dashboard Chart", chart)

    print("\n── Dashboard ──")
    dash_name = "Kiosk Attendance"
    try:
        if frappe.db.exists("Dashboard", dash_name):
            dash = frappe.get_doc("Dashboard", dash_name)
            dash.cards  = []
            dash.charts = []
        else:
            dash = frappe.new_doc("Dashboard")
            dash.dashboard_name = dash_name

        for card in NUMBER_CARDS:
            dash.append("cards",  {"card":  card["name"]})
        for chart in CHARTS:
            dash.append("charts", {"chart": chart["name"]})

        dash.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Dashboard '{dash_name}' ready!")
        print("\nNavigate to: Frappe Admin → Dashboard → Kiosk Attendance")
    except Exception as e:
        print(f"  ERROR creating Dashboard: {e}")
