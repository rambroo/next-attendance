import frappe
from frappe.utils import format_datetime


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = [
        {"label": "ID / Roll No",  "fieldname": "id_number",   "fieldtype": "Data",     "width": 110},
        {"label": "Name",          "fieldname": "person_name",  "fieldtype": "Data",     "width": 180},
        {"label": "Type",          "fieldname": "person_type",  "fieldtype": "Data",     "width": 120},
        {"label": "Group / Class", "fieldname": "grp",          "fieldtype": "Data",     "width": 120},
        {"label": "IN Time",       "fieldname": "in_time",      "fieldtype": "Data",     "width": 100},
        {"label": "OUT Time",      "fieldname": "out_time",     "fieldtype": "Data",     "width": 100},
        {"label": "Status",        "fieldname": "status",       "fieldtype": "Data",     "width": 120},
    ]

    date        = filters.get("date") or frappe.utils.today()
    group       = filters.get("group")
    person_type = filters.get("person_type")

    # ── Fetch persons ────────────────────────────────────────────────────────
    person_filters = {"status": "Active"}
    persons = frappe.db.get_all(
        "Person",
        filters=person_filters,
        fields=["name", "person_name", "id_number", "person_type", "group"],
        order_by="person_name asc",
    )
    if group:
        persons = [p for p in persons if p.get("group") == group]
    if person_type:
        persons = [p for p in persons if p.get("person_type") == person_type]

    # ── Fetch punches for the day ────────────────────────────────────────────
    punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": date},
        fields=["person", "log_type", "time"],
        order_by="time asc",
    )

    # Build punch map: {person_name: {IN: time, OUT: time}}
    punch_map = {}
    for p in punches:
        punch_map.setdefault(p.person, {})
        punch_map[p.person][p.log_type] = p.time   # last punch wins per type

    # ── Build rows ───────────────────────────────────────────────────────────
    data    = []
    present = absent = partial = 0

    for person in persons:
        pdata   = punch_map.get(person.name, {})
        in_dt   = pdata.get("IN")
        out_dt  = pdata.get("OUT")

        in_str  = format_datetime(in_dt,  "hh:mm a") if in_dt  else ""
        out_str = format_datetime(out_dt, "hh:mm a") if out_dt else ""

        if in_dt and out_dt:
            status  = "Present"
            present += 1
            indicator = "green"
        elif in_dt:
            status  = "Partial (IN only)"
            partial += 1
            indicator = "orange"
        else:
            status  = "Absent"
            absent  += 1
            indicator = "red"

        data.append({
            "id_number":   person.id_number,
            "person_name": person.person_name,
            "person_type": person.person_type or "",
            "grp":         person.get("group") or "",
            "in_time":     in_str,
            "out_time":    out_str,
            "status":      status,
        })

    # ── Summary row ──────────────────────────────────────────────────────────
    total = len(persons)
    data.append({})
    data.append({
        "person_name": f"TOTAL  ({total} persons)",
        "in_time":     f"Present: {present}",
        "out_time":    f"Partial: {partial}",
        "status":      f"Absent: {absent}",
    })

    return columns, data
