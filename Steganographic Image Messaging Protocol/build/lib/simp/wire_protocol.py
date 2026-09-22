"""Versioned message envelopes carried inside steganographic PNG images."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import re
import uuid

from .steg import StegError, embed_bytes, extract_bytes


PROTOCOL_VERSION = 1
PAYLOAD_PREFIX = b"SIMP/1\0"
LEGACY_PAYLOAD_PREFIXES = (b"LATTICE-WIRE/1\0",)
MAX_TEXT_BYTES = 16 * 1024
MAX_ID_LENGTH = 32
DEFAULT_TTL_SECONDS = 24 * 60 * 60
MAX_TTL_SECONDS = 7 * 24 * 60 * 60
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{0,31}$")
KINDS = {"join", "message", "leave", "ack", "error"}


class ProtocolError(ValueError):
    """Raised when an image does not contain a valid SIMP envelope."""


@dataclass(frozen=True, slots=True)
class Envelope:
    version: int
    kind: str
    message_id: str
    sender: str
    room: str
    sent_at: str
    text: str
    expires_at: str

    def validate(self) -> "Envelope":
        if self.version != PROTOCOL_VERSION:
            raise ProtocolError(f"unsupported protocol version: {self.version}")
        if self.kind not in KINDS:
            raise ProtocolError(f"unsupported message kind: {self.kind!r}")
        if not _IDENTIFIER.fullmatch(self.sender):
            raise ProtocolError(
                "sender must be 1-32 letters, numbers, spaces, dots, dashes, or underscores"
            )
        if not _IDENTIFIER.fullmatch(self.room):
            raise ProtocolError(
                "room must be 1-32 letters, numbers, spaces, dots, dashes, or underscores"
            )
        try:
            uuid.UUID(self.message_id)
        except (ValueError, AttributeError) as exc:
            raise ProtocolError("message_id must be a UUID") from exc
        try:
            parsed_time = datetime.fromisoformat(self.sent_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as exc:
            raise ProtocolError("sent_at must be an ISO-8601 timestamp") from exc
        if parsed_time.tzinfo is None:
            raise ProtocolError("sent_at must include a timezone")
        try:
            parsed_expiry = datetime.fromisoformat(
                self.expires_at.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError) as exc:
            raise ProtocolError("expires_at must be an ISO-8601 timestamp") from exc
        if parsed_expiry.tzinfo is None:
            raise ProtocolError("expires_at must include a timezone")
        lifetime = parsed_expiry - parsed_time
        if lifetime <= timedelta(0):
            raise ProtocolError("expires_at must be later than sent_at")
        if lifetime > timedelta(seconds=MAX_TTL_SECONDS):
            raise ProtocolError("message lifetime cannot exceed 7 days")
        if not isinstance(self.text, str):
            raise ProtocolError("text must be a string")
        if len(self.text.encode("utf-8")) > MAX_TEXT_BYTES:
            raise ProtocolError(f"message text exceeds {MAX_TEXT_BYTES} UTF-8 bytes")
        if self.kind in {"message", "ack", "error"} and not self.text.strip():
            raise ProtocolError(f"{self.kind} text cannot be empty")
        return self

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether this envelope is past its embedded expiry time."""
        current = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return expiry <= current

    def to_payload(self) -> bytes:
        self.validate()
        body = json.dumps(
            asdict(self), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return PAYLOAD_PREFIX + body

    @classmethod
    def from_payload(cls, payload: bytes) -> "Envelope":
        prefix = next(
            (
                candidate
                for candidate in (PAYLOAD_PREFIX, *LEGACY_PAYLOAD_PREFIXES)
                if payload.startswith(candidate)
            ),
            None,
        )
        if prefix is None:
            raise ProtocolError("image contains data, but not a SIMP message")
        try:
            raw = json.loads(payload[len(prefix):].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtocolError("message envelope is not valid UTF-8 JSON") from exc
        if not isinstance(raw, dict):
            raise ProtocolError("message envelope must be a JSON object")
        previous = {"version", "kind", "message_id", "sender", "room", "sent_at", "text"}
        expected = previous | {"expires_at"}
        if set(raw) == previous:
            try:
                sent = datetime.fromisoformat(raw["sent_at"].replace("Z", "+00:00"))
                expiry = sent + timedelta(seconds=DEFAULT_TTL_SECONDS)
                raw["expires_at"] = expiry.isoformat(timespec="seconds").replace(
                    "+00:00", "Z"
                )
            except (KeyError, TypeError, ValueError, AttributeError):
                raw["expires_at"] = raw.get("sent_at", "")
        elif set(raw) != expected:
            raise ProtocolError("message envelope has missing or unknown fields")
        try:
            envelope = cls(**raw)
        except TypeError as exc:
            raise ProtocolError("message envelope fields are invalid") from exc
        return envelope.validate()


def new_envelope(
    kind: str,
    sender: str,
    room: str,
    text: str = "",
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> Envelope:
    """Create and validate a new protocol envelope."""
    if not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ProtocolError("ttl_seconds must be between 1 second and 7 days")
    sent = datetime.now(timezone.utc)
    expires = sent + timedelta(seconds=ttl_seconds)
    envelope = Envelope(
        version=PROTOCOL_VERSION,
        kind=kind,
        message_id=str(uuid.uuid4()),
        sender=sender.strip(),
        room=room.strip(),
        sent_at=sent.isoformat(timespec="seconds").replace("+00:00", "Z"),
        text=text,
        expires_at=expires.isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    return envelope.validate()


def encode_image(carrier_png: bytes, envelope: Envelope) -> bytes:
    """Return a PNG whose LSB payload contains ``envelope``."""
    try:
        return embed_bytes(carrier_png, envelope.to_payload())
    except StegError as exc:
        raise ProtocolError(str(exc)) from exc


def decode_image(image_png: bytes) -> Envelope:
    """Decode and validate a SIMP envelope from PNG bytes."""
    try:
        payload = extract_bytes(image_png)
    except StegError as exc:
        raise ProtocolError(str(exc)) from exc
    return Envelope.from_payload(payload)
