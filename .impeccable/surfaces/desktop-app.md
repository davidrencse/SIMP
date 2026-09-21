# Desktop messenger surface

## Status

Shipped after finish review. The final reviewer disposition is **ship**, with all 20 protocol and relay tests passing.

## Primary target

`simp/app.py` (entry point) and `simp/chat.py` (messenger UI)

Related implementation: `simp/wire_protocol.py`, `simp/transport.py`, `simp/wire_client.py`, and `simp/relay.py`.

## Approved artifact

`.impeccable/review/conversation-hardened.png`

## Mode

Operate. The user connects to a room, understands the image transport, and exchanges decoded text without managing protocol internals.

## Direction contract

**THESIS:** SIMP is a darkroom correspondence desk. The conversation is calm and readable, while every record retains visible proof of the PNG that carried it. It is neither a generic chat skin nor a hacker console.

**OWN-WORLD:** A near-black connection rail sits beside an off-white reading room. Libre Caslon Text gives the identity and room title editorial authority; Segoe UI carries conversation; Consolas reports carrier, time, and protocol facts. Square fields, hairline rules, and image proof tiles create structure without cards, shadows, gradients, or ornamental chrome.

**STORY:** The user names themselves and a room, points to a relay, chooses a reusable carrier, and connects. Join and leave images appear as compact system records. A sent message is embedded into a fresh PNG, routed to peers in the room, validated, and offered as an image record whose text can be revealed on request. Capacity copy beneath the composer explains whether the complete envelope fits before sending.

**FIRST VIEWPORT:** The shipped window opens at 1280 x 820 with a fixed 310-pixel black connection rail and a flexible conversation pane. The reading room has a 108-pixel header, a scrollable transcript, and a persistent bottom composer. At the 880 x 620 minimum, the same hierarchy remains intact rather than switching to a separate mobile composition.

**FORM:** The signature composition is the black rail / white room split. The signature record pairs one 224 x 148 image proof tile with sender, local time, a `Reveal` action, and text shown below the proof on request. System events use a smaller image thumbnail crossed by a hairline into the event text.

**BEHAVIOR:** Connect operations, sends, image decoding, and local relay work stay off the Tkinter UI thread. Connection fields and carrier selection lock while connected. The composer enables sending only when connected, non-empty, within protocol validation, and within carrier capacity. Duplicate names, invalid ports, connection loss, oversized messages, invalid carriers, and relay-start failures produce visible, actionable status text.

**KEYBOARD:** Ctrl+K connects or disconnects, Ctrl+O chooses the carrier, Ctrl+Enter sends, and Alt+S focuses live status. Native focus remains visible on fields, buttons, and status.

**BOUNDARY:** Steganography conceals but does not encrypt. The relay decodes each envelope for validation and room routing. The surface must never suggest end-to-end secrecy, persistent history, identity verification, or a plaintext fallback channel.

## Secondary surface

`simp/workbench.py` remains the original local Hide/Recover utility. Its Photographic Proofing Bench direction, warm paper palette, brick action, sage capacity state, dominant carrier preview, crop marks, and wide-bench/compact-docket behavior remain supported. It is explicitly separate and must never displace the messenger's black-and-white correspondence desk as the primary product surface.

## Finish evidence

- Final capture: `.impeccable/review/conversation-hardened.png`.
- Automated verification: unit and multi-client integration tests in `tests/test_wire.py`.
- Two-client exchange verifies the received PNG is byte-for-byte identical to the sent PNG and that its decoded text is readable.
- Three-client delivery verifies the same PNG reaches both peers.
- Room isolation and duplicate-name behavior are covered.
- Disposition: ship.
