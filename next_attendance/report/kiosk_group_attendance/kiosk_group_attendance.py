import frappe
from frappe.utils import format_datetime, date_range, getdate


def execute(filters=None):
    filters    = frappe._dict(filters or {})
    from_date  = filters.get("from_date") or frappe.utils.today()
    to_date    = filters.get("to_date")   or frappe.utils.today()
    group      = filters.get("group")
    person_type = filters.get("person_type")

    dates = []
    cur = getdate(from_date)
    end = getdate(to_date)
    while cur <= end:
        dates.append(cur)
        cur = frappe.utils.add_days(cur, 1)

    # ── Columns ──────────────────────────────────────────────────────────────
    columns = [
        {"label": "ID",    "fieldname": "id_number",   "fieldtype": "Data", "width": 90},
        {"label": "Name",  "fieldname": "person_name", "fieldtype": "Data", "width": 160},
        {"label": "Group", "fieldname": "grp",         "fieldtype": "Data", "width": 100},
        {"label": "Type",  "fieldname": "person_type", "fieldtype": "Data", "width": 110},
    ]
    for d in dates:
        columns.append({
            "label":     d.strftime("%d %b"),
            "fieldname": f"d_{d.strftime('%Y%m%d')}",
            "fieldtype": "Data",
            "width":     70,
        })
    columns.append({"label": "Present", "fieldname": "present_days", "fieldtype": "Int", "width": 70})

    # ── Fetch persons ────────────────────────────────────────────────────────
    person_filters = {"status": "Active"}
    persons = frappe.db.get_all(
        "Person",
        filters=person_filters,
        fields=["name", "person_name", "id_number", "person_type", "group"],
        order_by="group asc, person_name asc",
    )
    if group:
        persons = [p for p in persons if p.get("group") == group]
    if person_type:
        persons = [p for p in persons if p.get("person_type") == person_type]

    # ── Fetch punches ────────────────────────────────────────────────────────
    punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": ["between", [from_date, to_date]]},
        fields=["person", "log_type", "attendance_date"],
    )

    punch_map = {}
    for p in punches:
        key = (p.person, str(p.attendance_date))
        punch_map.setdefault(key, set()).add(p.log_type)

    today = frappe.utils.getdate()

    # ── Rows ─────────────────────────────────────────────────────────────────
    data = []
    current_group = None

    for person in persons:
        grp = person.get("group") or "No Group"

        # Group header row
        if grp != current_group:
            current_group = grp
            if data:
                data.append({})
            data.append({"person_name": f"── {grp} ──"})

        row = {
            "id_number":   person.id_number,
            "person_name": person.person_name,
            "grp":         grp,
            "person_type": person.person_type or "",
        }
        present_days = 0

        for d in dates:
            key  = (person.name, str(d))
            types = punch_map.get(key, set())
            if "IN" in types and "OUT" in types:
                cell = "P"
                present_days += 1
            elif types:
                cell = "½"
            elif d > today:
                cell = "-"
            else:
                cell = "A"
            row[f"d_{d.strftime('%Y%m%d')}"] = cell

        row["present_days"] = present_days
        data.append(row)

    return columns, data
