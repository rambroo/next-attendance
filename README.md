# Next Attendance — Frappe app

The backend for the [Next Attendance mobile app](https://github.com/rambroo/attendance-app). It adds selfie + GPS punching for employees, a kiosk mode for students or visitors, and private selfie storage to a [Frappe HR](https://frappe.io/hr) site.

## What it adds

| | |
|---|---|
| **Punch API** | `attendance_app_punch` (Server Script) — creates an Employee Checkin with GPS, selfie and notes |
| **Kiosk API** | `techniti_kiosk_lookup` and `techniti_kiosk_punch` — look up a person by ID number and record their IN/OUT |
| **Private selfies** | `next_attendance.api.sign_selfies` / `serve_selfie` — short-lived signed links, so selfies can be private files |
| **Geofence** | An Employee Checkin "Before Save" script that blocks punches outside your sites (ships **disabled**) |
| **Custom fields** | On Employee Checkin: selfie, geofence status, notes, latitude, longitude |
| **DocTypes** | Person, Person Group, Person Group Member, Person Attendance |
| **Reports** | Kiosk Daily Attendance, Group Attendance, Late Arrivals, Monthly Register |
| **Role** | Kiosk User |

## Requirements

- Frappe v15 or v16 with **Frappe HR** (`hrms`) installed
- **Server Scripts enabled** on the bench:
  ```bash
  bench set-config -g server_script_enabled 1
  ```

## Install

```bash
bench get-app https://github.com/rambroo/next-attendance
bench --site your-site install-app next_attendance
bench --site your-site migrate
```

On Frappe Cloud: add the app from GitHub to your bench, deploy, then install it on the site.

The installer only **adds** what is missing. It never changes custom fields or Server Scripts that already exist on your site, so it is safe on a site you have customised by hand. The flip side: to update a Server Script you already have, edit it in the desk (or delete it and run `bench migrate`).

## Set up

### 1. Employees

For each employee who will use the app:

1. Create a **User** with the **Employee** role.
2. On their **Employee** record, set **User ID** to that user, with **Create User Permission** ticked.

That user permission is what stops an employee from punching on behalf of someone else. Without it, the punch API accepts any employee ID the user has access to.

### 2. Kiosk (optional)

1. Create a dedicated user, e.g. `kiosk@your-domain`, with only the **Kiosk User** role. Don't reuse a staff member's account: its API key will be stored on a shared tablet.
2. On that user, go to **Settings → API Access → Generate Keys**, and copy the key and secret.
3. In the app, tap **Switch to Kiosk Mode** and enter them as `apiKey:apiSecret`.
4. Add the students or visitors as **Person** records. The ID number is what they type at the kiosk.

The kiosk endpoints refuse accounts without one of these roles: Kiosk User, Operations Manager, HR Manager, or System Manager.

### 3. Geofence (optional)

1. Open **Server Script → Employee Checkin Geofence & Selfie Validation**.
2. Replace the example in `LOCATIONS` with your own sites. For each: name, latitude, longitude, radius in metres, and `cos_lat` (the cosine of the latitude in radians, e.g. `0.9444` at 19.2°N).
3. Untick **Disabled** and save.

## Security model

- **Punch times** come from the phone, because the app queues punches offline. The server rejects times more than 10 minutes in the future or more than 48 hours old.
- **Selfie URLs** come from the phone too. The punch API only accepts a file the calling user uploaded, and `sign_selfies` only signs an image uploaded by the check-in's owner. Anything else is refused, so a check-in can't be used to read someone else's private files.
- **`serve_selfie` allows guests** on purpose: the HMAC signature (keyed on the site's encryption key, covering the file path and expiry) is the authorisation. Links expire after 15 minutes and are confined to the site's file folders.
- **GPS** is reported by the phone and can be spoofed on a rooted device. Treat the geofence as a deterrent, not proof.

Found a security issue? Please email the maintainer rather than opening a public issue.

## API reference

All endpoints need a logged-in session or an API key (`Authorization: token key:secret`), except `serve_selfie`.

| Endpoint | Method | Parameters | Returns |
|---|---|---|---|
| `/api/method/attendance_app_punch` | POST | `employee`, `log_type` (IN/OUT), `time` (`YYYY-MM-DD HH:mm:ss`), `latitude`, `longitude`, `selfie_file_url`, `notes` | The created Employee Checkin |
| `/api/method/techniti_kiosk_lookup` | GET | `id_number` | `name`, `person_name`, `person_type`, `image_url` |
| `/api/method/techniti_kiosk_punch` | POST | `id_number`, `location`, `device_id`, `selfie_url` | `person_name`, `log_type`, `time`, … |
| `/api/method/next_attendance.api.sign_selfies` | POST | `checkins`: JSON list of Employee Checkin names | `{ checkin: signed_url }` |
| `/api/method/next_attendance.api.serve_selfie` | GET | `f`, `e`, `s` (from a signed URL) | The image |

Upload the selfie first with Frappe's standard `/api/method/upload_file` (`is_private=1`), then pass the returned `file_url` to the punch API.

## Contributing

Pull requests are welcome against the **`develop`** branch.

Server Scripts run in Frappe's restricted sandbox. That means no `import`, and a function defined in the script is not visible inside a generator expression or comprehension. Test script changes on a development site before opening a PR.
