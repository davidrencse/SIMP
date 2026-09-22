"""Length-framed socket transport for PNG-only SIMP messages."""

from __future__ import annotations

import socket
import struct

from .steg import SIGNATURE


MAX_IMAGE_BYTES = 32 * 1024 * 1024
_LENGTH = struct.Struct(">I")


class TransportError(ConnectionError):
    """Raised when a peer sends an invalid or incomplete transport frame."""


def send_image(sock: socket.socket, image_png: bytes) -> None:
    """Send one PNG frame with a four-byte network-order length prefix."""
    if not image_png.startswith(SIGNATURE):
        raise TransportError("outgoing frame is not a PNG image")
    if len(image_png) > MAX_IMAGE_BYTES:
        raise TransportError(f"PNG exceeds the {MAX_IMAGE_BYTES}-byte transport limit")
    sock.sendall(_LENGTH.pack(len(image_png)) + image_png)


def receive_image(sock: socket.socket) -> bytes | None:
    """Receive one PNG frame; return ``None`` for a cleanly closed connection."""
    header = _receive_exact(sock, _LENGTH.size, allow_eof=True)
    if header is None:
        return None
    (size,) = _LENGTH.unpack(header)
    if size < len(SIGNATURE) or size > MAX_IMAGE_BYTES:
        raise TransportError(f"invalid PNG frame length: {size}")
    image = _receive_exact(sock, size)
    if image is None or not image.startswith(SIGNATURE):
        raise TransportError("received frame is not a PNG image")
    return image


def _receive_exact(
    sock: socket.socket, size: int, *, allow_eof: bool = False
) -> bytes | None:
    chunks = bytearray()
    while len(chunks) < size:
        try:
            chunk = sock.recv(size - len(chunks))
        except OSError as exc:
            raise TransportError(str(exc)) from exc
        if not chunk:
            if allow_eof and not chunks:
                return None
            raise TransportError("connection closed during a PNG frame")
        chunks.extend(chunk)
    return bytes(chunks)
