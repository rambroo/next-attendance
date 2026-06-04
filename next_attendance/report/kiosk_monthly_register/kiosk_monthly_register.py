import frappe
import calendar

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def execute(filters=None):
    filters = frappe._dict(filters or {})

    month_name  = filters.get("month") or frappe.utils.getdate().strftime("%B")
    year        = int(filters.get("year")  or frappe.utils.getdate().year)
    month       = MONTH_MAP.get(month_name, frappe.utils.getdate().month)
    group       = filters.get("group")
    person_type = filters.get("person_type")

    _, days_in_month = calendar.monthrange(year, month)

    # ── Columns ──────────────────────────────────────────────────────────────
    columns = [
        {"label": "ID",            "fieldname": "id_number",   "fieldtype": "Data", "width": 90},
        {"label": "Name",          "fieldname": "person_name", "fieldtype": "Data", "width": 160},
        {"label": "Group",         "fieldname": "grp",         "fieldtype": "Data", "width": 100},
    ]
    for d in range(1, days_in_month + 1):
        columns.append({
            "label":     str(d),
            "fieldname": f"d{d:02d}",
            "fieldtype": "Data",
            "width":     36,
        })
    columns.append({"label": "Present", "fieldname": "present_days", "fieldtype": "Int", "width": 65})
    columns.append({"label": "Absent",  "fieldname": "absent_days",  "fieldtype": "Int", "width": 65})

    # ── Fetch persons ────────────────────────────────────────────────────────
    persons = frappe.db.get_all(
        "Person",
        filters={"status": "Active"},
        fields=["name", "person_name", "id_number", "person_type", "group"],
        order_by="person_name asc",
    )
    if group:
        persons = [p for p in persons if p.get("group") == group]
    if person_type:
        persons = [p for p in persons if p.get("person_type") == person_type]

    # ── Fetch punches for the month ──────────────────────────────────────────
    from_date = f"{year}-{month:02d}-01"
    to_date   = f"{year}-{month:02d}-{days_in_month:02d}"

    punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": ["between", [from_date, to_date]]},
        fields=["person", "log_type", "attendance_date"],
    )

    # punch_map: {person_name: {day_int: set_of_log_types}}
    punch_map = {}
    for p in punches:
        day = frappe.utils.getdate(p.attendance_date).day
        punch_map.setdefault(p.person, {}).setdefault(day, set()).add(p.log_type)

    today = frappe.utils.getdate()

    # ── Build rows ───────────────────────────────────────────────────────────
    data = []
    for person in persons:
        row = {
            "id_number":   person.id_number,
            "person_name": person.person_name,
            "grp":         person.get("group") or "",
        }
        present_days = absent_days = 0

        for d in range(1, days_in_month + 1):
            this_date = frappe.utils.getdate(f"{year}-{month:02d}-{d:02d}")
            types     = punch_map.get(person.name, {}).get(d, set())

            if "IN" in types and "OUT" in types:
                cell = "P"
                present_days += 1
            elif types:
                cell = "½"          # IN only (still inside)
            elif this_date > today:
                cell = "—"          # future date
            else:
                cell = "A"
                absent_days += 1

            row[f"d{d:02d}"] = cell

        row["present_days"] = present_days
        row["absent_days"]  = absent_days
        data.append(row)

    # ── Summary ──────────────────────────────────────────────────────────────
    total_present = sum(r.get("present_days", 0) for r in data)
    total_absent  = sum(r.get("absent_days",  0) for r in data)
    data.append({})
    data.append({
        "person_name":   f"TOTAL ({len(persons)} persons)",
        "present_days":  total_present,
        "absent_days":   total_absent,
    })

    return columns, data
