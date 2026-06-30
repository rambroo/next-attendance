"""
Idempotent install / migrate handler for next_attendance.
Safe to run multiple times — creates missing items, updates existing ones,
never raises errors for records that already exist.
"""
import frappe


# ── Custom fields on Employee Checkin ────────────────────────────────────────

CUSTOM_FIELDS = {
    "Employee Checkin": [
        {"fieldname": "custom_selfie_image",   "label": "Selfie Image",     "fieldtype": "Data",       "insert_after": "device_id",             "read_only": 1},
        {"fieldname": "custom_geofence_status","label": "Geofence Status",   "fieldtype": "Data",       "insert_after": "custom_selfie_image",   "read_only": 1},
        {"fieldname": "custom_notes",          "label": "Notes",             "fieldtype": "Small Text", "insert_after": "custom_geofence_status"},
        {"fieldname": "latitude",              "label": "Latitude",          "fieldtype": "Float",      "insert_after": "custom_notes",          "read_only": 1},
        {"fieldname": "longitude",             "label": "Longitude",         "fieldtype": "Float",      "insert_after": "latitude",              "read_only": 1},
    ]
}

# ── DocTypes (created if missing, skipped if already exist) ──────────────────

DOCTYPES = [
    {
        "name": "Person Group Member", "istable": 1, "custom": 1, "module": "Custom",
        "fields": [
            {"fieldname": "person",      "label": "Person",      "fieldtype": "Link", "options": "Person", "reqd": 1, "in_list_view": 1},
            {"fieldname": "person_name", "label": "Person Name", "fieldtype": "Data", "fetch_from": "person.person_name", "in_list_view": 1},
            {"fieldname": "person_type", "label": "Person Type", "fieldtype": "Data", "fetch_from": "person.person_type", "in_list_view": 1},
        ],
    },
    {
        "name": "Person", "autoname": "field:id_number", "naming_rule": "By fieldname",
        "custom": 1, "module": "Custom", "track_changes": 1, "allow_import": 1, "title_field": "person_name",
        "fields": [
            {"fieldname": "person_name",    "label": "Person Name",   "fieldtype": "Data",   "reqd": 1, "in_list_view": 1},
            {"fieldname": "person_type",    "label": "Person Type",   "fieldtype": "Select",
             "options": "Student\nSales Person\nVolunteer\nIntern\nSales Partner\nContractor\nOther", "reqd": 1, "in_list_view": 1},
            {"fieldname": "id_number",      "label": "ID Number",     "fieldtype": "Data",   "reqd": 1, "unique": 1, "in_list_view": 1},
            {"fieldname": "group",          "label": "Group / Class", "fieldtype": "Data",   "in_list_view": 1},
            {"fieldname": "column_break_1", "fieldtype": "Column Break"},
            {"fieldname": "image",          "label": "Photo",         "fieldtype": "Attach Image"},
            {"fieldname": "phone",          "label": "Phone",         "fieldtype": "Data"},
            {"fieldname": "email",          "label": "Email",         "fieldtype": "Data"},
            {"fieldname": "date_of_birth",  "label": "Date of Birth", "fieldtype": "Date"},
            {"fieldname": "company",        "label": "Company",       "fieldtype": "Link",   "options": "Company"},
            {"fieldname": "status",         "label": "Status",        "fieldtype": "Select",
             "options": "Active\nInactive", "default": "Active", "reqd": 1, "in_list_view": 1},
            {"fieldname": "notes",          "label": "Notes",         "fieldtype": "Small Text"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "HR Manager",     "read": 1, "write": 1, "create": 1},
        ],
    },
    {
        "name": "Person Group", "custom": 1, "module": "Custom", "allow_import": 1,
        "fields": [
            {"fieldname": "group_name", "label": "Group Name", "fieldtype": "Data",   "reqd": 1, "in_list_view": 1},
            {"fieldname": "group_type", "label": "Group Type", "fieldtype": "Select",
             "options": "Class\nTerritory\nDepartment\nBatch\nOther", "in_list_view": 1},
            {"fieldname": "company",    "label": "Company",    "fieldtype": "Link",   "options": "Company"},
            {"fieldname": "section_members", "label": "Members", "fieldtype": "Section Break"},
            {"fieldname": "persons",    "label": "Persons",    "fieldtype": "Table",  "options": "Person Group Member"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "HR Manager",     "read": 1, "write": 1, "create": 1},
        ],
    },
    {
        "name": "Person Attendance", "autoname": "PA-.YYYY.MM.DD.-.####", "naming_rule": "Expression",
        "custom": 1, "module": "Custom", "track_changes": 1, "title_field": "person_name",
        "fields": [
            {"fieldname": "person",          "label": "Person",         "fieldtype": "Link",     "options": "Person", "reqd": 1, "in_list_view": 1},
            {"fieldname": "person_name",     "label": "Person Name",    "fieldtype": "Data",     "fetch_from": "person.person_name", "in_list_view": 1},
            {"fieldname": "person_type",     "label": "Person Type",    "fieldtype": "Data",     "fetch_from": "person.person_type"},
            {"fieldname": "attendance_date", "label": "Date",           "fieldtype": "Date",     "reqd": 1, "in_list_view": 1},
            {"fieldname": "column_break_1",  "fieldtype": "Column Break"},
            {"fieldname": "log_type",        "label": "Log Type",       "fieldtype": "Select",   "options": "IN\nOUT", "reqd": 1, "in_list_view": 1},
            {"fieldname": "time",            "label": "Time",           "fieldtype": "Datetime", "in_list_view": 1},
            {"fieldname": "location",        "label": "Kiosk Location", "fieldtype": "Data"},
            {"fieldname": "device_id",       "label": "Device ID",      "fieldtype": "Data"},
            {"fieldname": "selfie_image",    "label": "Selfie Image",   "fieldtype": "Data",     "read_only": 1},
            {"fieldname": "marked_by",       "label": "Marked By",      "fieldtype": "Link",     "options": "User"},
        ],
        "permissions": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "HR Manager",     "read": 1, "write": 1, "create": 1},
        ],
    },
]

# ── Server scripts (upserted on every install/migrate) ────────────────────────

SERVER_SCRIPTS = [
    {
        "name": "attendance_app_punch", "script_type": "API",
        "api_method": "attendance_app_punch", "allow_guest": 0,
        "script": (
            "d = frappe.form_dict\n"
            "employee  = d.get('employee')\n"
            "log_type  = d.get('log_type')\n"
            "time_str  = d.get('time')\n"
            "latitude  = d.get('latitude')\n"
            "longitude = d.get('longitude')\n"
            "file_url  = d.get('selfie_file_url', '')\n"
            "notes     = d.get('notes', '')\n"
            "if not (employee and log_type and time_str):\n"
            "    frappe.throw('employee, log_type and time are required')\n"
            "checkin = frappe.get_doc({'doctype': 'Employee Checkin', 'employee': employee, 'log_type': log_type, 'time': time_str})\n"
            "if latitude:  checkin.latitude  = frappe.utils.flt(latitude)\n"
            "if longitude: checkin.longitude = frappe.utils.flt(longitude)\n"
            "if file_url:  checkin.custom_selfie_image = file_url\n"
            "if notes:     checkin.custom_notes = notes\n"
            "checkin.insert(ignore_permissions=False)\n"
            "frappe.response['message'] = checkin.as_dict()\n"
        ),
    },
    {
        "name": "techniti_kiosk_lookup", "script_type": "API",
        "api_method": "techniti_kiosk_lookup", "allow_guest": 0,
        "script": (
            "d = frappe.form_dict\n"
            "id_number = d.get('id_number')\n"
            "if not id_number:\n"
            "    frappe.throw('ID number is required')\n"
            "person = frappe.db.get_value('Person', {'id_number': id_number, 'status': 'Active'}, ['name', 'person_name', 'person_type', 'image'], as_dict=True)\n"
            "if not person:\n"
            "    frappe.throw('No active person found with ID: ' + str(id_number))\n"
            "image_url = (frappe.utils.get_url() + person.image) if person.get('image') else None\n"
            "frappe.response['message'] = {'name': person.name, 'person_name': person.person_name, 'person_type': person.get('person_type') or '', 'image_url': image_url}\n"
        ),
    },
    {
        "name": "techniti_kiosk_punch", "script_type": "API",
        "api_method": "techniti_kiosk_punch", "allow_guest": 0,
        "script": (
            "d = frappe.form_dict\n"
            "id_number  = d.get('id_number')\n"
            "location   = d.get('location') or 'Kiosk'\n"
            "device_id  = d.get('device_id') or 'unknown'\n"
            "selfie_url = d.get('selfie_url') or ''\n"
            "if not id_number:\n"
            "    frappe.throw('ID number is required')\n"
            "person = frappe.db.get_value('Person', {'id_number': id_number, 'status': 'Active'}, ['name', 'person_name', 'person_type', 'image'], as_dict=True)\n"
            "if not person:\n"
            "    frappe.throw('No active person found with ID: ' + str(id_number))\n"
            "last_logs = frappe.db.get_all('Person Attendance', filters={'person': person.name, 'attendance_date': frappe.utils.today()}, fields=['log_type'], order_by='creation desc', limit=1)\n"
            "last_log = last_logs[0].log_type if last_logs else None\n"
            "log_type  = 'OUT' if last_log == 'IN' else 'IN'\n"
            "doc = frappe.get_doc({'doctype': 'Person Attendance', 'person': person.name, 'person_name': person.person_name, 'person_type': person.get('person_type') or '', 'attendance_date': frappe.utils.today(), 'time': frappe.utils.now_datetime(), 'log_type': log_type, 'location': location, 'device_id': device_id, 'marked_by': frappe.session.user})\n"
            "if selfie_url: doc.selfie_image = selfie_url\n"
            "doc.insert(ignore_permissions=True)\n"
            "profile_image_url = (frappe.utils.get_url() + person.image) if person.get('image') else None\n"
            "frappe.response['message'] = {'person_name': person.person_name, 'person_type': person.get('person_type') or '', 'log_type': log_type, 'time': frappe.utils.format_datetime(doc.time, 'hh:mm a'), 'image_url': profile_image_url, 'selfie_url': selfie_url}\n"
        ),
    },
    {
        "name": "Employee Checkin Geofence & Selfie Validation",
        "script_type": "DocType Event", "reference_doctype": "Employee Checkin",
        "doctype_event": "Before Save", "allow_guest": 0,
        "script": (
            "import math\n"
            "from frappe.utils import flt\n"
            "LOCATIONS = [{'name': 'WCWW Office', 'lat': 19.2172, 'lon': 72.8246, 'radius': 50}, {'name': 'Old Age Home', 'lat': 19.2165, 'lon': 72.8246, 'radius': 50}]\n"
            "def haversine(lat1, lon1, lat2, lon2):\n"
            "    R = 6371000\n"
            "    phi1, phi2 = math.radians(lat1), math.radians(lat2)\n"
            "    dphi, dlam = math.radians(lat2-lat1), math.radians(lon2-lon1)\n"
            "    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2\n"
            "    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))\n"
            "lat, lon = flt(doc.get('latitude')), flt(doc.get('longitude'))\n"
            "if lat and lon:\n"
            "    for loc in LOCATIONS:\n"
            "        dist = haversine(lat, lon, loc['lat'], loc['lon'])\n"
            "        if dist <= loc['radius']:\n"
            "            doc.custom_geofence_status = f\"Within Range — {loc['name']} ({int(dist)}m)\"\n"
            "            break\n"
            "    else:\n"
            "        min_dist = min(haversine(lat, lon, l['lat'], l['lon']) for l in LOCATIONS)\n"
            "        frappe.throw(f'Check-in blocked: You are {int(min_dist)}m away. Must be within 50m.')\n"
        ),
    },
]


# ── Entry points called by hooks.py ──────────────────────────────────────────

def after_install():
    _create_doctypes()
    _create_custom_fields()
    _create_server_scripts()
    frappe.db.commit()
    frappe.msgprint("Next Attendance installed successfully.", alert=True)


def after_migrate():
    _create_doctypes()
    _create_custom_fields()
    _create_server_scripts()
    frappe.db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_doctypes():
    for dt_def in DOCTYPES:
        name = dt_def["name"]
        try:
            if frappe.db.exists("DocType", name):
                continue   # already exists — skip without error
            doc = frappe.get_doc({"doctype": "DocType", **dt_def})
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"next_attendance._create_doctypes: {name}: {e}")


def _create_custom_fields():
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    except Exception as e:
        frappe.log_error(f"next_attendance._create_custom_fields: {e}")


def _create_server_scripts():
    for script_data in SERVER_SCRIPTS:
        name = script_data["name"]
        try:
            if frappe.db.exists("Server Script", name):
                doc = frappe.get_doc("Server Script", name)
                doc.update(script_data)
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({"doctype": "Server Script", **script_data})
                doc.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"next_attendance._create_server_scripts: {name}: {e}")
