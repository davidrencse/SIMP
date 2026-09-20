"""Lattice: a local desktop UI for safe PNG steganography.

The interface only embeds and extracts bytes. Recovered data is never executed.
"""

from __future__ import annotations

import argparse
import ctypes
from fractions import Fraction
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

from steg import StegError, embed, extract, read_png


ROOT = Path(__file__).resolve().parent
SAMPLE_PLATE = ROOT / "assets/plates/carrier-photo.png"

PAPER = "#E7E6DD"
PAPER_LIGHT = "#F3F1E9"
INK = "#26241F"
MUTED = "#6D6B64"
RULE = "#AAA89F"
SAGE = "#75877B"
SAGE_DARK = "#53685C"
BRICK = "#A74838"
BRICK_ACTIVE = "#8C382D"
WHITE = "#FBFAF5"
ERROR = "#8E2F2A"

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

        root.title("Lattice — local PNG steganography")
        root.geometry("1536x985+0+0")
        root.minsize(1080, 720)
        root.configure(bg=PAPER)
        root.option_add("*Font", ("Segoe UI", 10))

        self._build_header()
        self._build_proof()
        self._build_bench()
        self._bind_shortcuts()

        if demo:
            self.carrier_path = SAMPLE_PLATE
            self.payload_text.insert("1.0", "Meet at the north trailhead at 7. Bring the maps.")
            self.output_path = ROOT / "lattice_encoded.png"
            self.output_var.set(str(self.output_path))
            self._inspect_carrier(SAMPLE_PLATE)
            self.caption_var.set("Carrier · sample landscape.png")
            self._set_status("Ready to create the encoded proof.", "ready")
            self._update_capacity()
        else:
            self._show_sample_state()

        root.after(120, self._render_preview)

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=PAPER)
        header.place(relx=0.03, rely=0.018, relwidth=0.94, relheight=0.085)

        tk.Label(
            header, text="Lattice", bg=PAPER, fg=INK, font=("Georgia", 34)
        ).place(relx=0.0, rely=0.02)
        tk.Frame(header, bg=INK, width=1).place(relx=0.135, rely=0.18, relheight=0.62)
        tk.Label(
            header,
            text="PNG steganography\nLocal only.",
            justify="left",
            bg=PAPER,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).place(relx=0.155, rely=0.18)

        self.mode_frame = tk.Frame(header, bg=RULE, padx=1, pady=1)
        self.mode_frame.place(relx=0.405, rely=0.17, relwidth=0.23, relheight=0.62)
        self.hide_button = self._flat_button(
            self.mode_frame, "Hide", lambda: self.set_mode("hide"), primary=True
        )
        self.hide_button.pack(side="left", fill="both", expand=True)
        self.recover_button = self._flat_button(
            self.mode_frame, "Recover", lambda: self.set_mode("recover")
        )
        self.recover_button.pack(side="left", fill="both", expand=True)

        status = tk.Frame(header, bg=PAPER)
        status.place(relx=0.835, rely=0.18, relwidth=0.165, relheight=0.58)
        dot = tk.Canvas(status, width=10, height=10, bg=PAPER, highlightthickness=0)
        dot.pack(side="left", padx=(0, 10))
        dot.create_oval(1, 1, 9, 9, fill=SAGE_DARK, outline="")
        tk.Label(
            status,
            text="Local only\nFiles never leave this device",
            justify="left",
            bg=PAPER,
            fg=INK,
            font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Frame(self.root, bg=RULE, height=1).place(
            relx=0.02, rely=0.108, relwidth=0.96
        )

    def _build_proof(self) -> None:
        self.carrier_label = tk.Label(
            self.root,
            text="Carrier image",
            bg=PAPER,
            fg=INK,
            font=("Segoe UI Semibold", 10),
        )
        self.carrier_label.place(relx=0.052, rely=0.115)
        self.proof = tk.Canvas(
            self.root,
            bg="#D8D8D0",
            highlightthickness=0,
            takefocus=1,
        )
        self.proof.place(relx=0.035, rely=0.145, relwidth=0.87, relheight=0.505)
        self.proof.bind("<Configure>", self._queue_preview)
        self.proof.bind("<Button-1>", lambda _event: self.choose_carrier())
        self.proof.bind("<Return>", lambda _event: self.choose_carrier())

        self.meta = tk.Frame(self.root, bg=PAPER)
        self.meta.place(relx=0.91, rely=0.145, relwidth=0.07, relheight=0.505)
        self.meta_primary = tk.Label(
            self.meta,
            text="",
            justify="left",
            anchor="nw",
            wraplength=105,
            bg=PAPER,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.meta_primary.pack(fill="x", pady=(14, 0))
        self.meta_note = tk.Label(
            self.meta,
            text="Choose a PNG\nto inspect.",
            justify="left",
            anchor="sw",
            wraplength=105,
            bg=PAPER,
            fg=MUTED,
            font=("Segoe UI Italic", 9),
        )
        self.meta_note.pack(fill="both", expand=True, pady=(10, 20))

        self.caption_var = tk.StringVar(value="Sample carrier · choose a PNG to begin")
        tk.Label(
            self.root,
            textvariable=self.caption_var,
            bg=PAPER,
            fg=MUTED,
            anchor="w",
            font=("Segoe UI", 9),
        ).place(relx=0.05, rely=0.657, relwidth=0.53, relheight=0.035)
        tk.Label(
            self.root,
            text="LATTICE   ·   LOCAL ONLY   ·   DATA IS NEVER EXECUTED",
            bg=PAPER,
            fg=MUTED,
            anchor="e",
            font=("Segoe UI", 8),
        ).place(relx=0.58, rely=0.657, relwidth=0.38, relheight=0.035)

    def _build_bench(self) -> None:
        self.bench = tk.Frame(
            self.root,
            bg=PAPER_LIGHT,
            highlightbackground=RULE,
            highlightthickness=1,
        )
        self.bench.place(relx=0.02, rely=0.71, relwidth=0.96, relheight=0.265)
        for column, weight in enumerate((27, 25, 25, 23)):
            self.bench.grid_columnconfigure(column, weight=weight, uniform="bench")
        self.bench.grid_rowconfigure(0, weight=1)
        self._render_bench()

    def _render_bench(self) -> None:
        for child in self.bench.winfo_children():
            child.destroy()
        if self.mode == "hide":
            self._build_hide_bench()
        else:
            self._build_recover_bench()

    def _station(self, column: int, title: str) -> tk.Frame:
        frame = tk.Frame(self.bench, bg=PAPER_LIGHT, padx=20, pady=17)
        frame.grid(row=0, column=column, sticky="nsew")
        if column:
            tk.Frame(frame, bg=RULE, width=1).place(x=0, rely=0.02, relheight=0.94)
        tk.Label(
            frame,
            text=title,
            bg=PAPER_LIGHT,
            fg=INK,
            anchor="w",
            font=("Segoe UI Semibold", 12),
        ).pack(fill="x")
        tk.Frame(frame, bg=RULE, height=1).pack(fill="x", pady=(8, 12))
        return frame

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
            capacity, height=18, bg="#D0CEC5", highlightthickness=0
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
            fg=INK,
            highlightbackground=RULE,
            highlightcolor=BRICK,
            highlightthickness=1,
        ).pack(fill="x", ipady=8)
        self._flat_button(output, "Choose output…", self.choose_output).pack(
            anchor="w", pady=(10, 0)
        )
        self.output_detail = tk.Label(
            output,
            text="A new PNG will be created; the source is unchanged.",
            justify="left",
            wraplength=290,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=("Segoe UI", 8),
        )
        self.output_detail.pack(fill="x", pady=(10, 0))

        action = self._station(3, "Ready when you are")
        self.primary_button = self._flat_button(
            action, "Create encoded PNG", self.encode_payload, primary=True, large=True
        )
        self.primary_button.pack(fill="x", ipady=11)
        self.status_var = tk.StringVar(value="Choose a carrier image to begin.")
        self.status_label = tk.Label(
            action,
            textvariable=self.status_var,
            justify="left",
            anchor="nw",
            wraplength=280,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=("Segoe UI", 9),
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
            height=5,
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
            fg=INK,
            highlightbackground=RULE,
            highlightcolor=BRICK,
            highlightthickness=1,
        ).pack(fill="x", ipady=8)
        self._flat_button(output, "Choose destination…", self.choose_recovery_output).pack(
            anchor="w", pady=(10, 0)
        )
        tk.Label(
            output,
            text="Recovered bytes are saved only when you choose a destination. They are never opened or executed.",
            justify="left",
            wraplength=290,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(fill="x", pady=(10, 0))

        action = self._station(3, "Inspect safely")
        self.primary_button = self._flat_button(
            action, "Recover payload", self.recover_payload, primary=True, large=True
        )
        self.primary_button.pack(fill="x", ipady=11)
        self.status_var = tk.StringVar(value="Choose an encoded PNG to inspect.")
        self.status_label = tk.Label(
            action,
            textvariable=self.status_var,
            justify="left",
            anchor="nw",
            wraplength=280,
            bg=PAPER_LIGHT,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.status_label.pack(fill="both", expand=True, pady=(13, 0))

    def _render_payload_body(self) -> None:
        for child in self.payload_body.winfo_children():
            child.destroy()
        if self.payload_kind == "text":
            self.payload_text = tk.Text(
                self.payload_body,
                height=4,
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
            cursor="hand2",
            takefocus=1,
            highlightbackground=BRICK if primary else RULE,
            highlightcolor=INK,
            highlightthickness=1,
            padx=15,
            pady=8 if large else 6,
            font=("Segoe UI Semibold", 11 if large else 9),
        )

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Alt-h>", lambda _event: self.set_mode("hide"))
        self.root.bind("<Alt-r>", lambda _event: self.set_mode("recover"))
        self.root.bind("<Control-o>", lambda _event: self.choose_carrier())
        self.root.bind("<Control-Return>", lambda _event: self.run_primary_action())

    def set_mode(self, mode: str) -> None:
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
            self.output_var.set(str(self.output_path))
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
            self.output_var.set(path)

    def choose_recovery_output(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save recovered data",
            initialfile="recovered_payload.bin",
            filetypes=[("All files", "*.*")],
        )
        if path:
            self.output_path = Path(path)
            self.output_var.set(path)

    def _text_modified(self, _event=None) -> None:
        if hasattr(self, "payload_text") and self.payload_text.edit_modified():
            self.payload_text.edit_modified(False)
            self._update_capacity()

    def _current_payload(self) -> bytes:
        if self.payload_kind == "text":
            return self.payload_text.get("1.0", "end-1c").encode("utf-8")
        if not self.payload_path:
            return b""
        return self.payload_path.read_bytes()

    def _update_capacity(self) -> None:
        if not hasattr(self, "capacity_canvas"):
            return
        try:
            self.payload_bytes = len(self._current_payload())
        except OSError:
            self.payload_bytes = 0
        ratio = self.payload_bytes / self.capacity if self.capacity else 0
        self.capacity_canvas.delete("all")
        width = max(1, self.capacity_canvas.winfo_width())
        height = max(1, self.capacity_canvas.winfo_height())
        fill = ERROR if ratio > 1 else SAGE
        self.capacity_canvas.create_rectangle(
            0, 0, width * min(ratio, 1), height, fill=fill, outline=""
        )
        if not self.carrier_path:
            text = "Select a carrier image\nto calculate available space."
        elif not self.payload_bytes:
            text = f"Available\n{readable_size(self.capacity)}\n\nAdd text or choose a file."
        else:
            remaining = self.capacity - self.payload_bytes
            suitability = "Fits this carrier" if remaining >= 0 else "Payload is too large"
            text = (
                f"{readable_size(self.payload_bytes)} of {readable_size(self.capacity)}\n"
                f"{max(0, ratio) * 100:.2f}% used\n\n{suitability}"
            )
        self.capacity_var.set(text)

    def encode_payload(self) -> None:
        if not self.carrier_path:
            return self._set_status("Choose a carrier PNG first.", "error")
        payload = self._current_payload()
        if not payload:
            return self._set_status("Enter text or choose a payload file.", "error")
        if len(payload) > self.capacity:
            return self._set_status("The payload is larger than this image can hold.", "error")
        if not self.output_path:
            self.choose_output()
            if not self.output_path:
                return self._set_status("Choose where to save the encoded PNG.", "error")
        if self.output_path.resolve() == self.carrier_path.resolve():
            return self._set_status("Choose a new output name; the source is never overwritten.", "error")
        self.primary_button.configure(state="disabled", text="Creating…")
        self.root.update_idletasks()
        try:
            embed(self.carrier_path, payload, self.output_path)
        except (StegError, OSError) as exc:
            self._set_status(str(exc), "error")
        else:
            self._set_status(
                f"Encoded proof created.\n{self.output_path.name}\n{readable_size(len(payload))} hidden locally.",
                "success",
            )
            self.output_detail.configure(text=f"Saved to {self.output_path.parent}")
        finally:
            self.primary_button.configure(state="normal", text="Create encoded PNG")

    def recover_payload(self) -> None:
        if not self.carrier_path:
            return self._set_status("Choose an encoded PNG first.", "error")
        self.primary_button.configure(state="disabled", text="Inspecting…")
        self.root.update_idletasks()
        try:
            payload = extract(self.carrier_path)
        except (StegError, OSError) as exc:
            self._set_status(str(exc), "error")
        else:
            try:
                preview = payload.decode("utf-8")
            except UnicodeDecodeError:
                preview = f"Binary payload · {readable_size(len(payload))}"
                if not self.output_path:
                    self._set_status(
                        "Binary data recovered. Choose a destination to save it.", "ready"
                    )
                else:
                    self.output_path.write_bytes(payload)
                    self._set_status(
                        f"Recovered {readable_size(len(payload))} to {self.output_path.name}.",
                        "success",
                    )
            else:
                self._set_status(
                    f"Readable text recovered · {readable_size(len(payload))}. Nothing was executed.",
                    "success",
                )
                if self.output_path:
                    self.output_path.write_bytes(payload)
            self.recovered_preview.configure(state="normal")
            self.recovered_preview.delete("1.0", "end")
            self.recovered_preview.insert("1.0", preview[:2000])
            self.recovered_preview.configure(state="disabled")
        finally:
            self.primary_button.configure(state="normal", text="Recover payload")

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
            source = tk.PhotoImage(master=self.root, file=str(self.preview_path))
            scale = max(width / source.width(), height / source.height())
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
        length = 18
        inset = 8
        for x, y, sx, sy in (
            (inset, inset, 1, 1),
            (width - inset, inset, -1, 1),
            (inset, height - inset, 1, -1),
            (width - inset, height - inset, -1, -1),
        ):
            self.proof.create_line(x, y, x + sx * length, y, fill=WHITE, width=2)
            self.proof.create_line(x, y, x, y + sy * length, fill=WHITE, width=2)


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
