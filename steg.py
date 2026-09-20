"""Steganography tool: hide and recover data inside PNG images.

Uses least-significant-bit (LSB) embedding in the pixel data of a lossless
PNG image. Only the lowest bit of each color channel byte is touched, so the
visual difference is imperceptible.

No third-party dependencies: the PNG codec is implemented with the stdlib
(zlib, struct).

Usage:
    python steg.py encode <image.png> <text> [-o output.png]
    python steg.py encode <image.png> --file payload.bin [-o output.png]
    python steg.py decode <image.png> [-o output.txt]
"""

import argparse
import struct
import sys
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAGIC = b"STEG"


class StegError(Exception):
    pass


# --------------------------------------------------------------------------
# PNG decoding (read raw pixels back out of a PNG file)
# --------------------------------------------------------------------------

def _iter_chunks(data):
    pos = 8
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        cdata = data[pos + 8:pos + 8 + length]
        yield ctype, cdata
        pos += 12 + length


def _paeth(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _unfilter_scanline(filter_type, scan, prev, bpp):
    out = bytearray(scan)
    for i in range(len(scan)):
        raw = out[i]
        a = out[i - bpp] if i >= bpp else 0
        b = prev[i] if prev else 0
        c = prev[i - bpp] if prev and i >= bpp else 0
        if filter_type == 1:
            out[i] = (raw + a) & 0xFF
        elif filter_type == 2:
            out[i] = (raw + b) & 0xFF
        elif filter_type == 3:
            out[i] = (raw + (a + b) // 2) & 0xFF
        elif filter_type == 4:
            out[i] = (raw + _paeth(a, b, c)) & 0xFF
    return bytes(out)


def _channels_for_color_type(color_type):
    return {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]


def read_png(path):
    """Return (width, height, channels, pixels).

    ``pixels`` is a ``bytearray`` of the raw image data in row-major order,
    ``channels`` bytes per pixel.
    """
    with open(path, "rb") as fh:
        data = fh.read()

    if not data.startswith(SIGNATURE):
        raise StegError("not a PNG file (bad signature)")

    width = height = bit_depth = color_type = None
    idat = bytearray()

    for ctype, cdata in _iter_chunks(data):
        if ctype == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(
                ">IIBB", cdata[:10]
            )
        elif ctype == b"IDAT":
            idat.extend(cdata)
        elif ctype == b"PLTE":
            raise StegError("paletted PNGs are not supported; convert to RGB first")

    if None in (width, height, bit_depth, color_type):
        raise StegError("malformed PNG: missing IHDR")
    if bit_depth != 8:
        raise StegError("only 8-bit PNGs are supported")
    if color_type not in (0, 2, 4, 6):
        raise StegError("unsupported color type; use grayscale, RGB, or RGBA")

    channels = _channels_for_color_type(color_type)

    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise StegError("could not decompress image data") from exc

    bpp = channels
    stride = width * channels
    pixels = bytearray()
    prev = b"\x00" * stride
    pos = 0
    for _ in range(height):
        filter_type = raw[pos]
        pos += 1
        scan = raw[pos:pos + stride]
        pos += stride
        if len(scan) < stride:
            raise StegError("malformed PNG: truncated scanline")
        decoded_scan = _unfilter_scanline(filter_type, scan, prev, bpp)
        pixels.extend(decoded_scan)
        prev = decoded_scan

    return width, height, channels, pixels


# --------------------------------------------------------------------------
# PNG encoding (write pixels back out as a PNG file)
# --------------------------------------------------------------------------

def _chunk(ctype, cdata):
    chunk = ctype + cdata
    crc = zlib.crc32(chunk) & 0xFFFFFFFF
    return struct.pack(">I", len(cdata)) + chunk + struct.pack(">I", crc)


def write_png(path, width, height, channels, pixels, color_type):
    raw = bytearray()
    stride = width * channels
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        raw.extend(pixels[y * stride:(y + 1) * stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    out = bytearray(SIGNATURE)
    out += _chunk(b"IHDR", ihdr)
    out += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += _chunk(b"IEND", b"")

    with open(path, "wb") as fh:
        fh.write(out)


# --------------------------------------------------------------------------
# LSB embedding / extraction
# --------------------------------------------------------------------------

def _encode_payload(payload):
    """Prepend MAGIC + 4-byte big-endian length to the payload."""
    if not isinstance(payload, (bytes, bytearray)):
        payload = bytes(payload)
    return MAGIC + struct.pack(">I", len(payload)) + payload


def _decode_payload(blob):
    """Strip MAGIC + length, returning the original payload."""
    if not blob.startswith(MAGIC):
        raise StegError("no hidden data found (bad magic)")
    length = struct.unpack(">I", blob[4:8])[0]
    payload = blob[8:8 + length]
    if len(payload) < length:
        raise StegError("hidden data is truncated (image was modified?)")
    return bytes(payload)


def embed(cover_path, payload, output_path):
    """Hide ``payload`` (bytes) inside ``cover_path``, writing to ``output_path``."""
    width, height, channels, pixels = read_png(cover_path)
    full = _encode_payload(payload)

    bits_needed = len(full) * 8
    if bits_needed > len(pixels):
        capacity = len(pixels) // 8
        raise StegError(
            f"payload too large: needs {len(full)} bytes but image holds "
            f"only {capacity - 8} bytes"
        )

    for i in range(len(full)):
        byte = full[i]
        for bit in range(8):
            pixel_index = i * 8 + bit
            pixels[pixel_index] = (pixels[pixel_index] & 0xFE) | ((byte >> bit) & 1)

    color_type = {1: 0, 3: 2, 2: 4, 4: 6}[channels]
    write_png(output_path, width, height, channels, pixels, color_type)


def extract(path):
    """Recover and return the payload hidden inside ``path`` (as bytes)."""
    _, _, _, pixels = read_png(path)

    header_bits = 8 * 8  # MAGIC + length field
    if len(pixels) < header_bits:
        raise StegError("image too small to contain hidden data")

    blob = bytearray(len(pixels) // 8)
    for i in range(len(blob)):
        byte = 0
        for bit in range(8):
            pixel_index = i * 8 + bit
            byte |= (pixels[pixel_index] & 1) << bit
        blob[i] = byte

    return _decode_payload(bytes(blob))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Hide text/data inside a PNG image and recover it."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="hide data inside an image")
    enc.add_argument("image", help="path to the cover PNG image")
    enc.add_argument("text", nargs="?", help="text to hide")
    enc.add_argument("--file", help="hide the contents of this file instead of text")
    enc.add_argument("-o", "--output", help="output image path")
    enc.set_defaults(func=_cmd_encode)

    dec = sub.add_parser("decode", help="recover hidden data from an image")
    dec.add_argument("image", help="path to the image with hidden data")
    dec.add_argument("-o", "--output", help="write recovered data to a file")
    dec.set_defaults(func=_cmd_decode)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except StegError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_encode(args):
    if args.text is not None:
        payload = args.text.encode("utf-8")
        if args.file:
            print("error: provide either text or --file, not both", file=sys.stderr)
            sys.exit(1)
    elif args.file:
        with open(args.file, "rb") as fh:
            payload = fh.read()
    else:
        print("error: provide text or --file", file=sys.stderr)
        sys.exit(1)

    output = args.output
    if output is None:
        if args.image.lower().endswith(".png"):
            stem = args.image[:-4]
        else:
            stem = args.image
        output = f"{stem}_steg.png"

    embed(args.image, payload, output)
    print(f"hidden {len(payload)} bytes -> {output}")


def _cmd_decode(args):
    payload = extract(args.image)
    if args.output:
        with open(args.output, "wb") as fh:
            fh.write(payload)
        print(f"recovered {len(payload)} bytes -> {args.output}")
    else:
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            print(payload, file=sys.stdout)
        else:
            print(text)


if __name__ == "__main__":
    sys.exit(main())
