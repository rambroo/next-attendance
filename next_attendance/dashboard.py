"""
Creates the Kiosk Attendance Dashboard with Number Cards and Charts.
Run via: bench --site yoursite.local execute next_attendance.dashboard.create_dashboard
Safe to run multiple times — updates existing records.
"""
import frappe


NUMBER_CARDS = [
    {
        "label":         "Kiosk - Present Today",
        "document_type": "Person Attendance",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  "[]",
        "type":          "Custom",
        "method":        "next_attendance.dashboard.get_present_today",
        "color":         "#3CC88F",
    },
    {
        "label":         "Kiosk - Absent Today",
        "document_type": "Person",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  "[]",
        "type":          "Custom",
        "method":        "next_attendance.dashboard.get_absent_today",
        "color":         "#E53935",
    },
    {
        "label":         "Kiosk - Checked In Only",
        "document_type": "Person Attendance",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  "[]",
        "type":          "Custom",
        "method":        "next_attendance.dashboard.get_partial_today",
        "color":         "#F59E0B",
    },
    {
        "label":         "Kiosk - Total Registered",
        "document_type": "Person",
        "function":      "Count",
        "aggregate_function_based_on": "name",
        "filters_json":  '[["status","=","Active"]]',
        "color":         "#1A6B47",
    },
]

CHARTS = [
    {
        "chart_name":    "Kiosk - Monthly Attendance Trend",
        "chart_type":    "Count",
        "document_type": "Person Attendance",
        "based_on":      "attendance_date",
        "filters_json":  '[["log_type","=","IN"]]',
        "type":          "Bar",
        "color":         "#3CC88F",
        "time_interval": "Daily",
        "timespan":      "Last Month",
    },
    {
        "chart_name":    "Kiosk - Group Attendance Today",
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


# ── Custom metric methods ─────────────────────────────────────────────────────

@frappe.whitelist()
def get_present_today():
    today   = frappe.utils.today()
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
    today   = frappe.utils.today()
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
    today   = frappe.utils.today()
    punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": today},
        fields=["person", "log_type"],
    )
    by_person = {}
    for p in punches:
        by_person.setdefault(p.person, set()).add(p.log_type)
    present_set = {pid for pid, t in by_person.items() if "IN" in t and "OUT" in t}

    persons   = frappe.db.get_all("Person", filters={"status": "Active"}, fields=["name", "group"])
    group_map = {}
    for p in persons:
        grp = p.get("group") or "No Group"
        group_map.setdefault(grp, {"present": 0, "total": 0})
        group_map[grp]["total"] += 1
        if p.name in present_set:
            group_map[grp]["present"] += 1

    labels = list(group_map.keys())
    return {
        "labels":   labels,
        "datasets": [
            {"name": "Present", "values": [group_map[g]["present"] for g in labels]},
            {"name": "Total",   "values": [group_map[g]["total"]   for g in labels]},
        ],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upsert_card(data):
    """Upsert a Number Card. Returns the actual doc.name after save."""
    label    = data["label"]
    existing = frappe.db.get_value("Number Card", {"label": label}, "name")
    if existing:
        doc = frappe.get_doc("Number Card", existing)
        doc.update(data)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Updated Number Card: {doc.name}")
        return doc.name
    else:
        doc = frappe.new_doc("Number Card")
        doc.update(data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Created Number Card: {doc.name}")
        return doc.name


def _upsert_chart(data):
    """Upsert a Dashboard Chart. Returns the actual doc.name after save."""
    chart_name = data["chart_name"]
    existing   = frappe.db.get_value("Dashboard Chart", {"chart_name": chart_name}, "name")
    if existing:
        doc = frappe.get_doc("Dashboard Chart", existing)
        doc.update(data)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Updated Dashboard Chart: {doc.name}")
        return doc.name
    else:
        doc = frappe.new_doc("Dashboard Chart")
        doc.update(data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Created Dashboard Chart: {doc.name}")
        return doc.name


# ── Entry point ───────────────────────────────────────────────────────────────

def create_dashboard():
    print("\n── Number Cards ──")
    card_names = [_upsert_card(c) for c in NUMBER_CARDS]

    print("\n── Charts ──")
    chart_names = [_upsert_chart(c) for c in CHARTS]

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

        for name in card_names:
            dash.append("cards",  {"card":  name})
        for name in chart_names:
            dash.append("charts", {"chart": name})

        dash.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"  Dashboard '{dash_name}' is ready!")
        print("\n  Navigate: Frappe Admin → search 'Dashboard' → Kiosk Attendance")
    except Exception as e:
        print(f"  ERROR creating Dashboard: {e}")
