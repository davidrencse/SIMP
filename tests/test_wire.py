from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import socket
from pathlib import Path
import struct
import threading
import time
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]

from simp.relay import RelayServer
from simp.chat import decode_message_text
from simp.steg import MAX_DIMENSION, SIGNATURE, StegError, embed_bytes, extract_bytes, read_png_bytes
from simp.transport import TransportError, receive_image, send_image
from simp.wire_client import WireClient
from simp.wire_protocol import (
    PAYLOAD_PREFIX,
    Envelope,
    ProtocolError,
    decode_image,
    encode_image,
    new_envelope,
)


CARRIER = (ROOT / "simp/assets/plates/carrier-photo-compact.png").read_bytes()


def png_chunk(kind: bytes, payload: bytes, *, crc: int | None = None) -> bytes:
    checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF if crc is None else crc
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def minimal_png(raw_scanline: bytes, *, width: int = 1, height: int = 1) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        SIGNATURE
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw_scanline))
        + png_chunk(b"IEND", b"")
    )


def wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


class StegMemoryTests(unittest.TestCase):
    def test_embed_and_extract_bytes(self) -> None:
        payload = "two clients, one image protocol".encode()
        encoded = embed_bytes(CARRIER, payload)
        self.assertTrue(encoded.startswith(SIGNATURE))
        self.assertEqual(extract_bytes(encoded), payload)
        self.assertNotEqual(encoded, CARRIER)

    def test_rejects_truncated_png_chunk_cleanly(self) -> None:
        malformed = SIGNATURE + struct.pack(">I", 40) + b"IDATshort"
        with self.assertRaisesRegex(StegError, "truncated chunk"):
            read_png_bytes(malformed)

    def test_rejects_bad_png_crc(self) -> None:
        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
        malformed = SIGNATURE + png_chunk(b"IHDR", ihdr, crc=0) + png_chunk(b"IEND", b"")
        with self.assertRaisesRegex(StegError, "bad CRC"):
            read_png_bytes(malformed)

    def test_rejects_unknown_png_filter(self) -> None:
        with self.assertRaisesRegex(StegError, "unsupported filter type 5"):
            read_png_bytes(minimal_png(b"\x05\x00"))

    def test_rejects_oversized_dimensions_before_decompression(self) -> None:
        malformed = minimal_png(b"", width=MAX_DIMENSION + 1)
        with self.assertRaisesRegex(StegError, "maximum"):
            read_png_bytes(malformed)


class ProtocolTests(unittest.TestCase):
    def test_envelope_round_trip_through_image(self) -> None:
        original = new_envelope("message", "Alice", "first-room", "Hello, Bob.")
        image = encode_image(CARRIER, original)
        self.assertEqual(decode_image(image), original)

    def test_rejects_plain_steg_payload(self) -> None:
        image = embed_bytes(CARRIER, b"not a wire envelope")
        with self.assertRaises(ProtocolError):
            decode_image(image)

    def test_decodes_legacy_lattice_envelope(self) -> None:
        original = new_envelope("message", "Alice", "first-room", "Still readable.")
        current_payload = original.to_payload()
        legacy_payload = b"LATTICE-WIRE/1\0" + current_payload[len(b"SIMP/1\0"):]
        image = embed_bytes(CARRIER, legacy_payload)
        self.assertEqual(decode_image(image), original)

    def test_old_envelope_without_expiry_remains_readable(self) -> None:
        original = new_envelope("message", "Alice", "first-room", "Older format.")
        raw = json.loads(original.to_payload()[len(PAYLOAD_PREFIX):].decode("utf-8"))
        del raw["expires_at"]
        payload = PAYLOAD_PREFIX + json.dumps(raw, separators=(",", ":")).encode("utf-8")

        decoded = decode_image(embed_bytes(CARRIER, payload))

        self.assertEqual(decoded.text, "Older format.")
        self.assertTrue(decoded.expires_at)

    def test_rejects_oversize_message(self) -> None:
        with self.assertRaises(ProtocolError):
            new_envelope("message", "Alice", "first-room", "x" * (16 * 1024 + 1))

    def test_message_text_is_revealed_from_the_png(self) -> None:
        message = new_envelope("message", "Alice", "first-room", "Decode on demand.")
        image = encode_image(CARRIER, message)
        self.assertEqual(decode_message_text(image), "Decode on demand.")

    def test_decode_button_helper_rejects_non_message_images(self) -> None:
        join = new_envelope("join", "Alice", "first-room", "Alice joined.")
        image = encode_image(CARRIER, join)
        with self.assertRaisesRegex(ProtocolError, "does not contain a text message"):
            decode_message_text(image)


class TransportTests(unittest.TestCase):
    def test_socket_frame_round_trip(self) -> None:
        left, right = socket.socketpair()
        try:
            sender = threading.Thread(target=send_image, args=(left, CARRIER))
            sender.start()
            self.assertEqual(receive_image(right), CARRIER)
            sender.join(timeout=1)
        finally:
            left.close()
            right.close()

    def test_rejects_non_png(self) -> None:
        left, right = socket.socketpair()
        try:
            with self.assertRaises(TransportError):
                send_image(left, b"plain text")
        finally:
            left.close()
            right.close()


class RelayIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = RelayServer("127.0.0.1", 0)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.assertTrue(self.server.ready.wait(2), "relay did not start")
        self.received_a: list[tuple[bytes, object]] = []
        self.received_b: list[tuple[bytes, object]] = []
        self.disconnected: list[str] = []
        self.a = WireClient(lambda i, e: self.received_a.append((i, e)), self.disconnected.append)
        self.b = WireClient(lambda i, e: self.received_b.append((i, e)), self.disconnected.append)
        self.c: WireClient | None = None

    def tearDown(self) -> None:
        self.a.close(announce=False)
        self.b.close(announce=False)
        if self.c:
            self.c.close(announce=False)
        self.server.shutdown()
        self.server_thread.join(timeout=2)

    def test_two_clients_exchange_an_image_message(self) -> None:
        self.a.connect("127.0.0.1", self.server.bound_port, "Alice", "test-room", CARRIER)
        self.b.connect("127.0.0.1", self.server.bound_port, "Bob", "test-room", CARRIER)

        self.assertTrue(
            wait_for(
                lambda: any(envelope.kind == "join" for _, envelope in self.received_a)
                and any(envelope.sender == "Alice" for _, envelope in self.received_b)
            ),
            "clients did not receive image-carried join events",
        )

        sent_image, sent_envelope = self.a.send_message("The decoded text is readable.")
        self.assertTrue(
            wait_for(
                lambda: any(
                    envelope.message_id == sent_envelope.message_id
                    for _, envelope in self.received_b
                )
            ),
            "Bob did not receive Alice's encoded PNG",
        )
        received_image = next(
            image
            for image, envelope in self.received_b
            if envelope.message_id == sent_envelope.message_id
        )
        self.assertEqual(received_image, sent_image)
        self.assertTrue(received_image.startswith(SIGNATURE))
        self.assertEqual(decode_image(received_image).text, "The decoded text is readable.")

    def test_room_isolation(self) -> None:
        self.a.connect("127.0.0.1", self.server.bound_port, "Alice", "room-a", CARRIER)
        self.b.connect("127.0.0.1", self.server.bound_port, "Bob", "room-b", CARRIER)
        _image, envelope = self.a.send_message("Only room A should see this.")
        time.sleep(0.25)
        self.assertFalse(
            any(item.message_id == envelope.message_id for _, item in self.received_b)
        )

    def test_three_clients_receive_the_same_png(self) -> None:
        received_c: list[tuple[bytes, object]] = []
        self.c = WireClient(lambda i, e: received_c.append((i, e)), self.disconnected.append)
        self.a.connect("127.0.0.1", self.server.bound_port, "Alice", "group-room", CARRIER)
        self.b.connect("127.0.0.1", self.server.bound_port, "Bob", "group-room", CARRIER)
        self.c.connect("127.0.0.1", self.server.bound_port, "Carol", "group-room", CARRIER)
        sent_image, envelope = self.a.send_message("Three-way delivery.")
        self.assertTrue(
            wait_for(
                lambda: any(e.message_id == envelope.message_id for _, e in self.received_b)
                and any(e.message_id == envelope.message_id for _, e in received_c)
            )
        )
        bob_image = next(i for i, e in self.received_b if e.message_id == envelope.message_id)
        carol_image = next(i for i, e in received_c if e.message_id == envelope.message_id)
        self.assertEqual(bob_image, sent_image)
        self.assertEqual(carol_image, sent_image)

    def test_duplicate_name_returns_actionable_error(self) -> None:
        self.a.connect("127.0.0.1", self.server.bound_port, "Alice", "same-room", CARRIER)
        with self.assertRaisesRegex(ConnectionError, "already in this room"):
            self.b.connect(
                "127.0.0.1", self.server.bound_port, "alice", "same-room", CARRIER
            )

    def test_client_cannot_spoof_relay_control_images(self) -> None:
        self.a.connect("127.0.0.1", self.server.bound_port, "Alice", "test-room", CARRIER)
        self.b.connect("127.0.0.1", self.server.bound_port, "Bob", "test-room", CARRIER)
        forged = new_envelope("ack", "Alice", "test-room", "Forged relay control.")
        forged_image = encode_image(CARRIER, forged)

        self.a._send_encoded(forged_image)

        self.assertTrue(
            wait_for(lambda: any("cannot send ack" in reason for reason in self.disconnected)),
            "sender did not receive an actionable control-frame rejection",
        )
        self.assertFalse(
            any(envelope.message_id == forged.message_id for _, envelope in self.received_b),
            "forged control image was forwarded to another client",
        )

    def test_expired_message_is_not_forwarded(self) -> None:
        self.a.connect("127.0.0.1", self.server.bound_port, "Alice", "test-room", CARRIER)
        self.b.connect("127.0.0.1", self.server.bound_port, "Bob", "test-room", CARRIER)
        now = datetime.now(timezone.utc)
        expired = Envelope(
            version=1,
            kind="message",
            message_id="d211e664-3389-455a-95d6-03f12c08e5ac",
            sender="Alice",
            room="test-room",
            sent_at=(now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
            text="Too late.",
            expires_at=(now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        )
        expired_image = encode_image(CARRIER, expired)

        self.a._send_encoded(expired_image)

        self.assertTrue(
            wait_for(lambda: any("expired" in reason for reason in self.disconnected)),
            "sender did not receive the expiry rejection",
        )
        self.assertFalse(
            any(envelope.message_id == expired.message_id for _, envelope in self.received_b),
            "expired message was forwarded",
        )


if __name__ == "__main__":
    unittest.main()
