"""SIMP: a monochrome desktop messenger carried entirely by PNG images."""

from __future__ import annotations

import argparse
import base64
import ctypes
from datetime import datetime
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from .relay import RelayServer
from .steg import StegError, read_png_bytes
from .wire_client import WireClient
from .wire_protocol import Envelope, ProtocolError, decode_image, new_envelope


ROOT = Path(__file__).resolve().parent
DISPLAY_FONT = ROOT / "assets/fonts/LibreCaslonText-Regular.ttf"
DEFAULT_CARRIER = ROOT / "assets/plates/carrier-photo-compact.png"

BLACK = "#080808"
INK = "#111111"
WHITE = "#F7F7F4"
PAPER = "#ECECE8"
LIGHT = "#DDDDD8"
MID = "#8A8A84"
DIM = "#565652"
MUTED_LIGHT = "#666661"
MAX_MESSAGE_ROWS = 100


def _register_private_font(path: Path) -> str:
    if sys.platform == "win32" and path.exists():
        try:
            if ctypes.windll.gdi32.AddFontResourceExW(str(path), 0x10, 0):
                return "Libre Caslon Text"
        except (AttributeError, OSError):
            pass
    return "Book Antiqua"


DISPLAY_FACE = _register_private_font(DISPLAY_FONT)


def readable_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def local_time(iso_time: str) -> str:
    try:
        parsed = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%H:%M")
    except ValueError:
        return "--:--"


def local_expiry(iso_time: str) -> str:
    try:
        parsed = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%b %d %H:%M")
    except ValueError:
        return "unknown"


def decode_message_text(image: bytes) -> str:
    """Decode one message PNG and return its concealed text."""
    envelope = decode_image(image)
    if envelope.kind != "message":
        raise ProtocolError("this PNG does not contain a text message")
    return envelope.text


class WireApp:
    def __init__(self, root: tk.Tk, *, demo_name: str = "") -> None:
        self.root = root
        self.events: queue.Queue[tuple] = queue.Queue()
        self.client: WireClient | None = None
        self.local_relay: RelayServer | None = None
        self.carrier_path = DEFAULT_CARRIER
        self.carrier_png = self.carrier_path.read_bytes()
        self.capacity = self._capacity(self.carrier_png)
        self.participants: set[str] = set()
        self.message_records: list[tuple[tk.Widget, tk.PhotoImage | None]] = []
        self._sending = False
        self._connect_generation = 0

        root.title("SIMP - Steganographic Image Messaging Protocol")
        root.geometry("1280x820+60+40")
        root.minsize(880, 620)
        root.configure(bg=BLACK)
        root.option_add("*Font", ("Segoe UI", 10))

        self._build_shell(demo_name)
        self._bind_shortcuts()
        self._set_connection_state(False)
        root.protocol("WM_DELETE_WINDOW", self._close)
        root.after(50, self._poll_events)
        root.after(120, self.name_entry.focus_set)

    def _build_shell(self, demo_name: str) -> None:
        self.sidebar = tk.Frame(self.root, bg=BLACK, width=310)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.main = tk.Frame(self.root, bg=WHITE)
        self.main.pack(side="left", fill="both", expand=True)

        brand = tk.Frame(self.sidebar, bg=BLACK)
        brand.pack(fill="x", padx=28, pady=(20, 20))
        tk.Label(
            brand,
            text="SIMP",
            bg=BLACK,
            fg=WHITE,
            font=(DISPLAY_FACE, 29),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            brand,
            text="STEGANOGRAPHIC IMAGE MESSAGING",
            bg=BLACK,
            fg=MID,
            font=("Consolas", 9),
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(4, 0))

        self.status_canvas = tk.Canvas(
            self.sidebar, width=10, height=10, bg=BLACK, highlightthickness=0
        )
        self.status_canvas.place(x=281, y=39)

        fields = tk.Frame(self.sidebar, bg=BLACK)
        fields.pack(fill="x", padx=28)
        self.name_var = tk.StringVar(value=demo_name)
        self.room_var = tk.StringVar(value="first-room")
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="45873")
        self.name_entry = self._dark_field(fields, "Your name", self.name_var)
        self.room_entry = self._dark_field(fields, "Room", self.room_var)

        network = tk.Frame(fields, bg=BLACK)
        network.pack(fill="x", pady=(0, 12))
        network.grid_columnconfigure(0, weight=1)
        network.grid_columnconfigure(1, weight=0)
        host_wrap = tk.Frame(network, bg=BLACK)
        host_wrap.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.host_entry = self._dark_field(host_wrap, "Relay", self.host_var, compact=True)
        port_wrap = tk.Frame(network, bg=BLACK)
        port_wrap.grid(row=0, column=1, sticky="e")
        self.port_entry = self._dark_field(
            port_wrap, "Port", self.port_var, compact=True, width=7
        )

        self.carrier_button = self._button(
            fields, "Change message image", self.choose_carrier, dark=True
        )
        self.carrier_button.pack(fill="x")
        self.carrier_var = tk.StringVar()
        self.carrier_label = tk.Label(
            fields,
            textvariable=self.carrier_var,
            bg=BLACK,
            fg=MID,
            justify="left",
            anchor="w",
            wraplength=250,
            font=("Consolas", 9),
        )
        self.carrier_label.pack(fill="x", pady=(7, 14))
        self._update_carrier_label()

        self.connect_button = self._button(
            fields, "Connect", self.toggle_connection, primary=True
        )
        self.connect_button.pack(fill="x", ipady=4)
        self.relay_button = self._button(
            fields, "Start relay on this computer", self.start_local_relay, dark=True
        )
        self.relay_button.pack(fill="x", pady=(8, 0))

        rail_bottom = tk.Frame(self.sidebar, bg=BLACK)
        rail_bottom.pack(side="bottom", fill="x", padx=28, pady=16)
        tk.Label(
            rail_bottom,
            text=(
                "Every message is a PNG.\n"
                "Concealed, not encrypted. Relay-readable."
            ),
            bg=BLACK,
            fg=MID,
            justify="left",
            anchor="w",
            font=("Segoe UI", 9),
        ).pack(fill="x")

        self._build_conversation()

    def _build_conversation(self) -> None:
        top = tk.Frame(self.main, bg=WHITE, height=108)
        top.pack(fill="x")
        top.pack_propagate(False)
        title_wrap = tk.Frame(top, bg=WHITE)
        title_wrap.pack(side="left", fill="both", expand=True, padx=36, pady=(18, 12))
        self.room_title = tk.Label(
            title_wrap,
            text="Not connected",
            bg=WHITE,
            fg=INK,
            anchor="w",
            font=(DISPLAY_FACE, 22),
        )
        self.room_title.pack(fill="x")
        self.status_var = tk.StringVar(value="Start or join a relay to begin.")
        self.room_status = tk.Label(
            title_wrap,
            textvariable=self.status_var,
            bg=WHITE,
            fg=DIM,
            anchor="w",
            font=("Segoe UI", 9),
            takefocus=True,
            highlightthickness=1,
            highlightbackground=WHITE,
            highlightcolor=INK,
        )
        self.room_status.pack(fill="x", pady=(3, 0))
        tk.Label(
            top,
            text="PNG FIRST / TEXT ON REQUEST",
            bg=WHITE,
            fg=DIM,
            font=("Consolas", 9),
        ).pack(side="right", padx=36)
        tk.Frame(self.main, height=1, bg=LIGHT).pack(fill="x")

        self.conversation_canvas = tk.Canvas(
            self.main, bg=WHITE, highlightthickness=0, bd=0
        )
        scrollbar = tk.Scrollbar(
            self.main,
            orient="vertical",
            command=self.conversation_canvas.yview,
            relief="flat",
            bd=0,
            width=12,
        )
        self.conversation_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.conversation_canvas.pack(fill="both", expand=True)
        self.message_list = tk.Frame(self.conversation_canvas, bg=WHITE)
        self.message_window = self.conversation_canvas.create_window(
            (0, 0), window=self.message_list, anchor="nw"
        )
        self.message_list.bind("<Configure>", self._sync_scroll_region)
        self.conversation_canvas.bind("<Configure>", self._sync_message_width)
        self.conversation_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.empty_state = tk.Frame(self.message_list, bg=WHITE)
        self.empty_state.pack(fill="both", expand=True, padx=58, pady=100)
        tk.Label(
            self.empty_state,
            text="The image is the message.",
            bg=WHITE,
            fg=INK,
            font=(DISPLAY_FACE, 28),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            self.empty_state,
            text=(
                "Connect two clients to the same room. Each message arrives as a picture. "
                "Choose Reveal beside an image to show its text."
            ),
            bg=WHITE,
            fg=DIM,
            font=("Segoe UI", 11),
            justify="left",
            wraplength=420,
            anchor="w",
        ).pack(fill="x", pady=(12, 0))

        composer = tk.Frame(self.main, bg=PAPER, padx=26, pady=20)
        composer.pack(fill="x", side="bottom")
        input_rule = tk.Frame(composer, bg=INK, padx=1, pady=1)
        input_rule.pack(side="left", fill="both", expand=True, padx=(0, 14))
        self.message_input = tk.Text(
            input_rule,
            width=1,
            height=3,
            wrap="word",
            relief="flat",
            bd=0,
            bg=WHITE,
            fg=INK,
            insertbackground=INK,
            selectbackground=INK,
            selectforeground=WHITE,
            padx=14,
            pady=11,
            font=("Segoe UI", 11),
            undo=True,
        )
        self.message_input.pack(fill="both", expand=True)
        self.message_input.bind("<<Modified>>", self._message_changed)
        action = tk.Frame(composer, bg=PAPER, width=150)
        action.pack(side="right", fill="y")
        action.pack_propagate(False)
        self.send_button = self._button(action, "Send as image", self.send_message, primary=False)
        self.send_button.pack(fill="x", ipady=8)
        self.count_var = tk.StringVar(value="0 B")
        tk.Label(
            action,
            textvariable=self.count_var,
            bg=PAPER,
            fg=DIM,
            anchor="e",
            font=("Consolas", 8),
        ).pack(fill="x", pady=(9, 0))
        self._update_count()

    def _dark_field(
        self,
        parent: tk.Misc,
        label: str,
        variable: tk.StringVar,
        *,
        compact: bool = False,
        width: int | None = None,
    ) -> tk.Entry:
        block = tk.Frame(parent, bg=BLACK)
        block.pack(fill="x", pady=(0, 10 if compact else 12))
        tk.Label(
            block,
            text=label,
            bg=BLACK,
            fg=MID,
            anchor="w",
            font=("Segoe UI Semibold", 8),
        ).pack(fill="x", pady=(0, 4))
        entry = tk.Entry(
            block,
            textvariable=variable,
            bg=BLACK,
            fg=WHITE,
            disabledbackground=BLACK,
            disabledforeground=LIGHT,
            insertbackground=WHITE,
            relief="flat",
            bd=0,
            highlightbackground=DIM,
            highlightcolor=WHITE,
            highlightthickness=1,
            selectbackground=WHITE,
            selectforeground=BLACK,
            font=("Segoe UI", 10),
            width=width or 20,
        )
        entry.pack(fill="x", ipady=6)
        return entry

    def _button(
        self,
        parent: tk.Misc,
        text: str,
        command,
        *,
        primary: bool = False,
        dark: bool = False,
    ) -> tk.Button:
        bg = WHITE if primary else (BLACK if dark else INK)
        fg = BLACK if primary else WHITE
        active_bg = LIGHT if primary else DIM
        disabled_fg = DIM if primary else LIGHT
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            disabledforeground=disabled_fg,
            cursor="hand2",
            highlightbackground=DIM if dark else INK,
            highlightcolor=WHITE if dark else INK,
            highlightthickness=1,
            padx=13,
            pady=8,
            font=("Segoe UI Semibold", 9),
            takefocus=True,
        )

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-Return>", lambda _event: self.send_message())
        self.root.bind("<Control-o>", lambda _event: self.choose_carrier())
        self.root.bind("<Control-k>", lambda _event: self.toggle_connection())
        self.root.bind("<Alt-s>", lambda _event: self.room_status.focus_set())

    def choose_carrier(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose the PNG used for messages",
            filetypes=[("PNG images", "*.png"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            image = Path(path).read_bytes()
            capacity = self._capacity(image)
            if capacity < 1024:
                raise StegError("carrier has less than 1 KB of message capacity")
        except (OSError, StegError) as exc:
            messagebox.showerror("Message image unavailable", str(exc), parent=self.root)
            return
        self.carrier_path = Path(path)
        self.carrier_png = image
        self.capacity = capacity
        self._update_carrier_label()

    @staticmethod
    def _capacity(image: bytes) -> int:
        _width, _height, _channels, pixels = read_png_bytes(image)
        return max(0, len(pixels) // 8 - 8)

    def _update_carrier_label(self) -> None:
        self.carrier_var.set(
            f"{self.carrier_path.name}\n{readable_size(len(self.carrier_png))} image / "
            f"{readable_size(self.capacity)} message capacity"
        )

    def start_local_relay(self) -> None:
        if self.local_relay is not None:
            self._status("Local relay is already running.")
            return
        try:
            port = int(self.port_var.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            return self._status("Port must be a number from 1 to 65535.", error=True)
        relay = RelayServer(self.host_var.get().strip() or "127.0.0.1", port)
        self.local_relay = relay

        def run() -> None:
            try:
                relay.serve_forever()
            except OSError as exc:
                self.events.put(("relay_error", str(exc), relay))

        thread = threading.Thread(target=run, name="simp-local-relay", daemon=True)
        thread.start()
        self._wait_for_relay(thread, relay, attempts=30)
        self.relay_button.configure(state="disabled", text="Starting local relay…")

    def _wait_for_relay(
        self, thread: threading.Thread, relay: RelayServer, attempts: int
    ) -> None:
        if relay.ready.is_set():
            self.relay_button.configure(state="disabled", text="Local relay running")
            self._status(f"Local relay is listening on port {relay.bound_port}.")
            return
        if not thread.is_alive() or attempts <= 0:
            if self.local_relay is relay:
                self.local_relay = None
            self.relay_button.configure(state="normal", text="Start relay on this computer")
            return
        self.root.after(50, self._wait_for_relay, thread, relay, attempts - 1)

    def toggle_connection(self) -> None:
        if self.client and self.client.connected:
            self.client.close()
            self.client = None
            self._set_connection_state(False)
            self._status("Disconnected. Messages stay in this window.")
        else:
            self.connect()

    def connect(self) -> None:
        name = self.name_var.get().strip()
        room = self.room_var.get().strip()
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            return self._status("Port must be a number from 1 to 65535.", error=True)
        self._connect_generation += 1
        generation = self._connect_generation
        client = WireClient(self._incoming_image, self._client_disconnected)
        self.connect_button.configure(state="disabled", text="Connecting…")
        self._status("Encoding a join image and contacting the relay…")

        def work() -> None:
            try:
                result = client.connect(host, port, name, room, self.carrier_png)
            except (OSError, ConnectionError, ProtocolError, ValueError) as exc:
                self.events.put(("connect_error", generation, str(exc)))
            else:
                self.events.put(("connected", generation, client, *result))

        threading.Thread(target=work, name="simp-connect", daemon=True).start()

    def send_message(self) -> str:
        text = self.message_input.get("1.0", "end-1c")
        if not text.strip():
            self._status("Type a message before sending.", error=True)
            return "break"
        if not self.client or not self.client.connected:
            self._status("Connect to a room before sending.", error=True)
            return "break"
        try:
            payload_size = len(
                new_envelope(
                    "message", self.client.name, self.client.room, text
                ).to_payload()
            )
        except ProtocolError as exc:
            self._status(f"Message cannot be sent: {exc}", error=True)
            return "break"
        if payload_size > self.capacity:
            self._status("This message does not fit in the selected carrier.", error=True)
            return "break"
        if self._sending:
            return "break"
        client = self.client
        self._sending = True
        self.send_button.configure(state="disabled", text="Encoding image…")
        self.message_input.configure(state="disabled")

        def work() -> None:
            try:
                image, envelope = client.send_message(text)
            except (OSError, ConnectionError, ProtocolError) as exc:
                self.events.put(("send_error", str(exc)))
            else:
                self.events.put(("sent", image, envelope))

        threading.Thread(target=work, name="simp-send", daemon=True).start()
        return "break"

    def _incoming_image(self, image: bytes, envelope: Envelope) -> None:
        self.events.put(("image", image, envelope))

    def _client_disconnected(self, reason: str) -> None:
        self.events.put(("disconnected", reason))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "connected":
                    _, generation, client, image, envelope = event
                    if generation != self._connect_generation:
                        client.close()
                        continue
                    self.client = client
                    self.participants = {envelope.sender}
                    self._set_connection_state(True)
                    self._append_message(image, envelope, mine=True)
                    self._status("Connected. The join event crossed the wire as a PNG.")
                elif kind == "connect_error":
                    _, generation, message = event
                    if generation == self._connect_generation:
                        self.connect_button.configure(state="normal", text="Connect")
                        self._status(f"Could not connect: {message}", error=True)
                elif kind == "image":
                    _, image, envelope = event
                    self._append_message(image, envelope, mine=False)
                elif kind == "sent":
                    _, image, envelope = event
                    self._sending = False
                    self.message_input.configure(state="normal")
                    self.message_input.delete("1.0", "end")
                    self.message_input.edit_modified(False)
                    self.send_button.configure(text="Send as image")
                    self._append_message(image, envelope, mine=True)
                    self._update_count()
                    self._status(f"Sent {readable_size(len(image))} as one PNG image.")
                    self.message_input.focus_set()
                elif kind == "send_error":
                    _, message = event
                    self._sending = False
                    self.message_input.configure(state="normal")
                    self.send_button.configure(text="Send as image")
                    self._update_count()
                    self._status(f"Message was not sent: {message}", error=True)
                elif kind == "disconnected":
                    _, reason = event
                    self.client = None
                    self._set_connection_state(False)
                    self._status(reason, error=True)
                elif kind == "relay_error":
                    _, message, relay = event
                    if self.local_relay is relay:
                        self.local_relay = None
                    self.relay_button.configure(
                        state="normal", text="Start relay on this computer"
                    )
                    self._status(f"Could not start relay: {message}", error=True)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_events)

    def _append_message(self, image: bytes, envelope: Envelope, *, mine: bool) -> None:
        if self.empty_state.winfo_exists():
            self.empty_state.destroy()
        if envelope.kind == "join":
            self.participants.add(envelope.sender)
        elif envelope.kind == "leave":
            self.participants.discard(envelope.sender)
        self._refresh_room_status()

        if envelope.kind != "message":
            row = tk.Frame(self.message_list, bg=WHITE)
            row.pack(fill="x", padx=38, pady=12)
            thumb = self._thumbnail(image, 42, 30)
            if thumb:
                tk.Label(row, image=thumb, bg=WHITE, bd=0).pack(side="left")
            tk.Frame(row, height=1, bg=LIGHT).pack(
                side="left", fill="x", expand=True, padx=(14, 14)
            )
            tk.Label(
                row,
                text=f"{envelope.sender} / {envelope.kind} image",
                bg=WHITE,
                fg=DIM,
                font=("Segoe UI", 9),
            ).pack(side="left")
            tk.Label(
                row,
                text=local_time(envelope.sent_at),
                bg=WHITE,
                fg=MUTED_LIGHT,
                font=("Consolas", 9),
            ).pack(side="right", padx=(12, 0))
        else:
            row = tk.Frame(self.message_list, bg=WHITE)
            row.pack(fill="x", padx=38, pady=(18, 12))
            message = tk.Frame(row, bg=WHITE)
            message.pack(side="right" if mine else "left", anchor="n")
            meta = tk.Frame(message, bg=WHITE)
            meta.pack(fill="x", pady=(0, 7))
            tk.Label(
                meta,
                text="You" if mine else envelope.sender,
                bg=WHITE,
                fg=INK,
                font=("Segoe UI Semibold", 9),
            ).pack(side="right" if mine else "left")
            tk.Label(
                meta,
                text=(
                    f"{local_time(envelope.sent_at)} · "
                    f"expires {local_expiry(envelope.expires_at)}"
                ),
                bg=WHITE,
                fg=MUTED_LIGHT,
                font=("Consolas", 8),
            ).pack(side="right" if not mine else "left")
            artifact = tk.Frame(message, bg=WHITE)
            artifact.pack(fill="x")
            image_column = tk.Frame(artifact, bg=INK, width=224, height=148)
            image_column.pack(side="right" if mine else "left", anchor="n")
            image_column.pack_propagate(False)
            thumb = self._thumbnail(image, 224, 124)
            if thumb:
                tk.Label(image_column, image=thumb, bg=INK, bd=0).pack(
                    fill="both", expand=True
                )
            tk.Label(
                image_column,
                text=f"PNG  {readable_size(len(image))}",
                bg=INK,
                fg=WHITE,
                font=("Consolas", 8),
                anchor="w",
                padx=9,
            ).pack(fill="x", ipady=3)

            action_column = tk.Frame(artifact, bg=WHITE)
            action_column.pack(
                side="right" if mine else "left",
                anchor="n",
                padx=(0, 12) if mine else (12, 0),
            )
            decoded_label = tk.Label(
                message,
                text="",
                bg=WHITE,
                fg=INK,
                justify="right" if mine else "left",
                anchor="e" if mine else "w",
                wraplength=430,
                font=("Segoe UI", 11),
            )
            decode_button = self._button(action_column, "Reveal", lambda: None)
            decode_hint = tk.Label(
                action_column,
                text="Show decoded text",
                bg=WHITE,
                fg=MUTED_LIGHT,
                font=("Consolas", 8),
            )
            decode_button.configure(
                command=lambda: self._decode_message(
                    envelope.text, decoded_label, decode_button, decode_hint
                )
            )
            decode_button.pack(ipadx=6)
            decode_hint.pack(pady=(7, 0))
        self.message_records.append((row, thumb))
        if len(self.message_records) > MAX_MESSAGE_ROWS:
            oldest, _old_thumb = self.message_records.pop(0)
            oldest.destroy()
        self.root.after_idle(self._scroll_to_bottom)

    def _decode_message(
        self,
        text: str,
        decoded_label: tk.Label,
        decode_button: tk.Button,
        decode_hint: tk.Label,
    ) -> None:
        decoded_label.configure(text=text)
        decoded_label.pack(fill="x", pady=(12, 0))
        decode_button.configure(text="Shown", state="disabled")
        decode_hint.configure(text="Text shown")
        self._status("Text revealed from the validated PNG envelope.")
        self.root.after_idle(self._scroll_to_bottom)

    def _thumbnail(self, image: bytes, max_width: int, max_height: int) -> tk.PhotoImage | None:
        try:
            source = tk.PhotoImage(data=base64.b64encode(image).decode("ascii"))
            ratio = max(source.width() / max_width, source.height() / max_height, 1)
            step = max(1, int(ratio + 0.999))
            return source.subsample(step, step)
        except tk.TclError:
            return None

    def _set_connection_state(self, connected: bool) -> None:
        state = "disabled" if connected else "normal"
        for widget in (
            self.name_entry,
            self.room_entry,
            self.host_entry,
            self.port_entry,
            self.carrier_button,
        ):
            widget.configure(state=state)
        self.connect_button.configure(
            state="normal", text="Disconnect" if connected else "Connect"
        )
        self._update_count()
        self.status_canvas.delete("all")
        self.status_canvas.create_oval(
            1,
            1,
            9,
            9,
            fill=WHITE if connected else DIM,
            outline="",
        )
        self.room_title.configure(
            text=f"{self.room_var.get().strip()} / {self.name_var.get().strip()}"
            if connected
            else "Not connected"
        )
        self._refresh_room_status()

    def _refresh_room_status(self) -> None:
        if self.client and self.client.connected:
            count = len(self.participants)
            noun = "participant" if count == 1 else "participants"
            self.status_var.set(f"{count} {noun} · image transport active")
            self.room_status.configure(fg=DIM)
        else:
            self.status_var.set("Start or join a relay to begin.")
            self.room_status.configure(fg=DIM)

    def _status(self, message: str, *, error: bool = False) -> None:
        self.status_var.set(message)
        self.room_status.configure(fg=INK if error else DIM)
        if error:
            self.root.bell()

    def _message_changed(self, _event=None) -> None:
        if self.message_input.edit_modified():
            self.message_input.edit_modified(False)
            self._update_count()

    def _update_count(self) -> None:
        text = self.message_input.get("1.0", "end-1c")
        text_size = len(text.encode("utf-8"))
        payload_size = 0
        fits = False
        if text.strip():
            try:
                envelope = new_envelope(
                    "message",
                    self.name_var.get().strip() or "User",
                    self.room_var.get().strip() or "room",
                    text,
                )
                payload_size = len(envelope.to_payload())
                fits = payload_size <= self.capacity
            except ProtocolError:
                fits = False
        if text and payload_size:
            verdict = "fits" if fits else "too large"
            self.count_var.set(
                f"{readable_size(text_size)} text / {readable_size(payload_size)} image envelope · {verdict}"
            )
        else:
            self.count_var.set(f"0 B text / {readable_size(self.capacity)} message capacity")
        connected = bool(self.client and self.client.connected)
        self.send_button.configure(
            state="normal" if connected and fits and not self._sending else "disabled"
        )

    def _sync_scroll_region(self, _event=None) -> None:
        self.conversation_canvas.configure(scrollregion=self.conversation_canvas.bbox("all"))

    def _sync_message_width(self, event) -> None:
        self.conversation_canvas.itemconfigure(self.message_window, width=event.width)

    def _scroll_to_bottom(self) -> None:
        self.conversation_canvas.update_idletasks()
        self.conversation_canvas.yview_moveto(1.0)

    def _on_mousewheel(self, event) -> None:
        self.conversation_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _close(self) -> None:
        if self.client:
            self.client.close()
        if self.local_relay:
            self.local_relay.shutdown()
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SIMP - Steganographic Image Messaging Protocol"
    )
    parser.add_argument("--name", default="", help="prefill the client display name")
    args = parser.parse_args(argv)
    root = tk.Tk()
    WireApp(root, demo_name=args.name)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
