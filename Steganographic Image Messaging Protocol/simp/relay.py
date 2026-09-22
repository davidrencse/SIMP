"""Multi-room relay for SIMP steganographic image messages."""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
import socket
import threading
import time

from .transport import TransportError, receive_image, send_image
from .wire_protocol import ProtocolError, decode_image, encode_image, new_envelope


MAX_PARTICIPANTS = 64
MAX_ROOM_PARTICIPANTS = 32
MAX_FRAMES_PER_WINDOW = 30
RATE_WINDOW_SECONDS = 10.0
HANDSHAKE_TIMEOUT_SECONDS = 10.0
IDLE_TIMEOUT_SECONDS = 30 * 60.0


@dataclass(eq=False, slots=True)
class Participant:
    sock: socket.socket
    address: tuple[str, int]
    name: str
    room: str
    join_image: bytes
    send_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, image: bytes) -> None:
        with self.send_lock:
            send_image(self.sock, image)


class RelayServer:
    """Threaded relay that routes validated PNG frames to room participants."""

    def __init__(self, host: str = "127.0.0.1", port: int = 45873) -> None:
        self.host = host
        self.port = port
        self.bound_port = port
        self.ready = threading.Event()
        self._listener: socket.socket | None = None
        self._participants: set[Participant] = set()
        self._lock = threading.RLock()
        self._stopping = threading.Event()
        self._connection_slots = threading.BoundedSemaphore(MAX_PARTICIPANTS)

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self.host, self.port))
            listener.listen(MAX_PARTICIPANTS)
            listener.settimeout(0.5)
            self._listener = listener
            self.bound_port = listener.getsockname()[1]
            self.ready.set()
            print(f"SIMP relay listening on {self.host}:{self.bound_port}", flush=True)
            while not self._stopping.is_set():
                try:
                    sock, address = listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not self._connection_slots.acquire(blocking=False):
                    sock.close()
                    continue
                sock.settimeout(HANDSHAKE_TIMEOUT_SECONDS)
                threading.Thread(
                    target=self._run_connection,
                    args=(sock, address),
                    name=f"simp-peer-{address[0]}-{address[1]}",
                    daemon=True,
                ).start()
        self.ready.set()

    def _run_connection(self, sock: socket.socket, address: tuple[str, int]) -> None:
        try:
            self._handle_connection(sock, address)
        finally:
            self._connection_slots.release()

    def shutdown(self) -> None:
        self._stopping.set()
        listener = self._listener
        if listener:
            try:
                listener.close()
            except OSError:
                pass
        with self._lock:
            participants = list(self._participants)
            self._participants.clear()
        for participant in participants:
            try:
                participant.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            participant.sock.close()

    def _handle_connection(self, sock: socket.socket, address: tuple[str, int]) -> None:
        participant: Participant | None = None
        announced_leave = False
        registered = False
        try:
            first_image = receive_image(sock)
            if first_image is None:
                return
            join = decode_image(first_image)
            if join.kind != "join":
                error = new_envelope(
                    "error", "relay", join.room, "First image must contain a join request."
                )
                send_image(sock, encode_image(first_image, error))
                return
            if join.is_expired():
                error = new_envelope(
                    "error", "relay", join.room, "The join image has expired."
                )
                send_image(sock, encode_image(first_image, error))
                return
            participant = Participant(sock, address, join.sender, join.room, first_image)
            rejection: str | None = None
            with self._lock:
                room_count = sum(peer.room == join.room for peer in self._participants)
                if len(self._participants) >= MAX_PARTICIPANTS:
                    rejection = "The relay is at its connection limit."
                elif room_count >= MAX_ROOM_PARTICIPANTS:
                    rejection = "This room is full."
                elif any(
                    peer.room == join.room and peer.name.casefold() == join.sender.casefold()
                    for peer in self._participants
                ):
                    rejection = (
                        "That display name is already in this room. Choose another name."
                    )
                else:
                    existing = [
                        peer for peer in self._participants if peer.room == join.room
                    ]
                    self._participants.add(participant)
                    registered = True
            if rejection:
                error = new_envelope("error", "relay", join.room, rejection)
                participant.send(encode_image(first_image, error))
                return
            accepted = new_envelope(
                "ack", "relay", join.room, f"Joined {join.room} as {join.sender}."
            )
            participant.send(encode_image(first_image, accepted))
            sock.settimeout(IDLE_TIMEOUT_SECONDS)
            for peer in existing:
                participant.send(peer.join_image)
            self._broadcast(participant.room, first_image, exclude=participant)

            frame_times: deque[float] = deque()
            while not self._stopping.is_set():
                image = receive_image(sock)
                if image is None:
                    break
                now = time.monotonic()
                while frame_times and now - frame_times[0] > RATE_WINDOW_SECONDS:
                    frame_times.popleft()
                if len(frame_times) >= MAX_FRAMES_PER_WINDOW:
                    error = new_envelope(
                        "error",
                        "relay",
                        participant.room,
                        "Message rate limit reached. Reconnect after a short pause.",
                    )
                    participant.send(encode_image(image, error))
                    break
                frame_times.append(now)
                envelope = decode_image(image)
                if envelope.sender != participant.name or envelope.room != participant.room:
                    raise ProtocolError("sender or room changed during the connection")
                if envelope.is_expired():
                    error = new_envelope(
                        "error",
                        "relay",
                        participant.room,
                        "This image message has expired and was not forwarded.",
                    )
                    participant.send(encode_image(image, error))
                    break
                if envelope.kind not in {"message", "leave"}:
                    error = new_envelope(
                        "error",
                        "relay",
                        participant.room,
                        f"Clients cannot send {envelope.kind} control images.",
                    )
                    participant.send(encode_image(image, error))
                    break
                self._broadcast(participant.room, image, exclude=participant)
                if envelope.kind == "leave":
                    announced_leave = True
                    break
        except (OSError, TransportError, ProtocolError):
            pass
        finally:
            if participant is not None and registered:
                with self._lock:
                    self._participants.discard(participant)
                if not announced_leave and not self._stopping.is_set():
                    try:
                        leave = new_envelope(
                            "leave",
                            participant.name,
                            participant.room,
                            f"{participant.name} disconnected.",
                        )
                        leave_image = encode_image(participant.join_image, leave)
                        self._broadcast(participant.room, leave_image, exclude=participant)
                    except ProtocolError:
                        pass
            try:
                sock.close()
            except OSError:
                pass

    def _broadcast(
        self, room: str, image: bytes, *, exclude: Participant | None = None
    ) -> None:
        with self._lock:
            recipients = [
                peer for peer in self._participants if peer.room == room and peer is not exclude
            ]
        for peer in recipients:
            try:
                peer.send(image)
            except (OSError, TransportError):
                try:
                    peer.sock.close()
                except OSError:
                    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Relay SIMP messages, each carried by a PNG image."
    )
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind")
    parser.add_argument("--port", default=45873, type=int, help="TCP port to bind")
    args = parser.parse_args(argv)
    server = RelayServer(args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping relay.")
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
