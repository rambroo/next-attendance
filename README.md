# Next Attendance

Frappe app backend for the **Next Attendance** mobile app.

Provides:
- Employee punch-in/out API with selfie + GPS verification
- Kiosk mode API for student / person attendance
- Custom fields on Employee Checkin (selfie, GPS, geofence status)
- Server scripts: `attendance_app_punch`, `techniti_kiosk_lookup`, `techniti_kiosk_punch`
- DocTypes: Person, Person Group, Person Attendance

## Installation

```bash
bench get-app next_attendance https://github.com/your-org/next-attendance
bench --site yoursite.local install-app next_attendance
```
