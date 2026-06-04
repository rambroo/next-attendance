import frappe
from frappe.utils import format_datetime, get_datetime


def execute(filters=None):
    filters     = frappe._dict(filters or {})
    date        = filters.get("date") or frappe.utils.today()
    cutoff_time = filters.get("cutoff_time") or "09:30:00"
    group       = filters.get("group")
    person_type = filters.get("person_type")

    cutoff_dt = get_datetime(f"{date} {cutoff_time}")

    columns = [
        {"label": "ID / Roll No",   "fieldname": "id_number",   "fieldtype": "Data", "width": 110},
        {"label": "Name",           "fieldname": "person_name", "fieldtype": "Data", "width": 180},
        {"label": "Type",           "fieldname": "person_type", "fieldtype": "Data", "width": 120},
        {"label": "Group / Class",  "fieldname": "grp",         "fieldtype": "Data", "width": 120},
        {"label": "IN Time",        "fieldname": "in_time",     "fieldtype": "Data", "width": 110},
        {"label": "Delay",          "fieldname": "delay",       "fieldtype": "Data", "width": 90},
        {"label": "OUT Time",       "fieldname": "out_time",    "fieldtype": "Data", "width": 110},
    ]

    # All IN punches for the date
    in_punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": date, "log_type": "IN"},
        fields=["person", "person_name", "person_type", "time"],
    )

    # All OUT punches for the date
    out_punches = frappe.db.get_all(
        "Person Attendance",
        filters={"attendance_date": date, "log_type": "OUT"},
        fields=["person", "time"],
    )
    out_map = {p.person: p.time for p in out_punches}

    # Get person details for group filter
    person_info = {}
    for p in frappe.db.get_all(
        "Person",
        fields=["name", "id_number", "group", "person_type"],
    ):
        person_info[p.name] = p

    data = []
    for punch in in_punches:
        in_dt = get_datetime(punch.time) if punch.time else None
        if not in_dt or in_dt <= cutoff_dt:
            continue  # on time or no punch — skip

        pinfo = person_info.get(punch.person, frappe._dict())

        if group and pinfo.get("group") != group:
            continue
        if person_type and (pinfo.get("person_type") or punch.person_type) != person_type:
            continue

        # Calculate delay
        diff_seconds = int((in_dt - cutoff_dt).total_seconds())
        hours, rem   = divmod(diff_seconds, 3600)
        minutes      = rem // 60
        if hours:
            delay = f"{hours}h {minutes}m late"
        else:
            delay = f"{minutes}m late"

        out_dt  = out_map.get(punch.person)
        out_str = format_datetime(out_dt, "hh:mm a") if out_dt else "—"

        data.append({
            "id_number":   pinfo.get("id_number", ""),
            "person_name": punch.person_name,
            "person_type": pinfo.get("person_type") or punch.person_type or "",
            "grp":         pinfo.get("group") or "",
            "in_time":     format_datetime(in_dt, "hh:mm a"),
            "delay":       delay,
            "out_time":    out_str,
        })

    # Sort by most late first
    data.sort(key=lambda r: r.get("delay", ""), reverse=True)

    if not data:
        data.append({"person_name": f"No late arrivals after {cutoff_time} on {date}"})

    return columns, data
