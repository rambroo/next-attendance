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

# Only standard chart_types (Count / Sum / Average / Min / Max).
# chart_type "Custom" requires a Dashboard Chart Source record — not supported here.
CHARTS = [
    {
        "chart_name":    "Kiosk - Daily Check-Ins (Last Month)",
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
        "chart_name":    "Kiosk - Daily Check-Outs (Last Month)",
        "chart_type":    "Count",
        "document_type": "Person Attendance",
        "based_on":      "attendance_date",
        "filters_json":  '[["log_type","=","OUT"]]',
        "type":          "Line",
        "color":         "#1A6B47",
        "time_interval": "Daily",
        "timespan":      "Last Month",
    },
]

# Old chart names that used chart_type="Custom" — delete these if they exist
OBSOLETE_CHARTS = [
    "Kiosk Monthly Attendance Trend",
    "Kiosk Group Attendance Today",
    "Kiosk - Monthly Attendance Trend",
    "Kiosk - Group Attendance Today",
]


# ── Custom metric methods (used by Number Cards) ──────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upsert_card(data):
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


def _delete_obsolete_charts():
    for chart_name in OBSOLETE_CHARTS:
        name = frappe.db.get_value("Dashboard Chart", {"chart_name": chart_name}, "name") \
               or frappe.db.exists("Dashboard Chart", chart_name)
        if name:
            try:
                frappe.delete_doc("Dashboard Chart", name, ignore_permissions=True, force=True)
                frappe.db.commit()
                print(f"  Deleted obsolete chart: {name}")
            except Exception as e:
                print(f"  Could not delete {name}: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

def create_dashboard():
    print("\n── Cleanup obsolete charts ──")
    _delete_obsolete_charts()

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
        print(f"\n  ✓ Dashboard '{dash_name}' is ready!")
        print("  Navigate: Frappe Admin → Dashboard → Kiosk Attendance")
    except Exception as e:
        print(f"  ERROR: {e}")
