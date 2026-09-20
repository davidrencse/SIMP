"""Lattice: a local desktop UI for safe PNG steganography.

The interface only embeds and extracts bytes. Recovered data is never executed.
"""

from __future__ import annotations

import argparse
import ctypes
from fractions import Fraction
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from steg import StegError, embed, extract, read_png


ROOT = Path(__file__).resolve().parent
DISPLAY_FONT = ROOT / "assets/fonts/LibreCaslonText-Regular.ttf"
SOURCE_PLATE = ROOT / "assets/plates/carrier-photo.png"
SAMPLE_PLATE = ROOT / "assets/plates/carrier-photo-preview.png"
COMPACT_PLATE = ROOT / "assets/plates/carrier-photo-compact.png"
DOCKET_PLATE = ROOT / "assets/plates/carrier-photo-docket.png"

PAPER = "#E7E6DD"
PAPER_LIGHT = "#F3F1E9"
INK = "#26241F"
MUTED = "#595750"
RULE = "#AAA89F"
SAGE = "#75877B"
SAGE_DARK = "#53685C"
BRICK = "#A74838"
BRICK_ACTIVE = "#8C382D"
WHITE = "#FBFAF5"
ERROR = "#8E2F2A"
def _register_private_font(path: Path) -> bool:
    """Make a bundled font available to this process without installing it."""
    if sys.platform != "win32" or not path.exists():
        return False
    try:
        return bool(ctypes.windll.gdi32.AddFontResourceExW(str(path), 0x10, 0))
    except (AttributeError, OSError):
        return False


DISPLAY_FACE = "Libre Caslon Text" if _register_private_font(DISPLAY_FONT) else "Book Antiqua"
DATA_FACE = "Consolas"
HAND_FACE = "Segoe Print"

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass


def readable_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


class LatticeApp:
    def __init__(self, root: tk.Tk, demo: bool = False) -> None:
        self.root = root
        self.mode = "hide"
        self.payload_kind = "text"
        self.carrier_path: Path | None = None
        self.payload_path: Path | None = None
        self.output_path: Path | None = None
        self.preview_path: Path = SAMPLE_PLATE
        self.preview_photo: tk.PhotoImage | None = None
        self.preview_job: str | None = None
        self.capacity = 0
        self.payload_bytes = 0
        self.compact = False
        self._last_width = 1536
        self.task_results: queue.Queue = queue.Queue()

        root.title("Lattice — local PNG steganography")
        root.geometry("1536x985+0+0")
        root.minsize(1200, 800)
        root.configure(bg=PAPER)
        root.option_add("*Font", ("Segoe UI", 10))

        self._build_header()
        self._build_proof()
        self._build_bench()
        self._bind_shortcuts()
        root.bind("<Configure>", self._responsive_layout)

        if demo:
            self.carrier_path = SAMPLE_PLATE
            self.payload_text.insert("1.0", "Meet at the north trailhead at 7. Bring the maps.")
            self.output_path = ROOT / "lattice_encoded.png"
            self.output_var.set(self.output_path.name)
            self._inspect_carrier(SAMPLE_PLATE)
            self.caption_var.set("Carrier · sample landscape.png")
            self._set_status("Ready to create the encoded proof.", "ready")
            self._update_capacity()
        else:
            self._show_sample_state()

        root.after(120, self._render_preview)
        root.after(180, self._responsive_layout)
        root.after(50, self._poll_task_results)

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=PAPER)
        header.place(relx=0.03, rely=0.0, relwidth=0.94, relheight=0.10)

        tk.Label(
            header, text="Lattice", bg=PAPER, fg=INK, font=(DISPLAY_FACE, 42)
        ).place(relx=0.0, rely=-0.08)
        self.title_rule = tk.Frame(header, bg=INK, width=1)
        self.title_rule.place(relx=0.135, rely=0.08, relheight=0.62)
        self.subtitle_label = tk.Label(
            header,
            text="Steganography for a calmer internet.\nLocal only.",
            justify="left",
            bg=PAPER,
            fg=MUTED,
            font=(DATA_FACE, 9),
        )
        self.subtitle_label.place(relx=0.155, rely=0.10)

        self.mode_frame = tk.Frame(header, bg=RULE, padx=1, pady=1)
        self.mode_frame.place(relx=0.405, rely=0.08, relwidth=0.23, relheight=0.62)
        self.hide_button = self._flat_button(
            self.mode_frame, "Hide", lambda: self.set_mode("hide"), primary=True
        )
        self.hide_button.pack(side="left", fill="both", expand=True)
        self.recover_button = self._flat_button(
            self.mode_frame, "Recover", lambda: self.set_mode("recover")
        )
        self.recover_button.pack(side="left", fill="both", expand=True)

        self.local_status = tk.Frame(header, bg=PAPER)
        self.local_status.place(relx=0.835, rely=0.10, relwidth=0.165, relheight=0.58)
        dot = tk.Canvas(self.local_status, width=10, height=10, bg=PAPER, highlightthickness=0)
        dot.pack(side="left", padx=(0, 10))
        dot.create_oval(1, 1, 9, 9, fill=SAGE_DARK, outline="")
        self.local_status_label = tk.Label(
            self.local_status,
            text="Local only\nFiles never leave this device",
            justify="left",
            bg=PAPER,
            fg=INK,
            font=(DATA_FACE, 9),
        )
        self.local_status_label.pack(side="left")
        tk.Frame(self.root, bg=RULE, height=1).place(
            relx=0.02, rely=0.075, relwidth=0.96
        )

    def _build_proof(self) -> None:
        self.proof_frame = tk.Canvas(
            self.root, bg=PAPER, highlightthickness=0, bd=0
        )
        self.proof_frame.place(relx=0.015, rely=0.09, relwidth=0.97, relheight=0.61)
        self.proof_frame.bind("<Configure>", self._draw_outer_proof_frame)
        self.carrier_label = tk.Label(
            self.root,
            text="Carrier image",
            bg=PAPER,
            fg=INK,
            font=("Segoe UI Semibold", 10),
        )
        self.carrier_label.place(relx=0.052, rely=0.088)
        self.proof = tk.Canvas(
            self.root,
            bg="#D8D8D0",
            highlightbackground=RULE,
            highlightcolor=BRICK,
            highlightthickness=2,
            takefocus=1,
        )
        self.proof.place(relx=0.035, rely=0.115, relwidth=0.87, relheight=0.53)
        self.proof.bind("<Configure>", self._queue_preview)
        self.proof.bind("<Button-1>", lambda _event: self.choose_carrier())
        self.proof.bind("<Return>", lambda _event: self.choose_carrier())
        self.proof.bind("<space>", lambda _event: self.choose_carrier())

        self.meta = tk.Frame(self.root, bg=PAPER)
        self.meta.place(relx=0.91, rely=0.115, relwidth=0.07, relheight=0.53)
        self.meta_primary = tk.Label(
            self.meta,
            text="",
            justify="right",
            anchor="ne",
            wraplength=76,
            bg=PAPER,
            fg=MUTED,
            font=(HAND_FACE, 11),
        )
        self.meta_primary.pack(fill="x", pady=(14, 0))
        self.meta_note = tk.Label(
            self.meta,
            text="Choose a PNG\nto inspect.",
            justify="right",
            anchor="se",
            wraplength=76,
            bg=PAPER,
            fg=MUTED,
            font=(HAND_FACE, 11),
        )
        self.meta_note.pack(fill="both", expand=True, pady=(10, 20))

        self.caption_var = tk.StringVar(value="Sample carrier · choose a PNG to begin")
        self.caption_label = tk.Label(
            self.root,
            textvariable=self.caption_var,
            bg=PAPER,
            fg=MUTED,
            anchor="w",
            font=(DATA_FACE, 9),
        )
        self.caption_label.place(relx=0.05, rely=0.652, relwidth=0.53, relheight=0.035)
        self.assurance_label = tk.Label(
            self.root,
            text="LATTICE   ·   LOCAL ONLY   ·   DATA IS NEVER EXECUTED",
            bg=PAPER,
            fg=MUTED,
            anchor="e",
            font=(DATA_FACE, 8),
        )
        self.assurance_label.place(relx=0.58, rely=0.652, relwidth=0.38, relheight=0.035)
        self.outer_crop_marks = []
        for _ in range(4):
            mark = tk.Canvas(
                self.root, width=46, height=46, bg=PAPER, highlightthickness=0, bd=0
            )
            mark.create_line(8, 23, 38, 23, fill=INK, width=2)
            mark.create_line(23, 8, 23, 38, fill=INK, width=2)
            self.outer_crop_marks.append(mark)
        self._place_outer_crop_marks(compact=False)

    def _place_outer_crop_marks(self, compact: bool) -> None:
        if compact:
            for mark in self.outer_crop_marks:
                mark.place_forget()
            return
        positions = ((0.012, 0.10), (0.959, 0.10), (0.012, 0.648), (0.959, 0.648))
        for mark, (relx, rely) in zip(self.outer_crop_marks, positions):
            mark.place(relx=relx, rely=rely, width=46, height=46)

    def _draw_outer_proof_frame(self, _event=None) -> None:
        canvas = self.proof_frame
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        canvas.delete("all")
        inset = 2
        cross = 15
        canvas.create_rectangle(
            inset, inset, width - inset - 1, height - inset - 1, outline=RULE, width=1
        )
        for x in (16, width - 17):
            for y in (21, height - 22):
                canvas.create_line(x - cross, y, x + cross, y, fill=INK, width=2)
                canvas.create_line(x, y - cross, x, y + cross, fill=INK, width=2)

    def _build_bench(self) -> None:
        self.bench = tk.Frame(
            self.root,
            bg=PAPER_LIGHT,
            highlightbackground=RULE,
            highlightthickness=1,
        )
        self.bench.place(relx=0.02, rely=0.71, relwidth=0.96, relheight=0.265)
        self._configure_bench_grid()
        self._render_bench()

    def _configure_bench_grid(self) -> None:
        for column in range(4):
            weight = 1 if self.compact and column == 0 else 0
            if not self.compact:
                weight = (27, 25, 25, 23)[column]
            self.bench.grid_columnconfigure(
                column, weight=weight, uniform="" if self.compact else "bench"
            )
        for row in range(4):
            self.bench.grid_rowconfigure(
                row,
                weight=1 if (self.compact or row == 0) else 0,
                uniform="docket" if self.compact else "",
            )

    def _render_bench(self) -> None:
        for child in self.bench.winfo_children():
            child.destroy()
        if self.mode == "hide":
            self._build_hide_bench()
        else:
            self._build_recover_bench()

    def _station(self, column: int, title: str) -> tk.Frame:
        pad_x = 12 if self.compact else 20
        pad_y = 8 if self.compact else 17
        frame = tk.Frame(self.bench, bg=PAPER_LIGHT, padx=pad_x, pady=pad_y)
        row, grid_column = (column, 0) if self.compact else (0, column)
        frame.grid(row=row, column=grid_column, sticky="nsew")
        if column:
            if self.compact:
                tk.Frame(frame, bg=RULE, height=1).place(x=0, y=0, relwidth=1.0)
            else:
                tk.Frame(frame, bg=RULE, width=1).place(x=0, rely=0.02, relheight=0.94)
        heading = tk.Frame(frame, bg=PAPER_LIGHT)
        heading.pack(fill="x")
        icon = tk.Canvas(
            heading, width=20, height=20, bg=PAPER_LIGHT, highlightthickness=0
        )
        icon.pack(side="left", padx=(0, 8))
        self._draw_station_icon(icon, title)
        tk.Label(
            heading,
            text=title,
            bg=PAPER_LIGHT,
            fg=INK,
            anchor="w",
            font=(DISPLAY_FACE, 10 if self.compact else 12),
        ).pack(side="left", fill="x", expand=True)
        tk.Frame(frame, bg=RULE, height=1).pack(
            fill="x", pady=((4 if self.compact else 8), (6 if self.compact else 12))
        )
        return frame

    def _draw_station_icon(self, canvas: tk.Canvas, title: str) -> None:
        color = INK
        if title in ("Payload", "Encoded image", "Output", "Save as"):
            canvas.create_rectangle(4, 2, 15, 18, outline=color, width=1)
            canvas.create_line(11, 2, 15, 6, fill=color, width=1)
            canvas.create_line(11, 2, 11, 6, 15, 6, fill=color, width=1)
        elif title in ("Capacity", "Recovered data"):
            for x, top in ((3, 12), (8, 7), (13, 3)):
                canvas.create_rectangle(x, top, x + 3, 18, outline=color, width=1)
        else:
            for x in (4, 11):
                for y in (4, 11):
                    canvas.create_rectangle(x, y, x + 5, y + 5, fill=color, outline="")

    def _build_hide_bench(self) -> None:
        payload = self._station(0, "Payload")
        kinds = tk.Frame(payload, bg=RULE, padx=1, pady=1)
        kinds.pack(fill="x")
        self.text_kind_button = self._flat_button(
            kinds, "Text", lambda: self.set_payload_kind("text"), primary=True
        )
        self.text_kind_button.pack(side="left", fill="x", expand=True)
        self.file_kind_button = self._flat_button(
            kinds, "File", lambda: self.set_payload_kind("file")
        )
        self.file_kind_button.pack(side="left", fill="x", expand=True)
        self.payload_body = tk.Frame(payload, bg=PAPER_LIGHT)
        self.payload_body.pack(fill="both", expand=True, pady=(10, 0))
        self._render_payload_body()

        capacity = self._station(1, "Capacity")
        self.capacity_canvas = tk.Canvas(
            capacity, height=12 if self.compact else 18, bg="#D0CEC5", highlightthickness=0
        )
        self.capacity_canvas.pack(fill="x", pady=(2, 10))
        self.capacity_var = tk.StringVar(value="Select a carrier image")
        tk.Label(
            capacity,
            textvariable=self.capacity_var,
            justify="left",
            anchor="nw",
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(fill="both", expand=True)

        output = self._station(2, "Output")
        self.output_var = tk.StringVar(value="Choose output location")
        tk.Entry(
            output,
            textvariable=self.output_var,
            relief="flat",
            bg=WHITE,
            readonlybackground=WHITE,
            fg=INK,
            state="readonly",
            highlightbackground=RULE,
            highlightcolor=BRICK,
            highlightthickness=1,
        ).pack(fill="x", ipady=4 if self.compact else 8)
        self._flat_button(output, "Choose output…", self.choose_output).pack(
            anchor="w", pady=(10, 0)
        )
        self.output_detail = tk.Label(
            output,
            text="The source image stays unchanged.",
            justify="left",
            wraplength=190 if self.compact else 220,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=(DATA_FACE, 7 if self.compact else 8),
        )
        self.output_detail.pack(fill="x", pady=(10, 0))

        action = self._station(3, "Ready when you are")
        self.primary_button = self._flat_button(
            action, "Create encoded PNG", self.encode_payload, primary=True, large=True
        )
        self.primary_button.pack(fill="x", ipady=5 if self.compact else 32)
        self.status_var = tk.StringVar(value="Choose a carrier image to begin.")
        self.status_label = tk.Label(
            action,
            textvariable=self.status_var,
            justify="left",
            anchor="nw",
            wraplength=280,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=(DATA_FACE, 8 if self.compact else 9),
        )
        self.status_label.pack(fill="both", expand=True, pady=(13, 0))
        self._update_capacity()

    def _build_recover_bench(self) -> None:
        encoded = self._station(0, "Encoded image")
        self._flat_button(encoded, "Choose PNG…", self.choose_carrier).pack(fill="x")
        self.recover_source_var = tk.StringVar(
            value=self.carrier_path.name if self.carrier_path else "No image selected"
        )
        tk.Label(
            encoded,
            textvariable=self.recover_source_var,
            justify="left",
            anchor="nw",
            wraplength=280,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(fill="both", expand=True, pady=(12, 0))

        found = self._station(1, "Recovered data")
        self.recovered_preview = tk.Text(
            found,
            height=3 if self.compact else 5,
            wrap="word",
            relief="flat",
            bg=WHITE,
            fg=INK,
            state="disabled",
            highlightbackground=RULE,
            highlightthickness=1,
            font=("Consolas", 9),
        )
        self.recovered_preview.pack(fill="both", expand=True)

        output = self._station(2, "Save as")
        self.output_var = tk.StringVar(value="Optional for readable text")
        tk.Entry(
            output,
            textvariable=self.output_var,
            relief="flat",
            bg=WHITE,
            readonlybackground=WHITE,
            fg=INK,
            state="readonly",
            highlightbackground=RULE,
            highlightcolor=BRICK,
            highlightthickness=1,
        ).pack(fill="x", ipady=4 if self.compact else 8)
        self._flat_button(output, "Choose destination…", self.choose_recovery_output).pack(
            anchor="w", pady=(10, 0)
        )
        tk.Label(
            output,
            text="Recovered bytes are saved only when you choose a destination. They are never opened or executed.",
            justify="left",
            wraplength=210 if self.compact else 290,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=(DATA_FACE, 7 if self.compact else 8),
        ).pack(fill="x", pady=(10, 0))

        action = self._station(3, "Inspect safely")
        self.primary_button = self._flat_button(
            action, "Recover payload", self.recover_payload, primary=True, large=True
        )
        self.primary_button.pack(fill="x", ipady=5 if self.compact else 32)
        self.status_var = tk.StringVar(value="Choose an encoded PNG to inspect.")
        self.status_label = tk.Label(
            action,
            textvariable=self.status_var,
            justify="left",
            anchor="nw",
            wraplength=280,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=(DATA_FACE, 8 if self.compact else 9),
        )
        self.status_label.pack(fill="both", expand=True, pady=(13, 0))

    def _render_payload_body(self) -> None:
        for child in self.payload_body.winfo_children():
            child.destroy()
        if self.payload_kind == "text":
            self.payload_text = tk.Text(
                self.payload_body,
                height=2 if self.compact else 4,
                wrap="word",
                relief="flat",
                bg=WHITE,
                fg=INK,
                insertbackground=INK,
                highlightbackground=RULE,
                highlightcolor=BRICK,
                highlightthickness=1,
                font=("Segoe UI", 9),
            )
            self.payload_text.pack(fill="both", expand=True)
            self.payload_text.bind("<<Modified>>", self._text_modified)
        else:
            self._flat_button(
                self.payload_body, "Choose a file…", self.choose_payload_file
            ).pack(fill="x")
            self.payload_file_var = tk.StringVar(
                value=self.payload_path.name if self.payload_path else "No file selected"
            )
            tk.Label(
                self.payload_body,
                textvariable=self.payload_file_var,
                justify="left",
                anchor="nw",
                wraplength=280,
                bg=PAPER_LIGHT,
                fg=MUTED,
                font=("Segoe UI", 9),
            ).pack(fill="both", expand=True, pady=(12, 0))

    def _flat_button(
        self,
        parent,
        text: str,
        command,
        primary: bool = False,
        large: bool = False,
    ) -> tk.Button:
        bg = BRICK if primary else PAPER_LIGHT
        fg = WHITE if primary else INK
        active_bg = BRICK_ACTIVE if primary else "#D8D6CD"
        button = tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            cursor="hand2",
            takefocus=1,
            highlightbackground=BRICK if primary else RULE,
            highlightcolor=INK,
            highlightthickness=1,
            padx=15,
            pady=8 if large else 6,
            font=((DISPLAY_FACE if primary else DATA_FACE), 11 if large else 9),
        )
        if primary and large:
            stamp = tk.PhotoImage(master=self.root, width=18, height=18)
            for left, top in ((2, 2), (10, 2), (2, 10), (10, 10)):
                stamp.put(WHITE, to=(left, top, left + 6, top + 6))
            button.configure(image=stamp, compound="left")
            button._stamp_image = stamp
        return button

    def _responsive_layout(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return
        width = self.root.winfo_width()
        if width <= 1:
            return
        compact = width < 1320
        self._last_width = width
        if compact == self.compact:
            return

        saved_text = ""
        if hasattr(self, "payload_text") and self.payload_text.winfo_exists():
            saved_text = self.payload_text.get("1.0", "end-1c")
        saved_status = self.status_var.get() if hasattr(self, "status_var") else ""
        saved_recovered = ""
        if hasattr(self, "recovered_preview") and self.recovered_preview.winfo_exists():
            saved_recovered = self.recovered_preview.get("1.0", "end-1c")

        self.compact = compact
        if compact:
            self._place_outer_crop_marks(compact=True)
            self.title_rule.place(relx=0.17, rely=0.08, relheight=0.62)
            self.subtitle_label.place(relx=0.19, rely=0.10)
            self.subtitle_label.configure(font=(DATA_FACE, 8))
            self.local_status.place(relx=0.79, rely=0.10, relwidth=0.21, relheight=0.58)
            self.local_status_label.configure(font=(DATA_FACE, 8))
            self.carrier_label.place(relx=0.04, rely=0.115)
            self.proof_frame.place(relx=0.02, rely=0.135, relwidth=0.68, relheight=0.75)
            self.proof.place(relx=0.035, rely=0.145, relwidth=0.60, relheight=0.67)
            self.meta.place(relx=0.645, rely=0.145, relwidth=0.055, relheight=0.67)
            self.caption_label.place(relx=0.05, rely=0.825, relwidth=0.61, relheight=0.035)
            self.assurance_label.place(relx=0.05, rely=0.865, relwidth=0.61, relheight=0.035)
            self.bench.place(relx=0.72, rely=0.12, relwidth=0.26, relheight=0.855)
            self.meta_primary.configure(wraplength=58, font=(HAND_FACE, 9))
            self.meta_note.configure(wraplength=58, font=(HAND_FACE, 9))
        else:
            self._place_outer_crop_marks(compact=False)
            self.title_rule.place(relx=0.135, rely=0.08, relheight=0.62)
            self.subtitle_label.place(relx=0.155, rely=0.10)
            self.subtitle_label.configure(font=(DATA_FACE, 9))
            self.local_status.place(relx=0.835, rely=0.10, relwidth=0.165, relheight=0.58)
            self.local_status_label.configure(font=(DATA_FACE, 9))
            self.carrier_label.place(relx=0.052, rely=0.088)
            self.proof_frame.place(relx=0.015, rely=0.09, relwidth=0.97, relheight=0.61)
            self.proof.place(relx=0.035, rely=0.115, relwidth=0.87, relheight=0.53)
            self.meta.place(relx=0.91, rely=0.115, relwidth=0.07, relheight=0.53)
            self.caption_label.place(relx=0.05, rely=0.652, relwidth=0.53, relheight=0.035)
            self.assurance_label.place(relx=0.58, rely=0.652, relwidth=0.38, relheight=0.035)
            self.bench.place(relx=0.02, rely=0.71, relwidth=0.96, relheight=0.265)
            self.meta_primary.configure(wraplength=76, font=(HAND_FACE, 11))
            self.meta_note.configure(wraplength=76, font=(HAND_FACE, 11))

        self._configure_bench_grid()
        self._render_bench()
        if saved_text and self.mode == "hide" and self.payload_kind == "text":
            self.payload_text.insert("1.0", saved_text)
        if self.output_path:
            self.output_var.set(self.output_path.name)
        if saved_status:
            self.status_var.set(saved_status)
        if saved_recovered and self.mode == "recover":
            self.recovered_preview.configure(state="normal")
            self.recovered_preview.insert("1.0", saved_recovered)
            self.recovered_preview.configure(state="disabled")
        self._update_capacity()
        self._queue_preview()

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Alt-h>", lambda _event: self.set_mode("hide"))
        self.root.bind("<Alt-r>", lambda _event: self.set_mode("recover"))
        self.root.bind("<Control-o>", lambda _event: self.choose_carrier())
        self.root.bind("<Control-Return>", lambda _event: self.run_primary_action())

    def set_mode(self, mode: str) -> None:
        if (
            hasattr(self, "primary_button")
            and self.primary_button.winfo_exists()
            and self.primary_button.cget("state") == "disabled"
        ):
            return
        if mode == self.mode:
            return
        self.mode = mode
        self.output_path = None
        self.hide_button.configure(
            bg=BRICK if mode == "hide" else PAPER_LIGHT,
            fg=WHITE if mode == "hide" else INK,
        )
        self.recover_button.configure(
            bg=BRICK if mode == "recover" else PAPER_LIGHT,
            fg=WHITE if mode == "recover" else INK,
        )
        self.carrier_label.configure(
            text="Carrier image" if mode == "hide" else "Encoded image"
        )
        self._render_bench()

    def set_payload_kind(self, kind: str) -> None:
        if kind == self.payload_kind:
            return
        self.payload_kind = kind
        self.text_kind_button.configure(
            bg=BRICK if kind == "text" else PAPER_LIGHT,
            fg=WHITE if kind == "text" else INK,
        )
        self.file_kind_button.configure(
            bg=BRICK if kind == "file" else PAPER_LIGHT,
            fg=WHITE if kind == "file" else INK,
        )
        self._render_payload_body()
        self._update_capacity()

    def choose_carrier(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a PNG image",
            filetypes=[("PNG images", "*.png"), ("All files", "*.*")],
        )
        if not path:
            return
        candidate = Path(path)
        try:
            self._inspect_carrier(candidate)
        except (StegError, OSError) as exc:
            self._set_status(str(exc), "error")
            messagebox.showerror("Could not open PNG", str(exc), parent=self.root)
            return
        self.carrier_path = candidate
        self.preview_path = candidate
        self._queue_preview()
        if self.mode == "hide" and self.output_path is None:
            self.output_path = candidate.with_name(f"{candidate.stem}_encoded.png")
            self.output_var.set(self.output_path.name)
            self.output_detail.configure(text=f"Will save in {self.output_path.parent}")
        if self.mode == "recover" and hasattr(self, "recover_source_var"):
            self.recover_source_var.set(candidate.name)
        self.caption_var.set(f"Carrier · {candidate.name}")
        self._set_status("Image ready for local processing.", "ready")
        self._update_capacity()

    def _inspect_carrier(self, path: Path) -> None:
        width, height, channels, pixels = read_png(path)
        self.capacity = max(0, len(pixels) // 8 - 8)
        color = {1: "grayscale", 2: "grayscale + alpha", 3: "RGB", 4: "RGBA"}[channels]
        self.meta_primary.configure(
            text=f"{width} × {height}\nPNG\n{color}\n\nCapacity\n{readable_size(self.capacity)}"
        )
        self.meta_note.configure(
            text="Suitable carrier.\n\nOnly the least-significant bits are changed."
        )

    def choose_payload_file(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Choose a payload file")
        if not path:
            return
        self.payload_path = Path(path)
        self.payload_file_var.set(
            f"{self.payload_path.name}\n{readable_size(self.payload_path.stat().st_size)}"
        )
        self._update_capacity()

    def choose_output(self) -> None:
        initial = "encoded.png"
        if self.carrier_path:
            initial = f"{self.carrier_path.stem}_encoded.png"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save encoded PNG",
            defaultextension=".png",
            initialfile=initial,
            filetypes=[("PNG images", "*.png")],
        )
        if path:
            self.output_path = Path(path)
            self.output_var.set(self.output_path.name)
            self.output_detail.configure(text=f"Will save in {self.output_path.parent}")

    def choose_recovery_output(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save recovered data",
            initialfile="recovered_payload.bin",
            filetypes=[("All files", "*.*")],
        )
        if path:
            self.output_path = Path(path)
            self.output_var.set(self.output_path.name)

    def _text_modified(self, _event=None) -> None:
        if hasattr(self, "payload_text") and self.payload_text.edit_modified():
            self.payload_text.edit_modified(False)
            self._update_capacity()

    def _current_payload(self) -> bytes:
        if self.payload_kind == "text":
            if not hasattr(self, "payload_text") or not self.payload_text.winfo_exists():
                return b""
            return self.payload_text.get("1.0", "end-1c").encode("utf-8")
        if not self.payload_path:
            return b""
        return self.payload_path.read_bytes()

    def _update_capacity(self) -> None:
        if (
            not hasattr(self, "capacity_canvas")
            or not self.capacity_canvas.winfo_exists()
        ):
            return
        try:
            if self.payload_kind == "text":
                self.payload_bytes = len(self._current_payload())
            elif self.payload_path:
                self.payload_bytes = self.payload_path.stat().st_size
            else:
                self.payload_bytes = 0
        except OSError:
            self.payload_bytes = 0
        ratio = self.payload_bytes / self.capacity if self.capacity else 0
        self.capacity_canvas.delete("all")
        width = max(1, self.capacity_canvas.winfo_width())
        height = max(1, self.capacity_canvas.winfo_height())
        fill = ERROR if ratio > 1 else SAGE
        meter_width = width * min(ratio, 1)
        if self.payload_bytes and ratio <= 1:
            meter_width = max(4, meter_width)
        self.capacity_canvas.create_rectangle(
            0, 0, meter_width, height, fill=fill, outline=""
        )
        remaining = self.capacity - self.payload_bytes
        capacity_text = readable_size(self.capacity) if self.carrier_path else "—"
        remaining_text = readable_size(max(0, remaining)) if self.carrier_path else "—"
        if not self.carrier_path:
            suitability = "—"
        elif not self.payload_bytes:
            suitability = "Add text or choose a file"
        elif remaining >= 0:
            suitability = "Yes — fits this carrier"
        else:
            suitability = "No — payload is too large"
        text = (
            f"{readable_size(self.payload_bytes)} of {capacity_text} "
            f"({max(0, ratio) * 100:.2f}%)\n\n\n"
            f"Estimated capacity  {capacity_text}\n"
            f"Remaining space  {remaining_text}\n"
            f"Suitable  {suitability}"
        )
        self.capacity_var.set(text)

    def encode_payload(self) -> None:
        if not self.carrier_path:
            return self._set_status("Choose a carrier PNG first.", "error")
        self._update_capacity()
        if not self.payload_bytes:
            return self._set_status("Enter text or choose a payload file.", "error")
        if self.payload_bytes > self.capacity:
            return self._set_status("The payload is larger than this image can hold.", "error")
        if not self.output_path:
            self.choose_output()
            if not self.output_path:
                return self._set_status("Choose where to save the encoded PNG.", "error")
        if self.output_path.resolve() == self.carrier_path.resolve():
            return self._set_status("Choose a new output name; the source is never overwritten.", "error")
        carrier = self.carrier_path
        output = self.output_path
        payload_kind = self.payload_kind
        payload_text = (
            self.payload_text.get("1.0", "end-1c") if payload_kind == "text" else ""
        )
        payload_path = self.payload_path

        def work():
            if payload_kind == "text":
                payload = payload_text.encode("utf-8")
            elif payload_path:
                payload = payload_path.read_bytes()
            else:
                raise OSError("Choose a payload file before encoding.")
            embed(carrier, payload, output)
            return len(payload), output

        self._run_background("Creating…", "Create encoded PNG", work, self._encode_done)

    def _encode_done(self, result) -> None:
        payload_size, output = result
        self._set_status(
            f"Encoded proof created.\n{output.name}\n{readable_size(payload_size)} hidden locally.",
            "success",
        )
        if hasattr(self, "output_detail") and self.output_detail.winfo_exists():
            self.output_detail.configure(text=f"Saved to {output.parent}")

    def recover_payload(self) -> None:
        if not self.carrier_path:
            return self._set_status("Choose an encoded PNG first.", "error")
        carrier = self.carrier_path
        output = self.output_path

        def work():
            payload = extract(carrier)
            if output:
                output.write_bytes(payload)
            try:
                preview = payload.decode("utf-8")
            except UnicodeDecodeError:
                preview = f"Binary payload · {readable_size(len(payload))}"
                readable = False
            else:
                readable = True
            return payload, preview, readable, output

        self._run_background("Inspecting…", "Recover payload", work, self._recover_done)

    def _recover_done(self, result) -> None:
        payload, preview, readable, output = result
        if output:
            message = f"Recovered {readable_size(len(payload))} to {output.name}. Nothing was executed."
            kind = "success"
        elif readable:
            message = f"Readable text recovered · {readable_size(len(payload))}. Nothing was executed."
            kind = "success"
        else:
            message = "Binary data recovered. Choose a destination, then recover again to save it."
            kind = "ready"
        self._set_status(message, kind)
        self.recovered_preview.configure(state="normal")
        self.recovered_preview.delete("1.0", "end")
        self.recovered_preview.insert("1.0", preview[:2000])
        self.recovered_preview.configure(state="disabled")

    def _run_background(self, busy_text: str, idle_text: str, work, on_success) -> None:
        self.primary_button.configure(state="disabled", text=busy_text)
        self.hide_button.configure(state="disabled")
        self.recover_button.configure(state="disabled")

        def worker() -> None:
            try:
                result = work()
            except (StegError, OSError, ValueError) as exc:
                message = str(exc)
                self.task_results.put((idle_text, message, None, None))
            except Exception as exc:  # keep callback failures recoverable in the UI
                message = f"Processing failed: {exc}"
                self.task_results.put((idle_text, message, None, None))
            else:
                self.task_results.put((idle_text, None, on_success, result))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_task_results(self) -> None:
        try:
            while True:
                args = self.task_results.get_nowait()
                self._finish_background(*args)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_task_results)

    def _finish_background(self, idle_text, error, on_success, result) -> None:
        self.primary_button.configure(state="normal", text=idle_text)
        self.hide_button.configure(state="normal")
        self.recover_button.configure(state="normal")
        if error:
            self._set_status(error, "error")
        elif on_success:
            on_success(result)

    def run_primary_action(self) -> None:
        if self.mode == "hide":
            self.encode_payload()
        else:
            self.recover_payload()

    def _set_status(self, message: str, kind: str) -> None:
        if not hasattr(self, "status_var"):
            return
        self.status_var.set(message)
        self.status_label.configure(
            fg={"error": ERROR, "success": SAGE_DARK}.get(kind, MUTED)
        )

    def _show_sample_state(self) -> None:
        try:
            width, height, _channels, _pixels = read_png(SAMPLE_PLATE)
            self.meta_primary.configure(text=f"{width} × {height}\nPNG\nSample proof")
        except (StegError, OSError):
            self.meta_primary.configure(text="Sample proof")
        self.meta_note.configure(text="Choose a PNG\nto replace this\nsample carrier.")

    def _queue_preview(self, _event=None) -> None:
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(140, self._render_preview)

    def _render_preview(self) -> None:
        self.preview_job = None
        width = max(120, self.proof.winfo_width())
        height = max(80, self.proof.winfo_height())
        self.proof.delete("all")
        try:
            display_path = self.preview_path
            if self.preview_path == SAMPLE_PLATE and self.compact:
                display_path = DOCKET_PLATE
            elif self.preview_path == SAMPLE_PLATE and width < 1200:
                display_path = COMPACT_PLATE
            source = tk.PhotoImage(master=self.root, file=str(display_path))
            scale = max(width / source.width(), height / source.height())
            if 0.90 <= scale <= 1.10:
                self.preview_photo = source
            else:
                fraction = Fraction(scale).limit_denominator(8)
                numerator = max(1, fraction.numerator)
                denominator = max(1, fraction.denominator)
                while (
                    source.width() * numerator // denominator < width
                    or source.height() * numerator // denominator < height
                ):
                    numerator += 1
                numerator = min(numerator, 16)
                self.preview_photo = source.subsample(denominator, denominator).zoom(
                    numerator, numerator
                )
            self.proof.create_image(
                width // 2,
                height // 2,
                image=self.preview_photo,
                anchor="center",
            )
        except tk.TclError:
            self.proof.configure(bg="#D8D8D0")
            self.proof.create_text(
                width // 2,
                height // 2,
                text="Preview unavailable\nChoose an 8-bit PNG",
                fill=MUTED,
                justify="center",
                font=("Segoe UI", 12),
            )
        self._draw_crop_marks(width, height)

    def _draw_crop_marks(self, width: int, height: int) -> None:
        length = 28
        inset = 9
        self.proof.create_rectangle(
            3, 3, width - 4, height - 4, outline=PAPER_LIGHT, width=3
        )
        for x, y, sx, sy in (
            (inset, inset, 1, 1),
            (width - inset, inset, -1, 1),
            (inset, height - inset, 1, -1),
            (width - inset, height - inset, -1, -1),
        ):
            self.proof.create_line(x, y, x + sx * length, y, fill=PAPER_LIGHT, width=4)
            self.proof.create_line(x, y, x, y + sy * length, fill=PAPER_LIGHT, width=4)
            self.proof.create_line(x, y, x + sx * length, y, fill=INK, width=1)
            self.proof.create_line(x, y, x, y + sy * length, fill=INK, width=1)
        for x in (width // 2,):
            self.proof.create_line(x, 3, x, 16, fill=PAPER_LIGHT, width=3)
            self.proof.create_line(x, height - 4, x, height - 17, fill=PAPER_LIGHT, width=3)
        for y in (height // 2,):
            self.proof.create_line(3, y, 16, y, fill=PAPER_LIGHT, width=3)
            self.proof.create_line(width - 4, y, width - 17, y, fill=PAPER_LIGHT, width=3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lattice local PNG steganography UI")
    parser.add_argument("--demo", action="store_true", help="load sample content for review")
    args = parser.parse_args(argv)
    root = tk.Tk()
    LatticeApp(root, demo=args.demo)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
