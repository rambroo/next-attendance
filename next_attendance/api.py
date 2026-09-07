"""
Short-lived signed URLs for punch selfies.

Selfies used to be uploaded with ``is_private=0``, which put every check-in
photo — including kiosk photos of students — behind a permanently public,
unauthenticated URL. They are now uploaded as private files.

A private file cannot be rendered directly by React Native's ``<Image>`` on
Android: the native HTTP stack does not attach the Frappe ``sid`` cookie to
image requests, so ``/private/files/...`` comes back 403. Instead of making the
files world-readable, the app asks :func:`sign_selfies` for a short-lived
signed URL and renders that.

The signature is an HMAC over ``(file_url, expiry)`` keyed on the site's
encryption key, so a link cannot be forged, cannot be edited to point at a
different file, and stops working after :data:`SELFIE_URL_TTL` seconds.
"""

import hashlib
import hmac
import mimetypes
import os
import time
from urllib.parse import quote

import frappe
from frappe.utils import get_files_path
from frappe.utils.password import get_encryption_key

#: How long a signed selfie URL stays valid. Long enough to open the day-detail
#: modal and scroll, short enough that a leaked URL is worthless.
SELFIE_URL_TTL = 900  # seconds

#: Only files living in the site's own file directories can ever be served.
_ALLOWED_PREFIXES = ("/private/files/", "/files/")

#: Cap on a single sign_selfies() call, so one request cannot fan out forever.
_MAX_BATCH = 50


# ── Signing ──────────────────────────────────────────────────────────────────


def _sign(file_url: str, expires: int) -> str:
    key = get_encryption_key()
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, f"{file_url}|{expires}".encode(), hashlib.sha256).hexdigest()[:32]


def _signed_url(file_url: str) -> str:
    expires = int(time.time()) + SELFIE_URL_TTL
    return (
        "/api/method/next_attendance.api.serve_selfie"
        f"?f={quote(file_url, safe='')}"
        f"&e={expires}"
        f"&s={_sign(file_url, expires)}"
    )


def _resolve_path(file_url: str) -> str:
    """Map a stored file_url onto a real path, refusing anything outside the
    site's file directories."""
    if not file_url or ".." in file_url or not file_url.startswith(_ALLOWED_PREFIXES):
        raise frappe.PermissionError("Invalid selfie link.")

    base = os.path.realpath(get_files_path(is_private=file_url.startswith("/private/")))
    # Frappe stores files flat, so basename() is both correct and traversal-proof.
    path = os.path.realpath(os.path.join(base, os.path.basename(file_url)))
    if not path.startswith(base + os.sep):
        raise frappe.PermissionError("Invalid selfie link.")
    return path


# ── Endpoints ────────────────────────────────────────────────────────────────


@frappe.whitelist()
def sign_selfies(checkins):
    """Return ``{checkin_name: signed_url}`` for the check-ins the caller may read.

    Check-ins the caller cannot read, and check-ins with no selfie, are simply
    omitted rather than raising — the mobile app renders a placeholder for those.
    """
    names = frappe.parse_json(checkins) if isinstance(checkins, str) else checkins
    if not isinstance(names, (list, tuple)):
        names = [names]

    out = {}
    for name in names[:_MAX_BATCH]:
        if not frappe.has_permission("Employee Checkin", ptype="read", doc=name):
            continue
        file_url = frappe.db.get_value("Employee Checkin", name, "custom_selfie_image")
        if file_url:
            out[name] = _signed_url(file_url)
    return out


@frappe.whitelist(allow_guest=True)
def serve_selfie(f=None, e=None, s=None):
    """Stream a selfie to a caller holding a valid signature.

    ``allow_guest`` is deliberate: the signature *is* the authorisation. It is
    issued only by :func:`sign_selfies`, which enforces read permission on the
    underlying Employee Checkin.
    """
    try:
        expires = int(e)
    except (TypeError, ValueError):
        raise frappe.PermissionError("Invalid selfie link.")

    if expires < int(time.time()):
        raise frappe.PermissionError("This selfie link has expired.")

    if not hmac.compare_digest(_sign(f or "", expires), s or ""):
        raise frappe.PermissionError("Invalid selfie link.")

    path = _resolve_path(f)
    if not os.path.isfile(path):
        raise frappe.DoesNotExistError("Selfie not found.")

    with open(path, "rb") as fh:
        content = fh.read()

    frappe.local.response.filename = os.path.basename(path)
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"
    frappe.local.response.content_type = mimetypes.guess_type(path)[0] or "image/jpeg"
    frappe.local.response.display_content_as = "inline"
