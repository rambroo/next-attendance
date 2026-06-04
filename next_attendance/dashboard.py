"""
Creates the Kiosk Attendance Dashboard with Number Cards and Charts.
Run via: bench --site techniti.local execute next_attendance.dashboard.create_dashboard
"""
import frappe


NUMBER_CARDS = [
    {
        "name":            "Kiosk Present Today",
        "label":           "Present Today",
        "document_type":   "Person Attendance",
        "function":        "Count",
        "aggregate_function_based_on": "name",
        "filters_json":    "[]",
        "type":            "Custom",
        "method":          "next_attendance.dashboard.get_present_today",
        "color":           "#3CC88F",
    },
    {
        "name":            "Kiosk Absent Today",
        "label":           "Absent Today",
        "document_type":   "Person",
        "function":        "Count",
        "aggregate_function_based_on": "name",
        "type":            "Custom",
        "method":          "next_attendance.dashboard.get_absent_today",
        "color":           "#E53935",
    },
    {
        "name":            "Kiosk Checked In Only",
        "label":           "Checked In (No OUT)",
        "document_type":   "Person Attendance",
        "function":        "Count",
        "type":            "Custom",
        "method":          "next_attendance.dashboard.get_partial_today",
        "color":           "#F59E0B",
    },
    {
        "name":            "Kiosk Total Persons",
        "label":           "Total Registered",
        "document_type":   "Person",
        "function":        "Count",
        "aggregate_function_based_on": "name",
        "filters_json":    '[["status","=","Active"]]',
        "color":           "#1A6B47",
    },
]

CHARTS = [
    {
        "name":          "Kiosk Monthly Attendance Trend",
        "chart_name":    "Monthly Attendance Trend",
        "chart_type":    "Count",
        "document_type": "Person Attendance",
        "based_on":      "attendance_date",
        "value_based_on": "log_type",
        "filters_json":  '[["log_type","=","IN"]]',
        "type":          "Bar",
        "color":         "#3CC88F",
        "time_interval": "Daily",
        "timespan":      "Last Month",
    },
    {
        "name":          "Kiosk Group Attendance Today",
        "chart_name":    "Group Attendance Today",
        "chart_type":    "Custom",
        "type":          "Bar",
        "color":         "#1A6B47",
        "method":        "next_attendance.dashboard.get_group_attendance_today",
    },
]


@frappe.whitelist()
def get_present_today():
    today = frappe.utils.today()
    all_punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": today},
        fields=["person", "log_type"],
    )
    by_person = {}
    for p in all_punches:
        by_person.setdefault(p.person, set()).add(p.log_type)
    present = sum(1 for types in by_person.values() if "IN" in types and "OUT" in types)
    return present


@frappe.whitelist()
def get_absent_today():
    today   = frappe.utils.today()
    total   = frappe.db.count("Person", {"status": "Active"})
    present = get_present_today()
    partial = get_partial_today()
    return max(0, total - present - partial)


@frappe.whitelist()
def get_partial_today():
    today = frappe.utils.today()
    all_punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": today},
        fields=["person", "log_type"],
    )
    by_person = {}
    for p in all_punches:
        by_person.setdefault(p.person, set()).add(p.log_type)
    partial = sum(1 for types in by_person.values() if "IN" in types and "OUT" not in types)
    return partial


@frappe.whitelist()
def get_group_attendance_today(**kwargs):
    today = frappe.utils.today()
    all_punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": today},
        fields=["person", "log_type"],
    )
    by_person = {}
    for p in all_punches:
        by_person.setdefault(p.person, set()).add(p.log_type)
    present_persons = {pid for pid, types in by_person.items() if "IN" in types and "OUT" in types}

    persons = frappe.db.get_all(
        "Person",
        filters={"status": "Active"},
        fields=["name", "group"],
    )

    group_map = {}
    for p in persons:
        grp = p.get("group") or "No Group"
        group_map.setdefault(grp, {"present": 0, "total": 0})
        group_map[grp]["total"] += 1
        if p.name in present_persons:
            group_map[grp]["present"] += 1

    labels  = list(group_map.keys())
    present = [group_map[g]["present"] for g in labels]
    total   = [group_map[g]["total"]   for g in labels]

    return {
        "labels":   labels,
        "datasets": [
            {"name": "Present", "values": present},
            {"name": "Total",   "values": total},
        ],
    }


def create_dashboard():
    # ── Number Cards ─────────────────────────────────────────────────────────
    for card in NUMBER_CARDS:
        name = card["name"]
        if frappe.db.exists("Number Card", name):
            doc = frappe.get_doc("Number Card", name)
        else:
            doc = frappe.new_doc("Number Card")
        doc.update(card)
        doc.save(ignore_permissions=True)
        print(f"  Number Card: {name}")

    # ── Charts ────────────────────────────────────────────────────────────────
    for chart in CHARTS:
        name = chart["name"]
        if frappe.db.exists("Dashboard Chart", name):
            doc = frappe.get_doc("Dashboard Chart", name)
        else:
            doc = frappe.new_doc("Dashboard Chart")
        doc.update(chart)
        doc.save(ignore_permissions=True)
        print(f"  Chart: {name}")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    dash_name = "Kiosk Attendance"
    if frappe.db.exists("Dashboard", dash_name):
        dash = frappe.get_doc("Dashboard", dash_name)
        dash.cards  = []
        dash.charts = []
    else:
        dash = frappe.new_doc("Dashboard")
        dash.dashboard_name = dash_name
        dash.is_default = 0

    for card in NUMBER_CARDS:
        dash.append("cards",  {"card":  card["name"]})
    for chart in CHARTS:
        dash.append("charts", {"chart": chart["name"]})

    dash.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"  Dashboard '{dash_name}' ready.")
    print("\nOpen: /app/kiosk-attendance or Frappe → Dashboards → Kiosk Attendance")
