"""Google Calendar read-only untuk DogiPet dengan OAuth desktop + PKCE."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser


CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"
GOOGLE_CLIENT_KEY = "google_calendar_client"
GOOGLE_TOKEN_KEY = "google_calendar_token"


class CalendarIntegrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime | None
    all_day: bool
    html_link: str

    def local_start(self) -> datetime:
        return self.start.astimezone()

    def display(self) -> str:
        local = self.local_start()
        when = local.strftime("%d %b  SEHARIAN") if self.all_day \
            else local.strftime("%d %b  %H:%M")
        return f"{when}  /  {self.title}"


def load_google_client_config(path: str | Path) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        config = payload.get("installed")
    except Exception as exc:
        raise CalendarIntegrationError("File kredensial Google tidak valid.") from exc
    required = ("client_id", "client_secret", "auth_uri", "token_uri")
    if not isinstance(config, dict) or any(not config.get(key) for key in required):
        raise CalendarIntegrationError(
            "Gunakan OAuth Client JSON dengan tipe aplikasi Desktop."
        )
    return {key: config[key] for key in required}


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_authorization_url(
    config: dict, redirect_uri: str, state: str, challenge: str
) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": CALENDAR_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{config['auth_uri']}?{query}"


class _OAuthCallbackServer(HTTPServer):
    result: dict | None = None


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - nama metode ditentukan BaseHTTPRequestHandler
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        self.server.result = {key: values[0] for key, values in query.items()}
        body = (
            "<html><body style='font-family:sans-serif;padding:32px'>"
            "<h2>DogiPet terhubung.</h2>"
            "<p>Kamu boleh menutup tab ini dan kembali ke DogiPet.</p>"
            "</body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def _decode_json_response(response) -> dict:
    return json.loads(response.read().decode("utf-8"))


def _event_datetime(raw: dict, *, end=False) -> tuple[datetime, bool]:
    if raw.get("dateTime"):
        value = str(raw["dateTime"]).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed, False
    if raw.get("date"):
        parsed_date = date.fromisoformat(str(raw["date"]))
        # Agenda sehari penuh diingatkan pada 09:00 waktu lokal, bukan tengah
        # malam. Untuk end date Google (eksklusif), jam tidak berpengaruh.
        hour = 23 if end else 9
        return datetime.combine(
            parsed_date, datetime_time(hour=hour), tzinfo=datetime.now().astimezone().tzinfo
        ), True
    raise CalendarIntegrationError("Agenda Google tidak memiliki waktu mulai.")


def parse_google_event(raw: dict) -> CalendarEvent:
    start, all_day = _event_datetime(raw.get("start") or {})
    end_raw = raw.get("end") or {}
    try:
        end, _ = _event_datetime(end_raw, end=True)
    except CalendarIntegrationError:
        end = None
    return CalendarEvent(
        id=str(raw.get("id") or raw.get("iCalUID") or ""),
        title=str(raw.get("summary") or "Agenda tanpa judul"),
        start=start,
        end=end,
        all_day=all_day,
        html_link=str(raw.get("htmlLink") or ""),
    )


def reminder_due(
    event: CalendarEvent,
    now: datetime,
    lead_minutes: int,
    reminded_ids: set[str] | None = None,
) -> bool:
    if reminded_ids and event.id in reminded_ids:
        return False
    current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    delta = (event.start.astimezone(current.tzinfo) - current).total_seconds()
    return 0 <= delta <= max(1, lead_minutes) * 60


class GoogleCalendarIntegration:
    """OAuth dan pengambilan agenda memakai penyimpanan terenkripsi."""

    def __init__(self, secure_store, opener=urllib.request.urlopen):
        self.store = secure_store
        self.opener = opener

    def connected(self) -> bool:
        token = self.store.get(GOOGLE_TOKEN_KEY, {}) or {}
        client = self.store.get(GOOGLE_CLIENT_KEY, {}) or {}
        return bool(client.get("client_id") and (
            token.get("access_token") or token.get("refresh_token")
        ))

    def import_client(self, path: str | Path) -> dict:
        config = load_google_client_config(path)
        self.store.set(GOOGLE_CLIENT_KEY, config)
        return config

    def _post_form(self, url: str, values: dict) -> dict:
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(values).encode("ascii"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=60) as response:
                return _decode_json_response(response)
        except urllib.error.HTTPError as exc:
            try:
                message = _decode_json_response(exc).get("error_description")
            except Exception:
                message = None
            raise CalendarIntegrationError(
                message or f"Google menolak autentikasi ({exc.code})."
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise CalendarIntegrationError("Tidak dapat terhubung ke Google.") from exc

    def authorize(self, timeout_seconds: int = 180) -> None:
        config = self.store.get(GOOGLE_CLIENT_KEY, {}) or {}
        if not config.get("client_id"):
            raise CalendarIntegrationError("File kredensial Google belum dipilih.")

        server = _OAuthCallbackServer(("127.0.0.1", 0), _OAuthCallbackHandler)
        redirect_uri = f"http://127.0.0.1:{server.server_port}/"
        verifier = secrets.token_urlsafe(64)
        state = secrets.token_urlsafe(24)
        url = build_authorization_url(
            config, redirect_uri, state, pkce_challenge(verifier)
        )
        webbrowser.open(url)
        server.timeout = 1.0
        deadline = time.time() + timeout_seconds
        try:
            while server.result is None and time.time() < deadline:
                server.handle_request()
        finally:
            server.server_close()
        result = server.result or {}
        if result.get("error"):
            raise CalendarIntegrationError("Izin Google Calendar dibatalkan.")
        if result.get("state") != state or not result.get("code"):
            raise CalendarIntegrationError("Login Google tidak selesai atau kedaluwarsa.")

        token = self._post_form(
            config["token_uri"],
            {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": result["code"],
                "code_verifier": verifier,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        if not token.get("access_token"):
            raise CalendarIntegrationError("Google tidak memberikan access token.")
        token["expires_at"] = time.time() + float(token.get("expires_in", 3600))
        self.store.set(GOOGLE_TOKEN_KEY, token)

    def _valid_token(self) -> dict:
        token = self.store.get(GOOGLE_TOKEN_KEY, {}) or {}
        if token.get("access_token") and float(token.get("expires_at", 0)) > time.time() + 60:
            return token
        if not token.get("refresh_token"):
            raise CalendarIntegrationError("Hubungkan ulang akun Google Calendar.")
        config = self.store.get(GOOGLE_CLIENT_KEY, {}) or {}
        refreshed = self._post_form(
            config.get("token_uri", "https://oauth2.googleapis.com/token"),
            {
                "client_id": config.get("client_id", ""),
                "client_secret": config.get("client_secret", ""),
                "refresh_token": token["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        if not refreshed.get("access_token"):
            raise CalendarIntegrationError("Token Google tidak dapat diperbarui.")
        refreshed["refresh_token"] = token["refresh_token"]
        refreshed["expires_at"] = time.time() + float(refreshed.get("expires_in", 3600))
        self.store.set(GOOGLE_TOKEN_KEY, refreshed)
        return refreshed

    def upcoming(self, days: int = 7, max_results: int = 12) -> list[CalendarEvent]:
        token = self._valid_token()
        now = datetime.now(timezone.utc)
        query = urllib.parse.urlencode(
            {
                "timeMin": now.isoformat().replace("+00:00", "Z"),
                "timeMax": (now + timedelta(days=days)).isoformat().replace("+00:00", "Z"),
                "maxResults": max_results,
                "singleEvents": "true",
                "orderBy": "startTime",
            }
        )
        request = urllib.request.Request(
            f"{CALENDAR_API}/calendars/primary/events?{query}",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        try:
            with self.opener(request, timeout=45) as response:
                payload = _decode_json_response(response)
        except urllib.error.HTTPError as exc:
            raise CalendarIntegrationError(
                f"Agenda Google gagal dimuat ({exc.code})."
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise CalendarIntegrationError("Tidak dapat mengambil agenda Google.") from exc
        events = []
        for item in payload.get("items", []):
            if item.get("status") == "cancelled":
                continue
            try:
                events.append(parse_google_event(item))
            except CalendarIntegrationError:
                continue
        return sorted(events, key=lambda event: event.start)

    def disconnect(self) -> None:
        self.store.delete(GOOGLE_TOKEN_KEY)
