app_name            = "next_attendance"
app_title           = "Next Attendance"
app_publisher       = "TechNiti"
app_description     = "Employee punch-in/out with selfie + GPS, kiosk mode for students and external persons, and HRMS integration."
app_email           = "rohanrambhiya59@gmail.com"
app_license         = "MIT"
app_version         = "1.0.0"

# Required apps — needs Frappe core; HRMS optional but recommended
# required_apps = ["frappe"]

# Fixtures — exported on `bench export-fixtures`, auto-imported on `bench migrate`
fixtures = [
    # Custom fields added to Employee Checkin
    {
        "doctype": "Custom Field",
        "filters": [["dt", "=", "Employee Checkin"]]
    },
    # Server scripts bundled with this app
    {
        "doctype": "Server Script",
        "filters": [["name", "in", [
            "attendance_app_punch",
            "techniti_kiosk_lookup",
            "techniti_kiosk_punch",
            "Employee Checkin Geofence & Selfie Validation",
        ]]]
    },
]

# DocType Events
doc_events = {}

# After install — run setup to create custom fields if not already present
after_install = "next_attendance.install.after_install"

# After migrate — re-apply any field/script updates
after_migrate = "next_attendance.install.after_migrate"
