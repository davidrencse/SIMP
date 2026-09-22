# Product

<!-- impeccable:product-schema 1 -->

## Platform

Native desktop application for Windows-class environments, implemented with Python and Tkinter.

## Stack

Python 3.10+ with the standard library only. Tkinter renders both desktop interfaces; standard-library sockets and threads provide the messenger transport and relay; the repository's PNG codec performs lossless least-significant-bit embedding and extraction.

## Users

The primary user is someone who wants to exchange short text with two or more participants while making the image carrier visible and understandable. They may run both clients and the relay on one computer for learning or connect desktop clients to a relay on a trusted local network.

A secondary user wants a local, no-command-line workbench for hiding UTF-8 text or arbitrary file bytes in a PNG and recovering them later.

## Product Purpose

SIMP is an image-message protocol made tangible as a desktop conversation. Every application event crosses the messenger connection as a steganographic PNG; the receiving client extracts and validates the envelope, then lets the reader reveal its text beside a thumbnail of the image that carried it. Success means two clients can join the same room, exchange readable messages, and see that the PNG is the transport rather than decoration.

The Hide/Recover workbench remains an explicitly named secondary utility for direct, local inspection of the same steganography pipeline; it is never the default application.

## Positioning

SIMP is a dependency-free learning and experimentation tool for deliberate image-carried communication. It is transparent about its boundary: steganography conceals bytes but does not encrypt, authenticate, or protect their integrity. The relay decodes envelopes to validate and route them, so it is not a zero-knowledge intermediary.

The product never executes recovered content. The local workbench makes no network calls; the messenger contacts only the relay address the user enters.

## Operating Context

The primary flow uses two or more messenger windows and one relay. A user chooses a display name, room, relay host and port, and reusable PNG carrier; they may start a relay inside one client or run `python -m simp relay` separately. Participants using the same room receive the same encoded PNG bytes and can reveal the validated envelope text within the conversation.

The secondary workbench runs independently. It lets a user choose a local carrier, inspect capacity, hide text or a file in a new PNG, and recover inert bytes from a compatible image.

## Capabilities and Constraints

### Image messenger

- Join, message, leave, acknowledgement, and error envelopes use the versioned `SIMP/1` format; legacy `LATTICE-WIRE/1` envelopes remain readable.
- Every application envelope is embedded in a PNG. TCP contributes only a four-byte, network-order frame length.
- The relay validates and routes images by room, rejects duplicate display names and client-forged control frames, and supports multiple concurrent participants.
- Sender and room identifiers are 1-32 characters and may contain letters, numbers, spaces, dots, dashes, and underscores.
- Message text is UTF-8 and limited to 16 KiB before envelope overhead. The selected carrier must have enough steganographic capacity for the complete envelope.
- New envelopes expire after 24 hours, lifetimes cannot exceed seven days, and the relay refuses expired images.
- Transport frames are limited to 32 MiB and must begin with a PNG signature.
- Conversation history exists only in the running client and is capped at 100 rendered records; there is no server persistence.
- The relay caps total and per-room participation, rate-limits frames, and expires stalled handshakes and idle connections.
- The protocol provides no encryption, authentication, delivery receipt, moderation, discovery, or production-grade internet-facing hardening.

### Hide/Recover workbench

- Input images must be 8-bit grayscale, RGB, grayscale-alpha, or RGBA PNG files; paletted and 16-bit PNGs are unsupported.
- PNG input, decoded image size, dimensions, chunk boundaries, checksums, and scanline filters are validated before pixel processing.
- Payloads may be UTF-8 text or arbitrary file bytes.
- Encoded output remains a PNG and includes the codec's internal marker and payload length.
- Extracted binary data is saved only to a user-chosen path and is never opened or executed.
- Capacity is checked before writing, and the source carrier is never overwritten.

## Evidence on Hand

- `simp/app.py` is the primary messenger entry point, `simp/chat.py` implements its UI, and `simp/workbench.py` is the optional Hide/Recover utility.
- `simp/wire_protocol.py`, `simp/transport.py`, `simp/wire_client.py`, and `simp/relay.py` implement the envelope, PNG-only framing, connected client, and multi-room relay.
- `tests/test_wire.py` covers codec memory operations, malformed inputs, envelope validation and compatibility, socket framing, room isolation, duplicate names, control-frame rejection, two-client exchange, and three-client delivery.
- `.impeccable/review/conversation-hardened.png` is the final reviewed messenger capture.
- `examples/sample.png` and `examples/hidden.png` are local codec fixtures.

## Product Principles

- Make the protocol visible: keep revealed text paired with the PNG that carried it.
- Keep connecting, choosing a carrier, and sending a message understandable without a command line.
- Preserve the image-only application boundary; do not add a parallel plaintext message path.
- State capacity, connection, and safety limits in plain language before users lose work.
- Keep room routing ready for more than two clients even when the common demonstration uses Alice and Bob.
- Preserve the local Hide/Recover workbench as a focused secondary tool rather than folding its file workflow into conversation.
- Never imply that concealment is encryption or that the relay cannot read an envelope.

## Accessibility & Inclusion

Both interfaces should remain fully keyboard operable, retain visible focus, and avoid communicating state with color alone. The messenger supports Ctrl+K to connect or disconnect, Ctrl+O to choose a carrier, Ctrl+Enter to send, and Alt+S to focus live status. Labels and status text must remain legible at common Windows display scaling settings, and errors must be written as actionable sentences.
