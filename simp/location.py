"""Optional, approximate location lookup for image messages."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .wire_protocol import MAX_LOCATION_BYTES


LOOKUP_URL = "https://ipapi.co/json/"
MAX_RESPONSE_BYTES = 16 * 1024


class LocationError(ValueError):
    """The approximate location could not be obtained."""


def approximate_location() -> str:
    """Return a city/region/country label from the user's public IP address.

    This sends one HTTPS request to ipapi.co. Call only after the user opts in.
    No IP address or coordinates are added to the SIMP envelope.
    """
    request = Request(LOOKUP_URL, headers={"User-Agent": "SIMP/0.1 location lookup"})
    try:
        with urlopen(request, timeout=5) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise LocationError("Location lookup failed. Check your connection and try again.") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise LocationError("Location service returned too much data.")
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocationError("Location service returned an invalid response.") from exc
    if not isinstance(data, dict) or data.get("error"):
        raise LocationError("Location service could not determine your area.")
    parts = [data.get("city"), data.get("region"), data.get("country_name")]
    parts = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    if not parts:
        raise LocationError("Location service could not determine your area.")
    location = ", ".join(dict.fromkeys(parts))
    if len(location.encode("utf-8")) > MAX_LOCATION_BYTES or any(
        ord(char) < 32 or ord(char) == 127 for char in location
    ):
        raise LocationError("Location service returned an invalid place name.")
    return location
