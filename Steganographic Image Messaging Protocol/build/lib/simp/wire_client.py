"""Reusable network client for the SIMP image-message protocol."""

from __future__ import annotations

import socket
import threading
from typing import Callable

from .transport import TransportError, receive_image, send_image
from .wire_protocol import Envelope, ProtocolError, decode_image, encode_image, new_envelope


ImageCallback = Callable[[bytes, Envelope], None]
DisconnectCallback = Callable[[str], None]


class WireClient:
    """A connected participant that sends and receives only encoded PNG frames."""

    def __init__(
        self,
        on_image: ImageCallback,
        on_disconnect: DisconnectCallback,
    ) -> None:
        self.on_image = on_image
        self.on_disconnect = on_disconnect
        self.name = ""
        self.room = ""
        self.carrier_png = b""
        self._socket: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._closing = threading.Event()
        self._receiver: threading.Thread | None = None

    @property
    def connected(self) -> bool:
        return self._socket is not None and not self._closing.is_set()

    def connect(
        self,
        host: str,
        port: int,
        name: str,
        room: str,
        carrier_png: bytes,
        *,
        timeout: float = 6.0,
    ) -> tuple[bytes, Envelope]:
        if self.connected:
            raise ConnectionError("client is already connected")
        join = new_envelope("join", name, room, f"{name.strip()} joined the room.")
        join_image = encode_image(carrier_png, join)
        sock = socket.create_connection((host, port), timeout=timeout)
        self.name = join.sender
        self.room = join.room
        self.carrier_png = carrier_png
        self._socket = sock
        self._closing.clear()
        try:
            self._send_encoded(join_image)
            response_image = receive_image(sock)
            if response_image is None:
                raise ConnectionError("relay closed before accepting the join image")
            response = decode_image(response_image)
            if response.room != join.room:
                raise ConnectionError("relay acknowledgement named a different room")
            if response.is_expired():
                raise ConnectionError("relay acknowledgement has expired")
            if response.kind == "error":
                raise ConnectionError(response.text)
            if response.kind != "ack":
                raise ConnectionError("relay did not acknowledge the join image")
        except Exception:
            self._socket = None
            sock.close()
            raise
        sock.settimeout(None)
        self._receiver = threading.Thread(
            target=self._receive_loop, name=f"simp-recv-{self.name}", daemon=True
        )
        self._receiver.start()
        return join_image, join

    def send_message(self, text: str) -> tuple[bytes, Envelope]:
        if not self.connected:
            raise ConnectionError("connect before sending a message")
        envelope = new_envelope("message", self.name, self.room, text)
        image = encode_image(self.carrier_png, envelope)
        self._send_encoded(image)
        return image, envelope

    def close(self, *, announce: bool = True) -> None:
        sock = self._socket
        if sock is None:
            return
        if announce and not self._closing.is_set():
            try:
                leave = new_envelope(
                    "leave", self.name, self.room, f"{self.name} left the room."
                )
                self._send_encoded(encode_image(self.carrier_png, leave))
            except (OSError, ConnectionError, ProtocolError, TransportError):
                pass
        self._closing.set()
        self._socket = None
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()

    def _send_encoded(self, image: bytes) -> None:
        sock = self._socket
        if sock is None:
            raise ConnectionError("not connected")
        with self._send_lock:
            send_image(sock, image)

    def _receive_loop(self) -> None:
        reason = "The relay closed the connection."
        try:
            while not self._closing.is_set():
                sock = self._socket
                if sock is None:
                    return
                image = receive_image(sock)
                if image is None:
                    break
                envelope = decode_image(image)
                if envelope.is_expired():
                    raise ProtocolError("received an expired image envelope")
                if envelope.kind == "error" and envelope.sender == "relay":
                    raise ProtocolError(envelope.text)
                if envelope.kind == "ack":
                    raise ProtocolError("unexpected acknowledgement from relay")
                self.on_image(image, envelope)
        except (OSError, TransportError, ProtocolError) as exc:
            reason = f"Connection ended: {exc}"
        finally:
            was_closing = self._closing.is_set()
            self.close(announce=False)
            if not was_closing:
                self.on_disconnect(reason)
