"""
Idempotent install / migrate handler for next_attendance.
Safe to run multiple times — creates missing items, updates existing ones,
never raises errors for records that already exist.
"""
import frappe


# ── Custom fields on Employee Checkin ────────────────────────────────────────

CUSTOM_FIELDS = {
    "Employee Checkin": [
        # Not read_only: HR/System Manager users check in through the desk form and
        # attach the selfie with this field's own button. Frappe hides that button
        # on a read-only field, which silently blocked HR check-ins after install.
        {"fieldname": "custom_selfie_image",   "label": "Selfie",           "fieldtype": "Attach Image", "insert_after": "device_id",           "read_only": 0},
        {"fieldname": "custom_geofence_status","label": "Geofence Status",   "fieldtype": "Select", "options": "\nWithin Range\nOutside Range",
         "insert_after": "custom_selfie_image", "read_only": 1},
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
            # The client sends the punch time (the app queues punches offline and
            # sends the capture time later). Accept it, but only within a window:
            # not in the future beyond clock drift, and not older than 48 hours.
            "punch_time = frappe.utils.get_datetime(time_str)\n"
            "age = frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), punch_time)\n"
            "if age < -600:\n"
            "    frappe.throw('Punch time is in the future. Please check the date and time on your phone.')\n"
            "if age > 172800:\n"
            "    frappe.throw('This punch is more than 48 hours old and cannot be recorded. Please contact HR.')\n"
            # The selfie URL also comes from the client: only accept a file this
            # user actually uploaded, so it can't point at someone else's file.
            "if file_url and not frappe.db.exists('File', {'file_url': file_url, 'owner': frappe.session.user}):\n"
            "    frappe.throw('Selfie upload not found for your account. Please retake the selfie.')\n"
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
            # Any logged-in account could otherwise look up and mark attendance
            # for any person by guessing ID numbers.
            "KIOSK_ROLES = ['Kiosk User', 'Operations Manager', 'HR Manager', 'System Manager']\n"
            "if not frappe.db.exists('Has Role', {'parent': frappe.session.user, 'parenttype': 'User', 'role': ['in', KIOSK_ROLES]}):\n"
            "    frappe.throw('Not permitted: this account is not set up as a kiosk.')\n"
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
            # Any logged-in account could otherwise look up and mark attendance
            # for any person by guessing ID numbers.
            "KIOSK_ROLES = ['Kiosk User', 'Operations Manager', 'HR Manager', 'System Manager']\n"
            "if not frappe.db.exists('Has Role', {'parent': frappe.session.user, 'parenttype': 'User', 'role': ['in', KIOSK_ROLES]}):\n"
            "    frappe.throw('Not permitted: this account is not set up as a kiosk.')\n"
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
        # Off until the site's coordinates are filled in — enabled with the
        # example location it would block every check-in.
        "disabled": 1,
        "script": (
            "# Ships DISABLED. Replace the example below with your own sites, then enable\n"
            "# this script. cos_lat = cos(latitude in radians), e.g. 0.9444 at 19.2 N.\n"
            "LOCATIONS = [\n"
            "    {'name': 'Example office', 'lat': 12.9716, 'lon': 77.5946, 'radius': 50, 'cos_lat': 0.9745},\n"
            "]\n"
            "lat = frappe.utils.flt(doc.get('latitude'))\n"
            "lon = frappe.utils.flt(doc.get('longitude'))\n"
            "if lat and lon:\n"
            "    nearest = None\n"
            "    for loc in LOCATIONS:\n"
            "        dlat = (loc['lat'] - lat) * 111320.0\n"
            "        dlon = (loc['lon'] - lon) * 111320.0 * loc['cos_lat']\n"
            "        dist = (dlat * dlat + dlon * dlon) ** 0.5\n"
            "        if dist <= loc['radius']:\n"
            "            doc.custom_geofence_status = 'Within Range'\n"
            "            doc.custom_matched_location = loc['name']\n"
            "            doc.custom_distance_meters = int(dist)\n"
            "            nearest = None\n"
            "            break\n"
            "        if nearest is None or dist < nearest:\n"
            "            nearest = dist\n"
            "    if nearest is not None:\n"
            "        frappe.throw('Check-in blocked: you are ' + str(int(nearest)) + ' m from the nearest allowed location.')\n"
        ),
    },
]


# ── Entry points called by hooks.py ──────────────────────────────────────────

def _create_roles():
    # Dedicated low-privilege role for kiosk devices. Give the kiosk's API user
    # this role only, rather than a staff member's own account.
    if not frappe.db.exists("Role", "Kiosk User"):
        frappe.get_doc({"doctype": "Role", "role_name": "Kiosk User", "desk_access": 0}).insert(ignore_permissions=True)


def after_install():
    _create_roles()
    _create_doctypes()
    _create_custom_fields()
    _create_server_scripts()
    frappe.db.commit()
    frappe.msgprint("Next Attendance installed successfully.", alert=True)


def after_migrate():
    _create_roles()
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
        # update=False is load-bearing. This app is installed onto sites whose
        # fields were created by hand and may be tuned locally; the default
        # update=True rewrites any existing field to match the dict above,
        # which is how a live "Attach Image" selfie field got downgraded to
        # plain Data on first install. Create what is missing, touch nothing else.
        create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=False)
    except Exception as e:
        frappe.log_error(f"next_attendance._create_custom_fields: {e}")


def _create_server_scripts():
    for script_data in SERVER_SCRIPTS:
        name = script_data["name"]
        try:
            if frappe.db.exists("Server Script", name):
                # Leave an existing script alone. These are live API endpoints
                # that a site may have edited (e.g. the geofence script is
                # disabled on production); silently replacing them on install
                # would discard those changes. Ship script updates through a
                # patch instead, where the intent is explicit.
                continue
            else:
                doc = frappe.get_doc({"doctype": "Server Script", **script_data})
                doc.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"next_attendance._create_server_scripts: {name}: {e}")
