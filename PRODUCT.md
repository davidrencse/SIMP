# Product

<!-- impeccable:product-schema 1 -->

## Platform

desktop

## Stack

Python with the standard-library Tkinter GUI toolkit, confirmed by the user as a local desktop app.

## Users

The primary user is someone working locally with PNG files who wants to hide text or a file inside an image and later recover it without using a command line.

## Product Purpose

Provide a clear, local interface for the existing PNG least-significant-bit steganography pipeline. Success means a user can select a source image, understand whether their payload fits, create an encoded PNG, and recover embedded data with unambiguous feedback.

## Positioning

The app performs lossless, local-only PNG steganography using the repository's dependency-free codec. It does not upload files, execute recovered data, or turn images into executable delivery mechanisms.

## Operating Context

The app runs on the user's desktop and works with local files. Its two core tasks are hiding text or a selected file in a PNG and recovering that data from a compatible PNG. Technical capacity and byte-count information should be available without making the primary workflow feel like a developer console.

## Capabilities and Constraints

- Input images must be 8-bit grayscale, RGB, grayscale-alpha, or RGBA PNG files; paletted PNGs are not supported by the current codec.
- Payloads may be UTF-8 text or arbitrary files.
- Encoded output remains a PNG and includes an internal marker and payload length.
- Extracted binary data is saved to a user-chosen path; the app never executes it.
- All processing stays on the local machine.
- The UI should use only Python standard-library dependencies.

## Evidence on Hand

- `steg.py` contains the working encode/decode pipeline and CLI.
- `sample.png` and `hidden.png` are available as local test fixtures.
- No verified commercial claims, testimonials, or external brand assets exist.

## Product Principles

- Keep the primary Hide and Recover tasks obvious.
- Explain capacity and errors in plain language before users lose work.
- Make local-only processing and non-execution behavior explicit.
- Preserve the image pipeline's existing formats and validation rules.
- Treat technical detail as supporting evidence, not the main interface.

## Accessibility & Inclusion

The interface should be fully keyboard operable, retain visible focus, avoid color-only status communication, and remain usable at common Windows display scaling settings.
