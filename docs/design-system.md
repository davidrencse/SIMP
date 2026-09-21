---
name: SIMP
description: A monochrome correspondence desk for image-carried messages, with a photographic proofing workbench as its secondary dialect.
colors:
  black: "#080808"
  ink: "#111111"
  white: "#F7F7F4"
  composer-paper: "#ECECE8"
  rule-light: "#DDDDD8"
  metadata: "#8A8A84"
  secondary-text: "#565652"
  workbench-paper: "#E7E6DD"
  workbench-paper-light: "#F3F1E9"
  workbench-ink: "#26241F"
  workbench-rule: "#AAA89F"
  workbench-brick: "#A74838"
  workbench-brick-active: "#8C382D"
  workbench-sage: "#75877B"
  workbench-error: "#8E2F2A"
typography:
  brand:
    fontFamily: "Libre Caslon Text, Book Antiqua, serif"
    fontSize: "29pt"
    fontWeight: 400
  room-title:
    fontFamily: "Libre Caslon Text, Book Antiqua, serif"
    fontSize: "22pt"
    fontWeight: 400
  empty-title:
    fontFamily: "Libre Caslon Text, Book Antiqua, serif"
    fontSize: "28pt"
    fontWeight: 400
  body:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "11pt"
    fontWeight: 400
  field:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "10pt"
    fontWeight: 400
  label:
    fontFamily: "Segoe UI Semibold, Segoe UI, sans-serif"
    fontSize: "9pt"
    fontWeight: 600
  data:
    fontFamily: "Consolas, monospace"
    fontSize: "9pt"
    fontWeight: 400
  workbench-display:
    fontFamily: "Libre Caslon Text, Book Antiqua, serif"
    fontSize: "42pt"
    fontWeight: 400
  workbench-annotation:
    fontFamily: "Segoe Print, cursive"
    fontSize: "11pt"
    fontWeight: 400
rounded:
  square: "0px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "14px"
  xl: "20px"
  rail: "28px"
  header: "36px"
  transcript: "38px"
components:
  button-connection:
    backgroundColor: "{colors.white}"
    textColor: "{colors.black}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "12px 13px"
  button-action:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "16px 13px"
  dark-field:
    backgroundColor: "{colors.black}"
    textColor: "{colors.white}"
    typography: "{typography.field}"
    rounded: "{rounded.square}"
    padding: "7px 0px"
  composer:
    backgroundColor: "{colors.composer-paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "20px 26px"
  proof-tile:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    typography: "{typography.data}"
    rounded: "{rounded.square}"
    size: "126px 94px"
  workbench-primary:
    backgroundColor: "{colors.workbench-brick}"
    textColor: "{colors.white}"
    rounded: "{rounded.square}"
    padding: "8px 15px"
  workbench-station:
    backgroundColor: "{colors.workbench-paper-light}"
    textColor: "{colors.workbench-ink}"
    rounded: "{rounded.square}"
    padding: "17px 20px"
---

# Design System: SIMP

## Overview

**Creative North Star: "The Darkroom Correspondence Desk"**

SIMP's primary visual world turns an unusual protocol into an ordinary, legible act of correspondence. A dense black connection rail holds setup and boundary information; an off-white reading room gives the decoded conversation space. Every message retains visible image evidence, so the protocol is explained by the composition itself instead of decorative networking imagery.

The system is editorial, exact, and deliberately quiet. Serif type names the product and place, sans-serif type carries human speech, and monospace reports the image and wire facts. The original Hide/Recover workbench remains a secondary photographic dialect: warmer paper, brick actions, sage capacity marks, and handwritten proof annotations belong there, not in the messenger.

**Key Characteristics:**

- A black setup rail and light reading room create the messenger's defining split.
- Every decoded message is visibly paired with its PNG proof tile.
- Square controls, one-pixel rules, and tonal blocks replace elevation.
- Serif establishes identity, sans-serif carries conversation, and monospace reports protocol facts.
- The workbench keeps its warm proof-paper system as an intentional secondary dialect.
- Native keyboard and focus behavior remain visible and understandable.

## Colors

The messenger is almost monochrome: carbon black, reading white, and a narrow range of warm grays. The workbench's mineral red and sage are reserved for that secondary surface.

### Primary

- **Darkroom Black:** The messenger rail and its native input surfaces; it is the product's strongest visual anchor.
- **Reading White:** The conversation room, light connection action, and reversed text on dark controls.
- **Correspondence Ink:** Conversation text, proof tiles, composer outline, and the send action.

### Secondary

- **Proof Brick:** The workbench's selected mode, editable focus, and primary processing action only.
- **Muted Sage:** The workbench's fitting-capacity and safe local-status cue only.
- **Error Oxide:** The workbench's oversize capacity and error cue, always paired with text.

### Neutral

- **Composer Paper:** The persistent message-composer band.
- **Light Rule:** Header divisions, event leaders, and light active feedback.
- **Metadata Gray:** Timestamps, carrier facts, protocol captions, and inactive status marks.
- **Secondary Graphite:** Explanatory copy and normal status text.
- **Workbench Proof Paper:** The warm ground of the Hide/Recover surface.
- **Workbench Light Paper:** Workbench stations and unselected controls.
- **Workbench Ink:** Workbench copy, crop marks, and focus indication.
- **Workbench Rule:** Workbench frames and separators.

### Named Rules

**The Two Rooms Rule.** Messenger setup lives on Darkroom Black and conversation lives on Reading White; do not blur the split with intermediate cards or tinted dashboards.

**The Workbench Color Boundary Rule.** Brick and sage communicate processing state in `simp/workbench.py`; they do not become messenger accents.

## Typography

**Display Font:** Libre Caslon Text (with Book Antiqua fallback)  
**Body Font:** Segoe UI (with the native sans-serif fallback)  
**Label/Mono Font:** Consolas

**Character:** The pairing is literary without nostalgia and technical without console theater. The serif establishes identity and location, Segoe UI keeps setup and decoded speech familiar, and Consolas makes image evidence scannable.

### Hierarchy

- **Brand** (regular, 29pt): The SIMP mark in the messenger rail.
- **Room title** (regular, 22pt): The connected room and local identity in the conversation header.
- **Empty title** (regular, 28pt): The single first-run statement in an empty transcript.
- **Conversation body** (regular, 11pt): Decoded messages, empty-state explanation, and composer input.
- **Setup value** (regular, 10pt): Name, room, relay, and port values in the connection rail.
- **Control** (semibold, 9pt): Buttons, sender names, and compact field labels.
- **Operational data** (regular, 8-9pt): Message-image size, message capacity, event time, expiry, protocol captions, and the brand descriptor.
- **Workbench display** (regular, 42pt): The secondary workbench wordmark only.
- **Workbench annotation** (regular, 9-11pt): Carrier facts beside the workbench proof only.

### Named Rules

**The Three Voices Rule.** Serif names, sans-serif speaks, and monospace proves; do not use monospace for decoded conversation or serif for dense setup copy.

## Layout

The messenger opens at 1280 x 820 and does not shrink below 880 x 620. Its 310-pixel connection rail is fixed while the reading room expands. The room header is 108 pixels high; the transcript scrolls independently; the composer stays pinned to the bottom with 26-pixel horizontal and 20-pixel vertical padding.

The rail uses 28-pixel side insets. The header uses 36-pixel side insets. Transcript records use 38-pixel side insets and rely on open white space rather than card bounds. A full message pairs a 224 x 148 proof tile with a compact reveal action; system events reduce the thumbnail to 42 x 30 and bridge it to event copy with a one-pixel rule.

The transcript supports sender-side mirroring: received image records lead from the left and local records lead from the right. Text alignment follows the sender side. The 880-pixel minimum preserves this composition; there is no mobile or collapsed-rail variant.

The secondary workbench retains its independent responsive rule: a wide horizontal processing bench at 1320 pixels and above, then a proof-plus-docket composition below that threshold, with a 1050 x 700 minimum.

**The Evidence Travels With the Text Rule.** A conversation record may mirror by sender, but its proof tile, sender, time, reveal action, and revealed copy stay together.

## Elevation & Depth

The system is flat and uses no shadows. Depth comes from the black/white field split, the slightly darker composer band, image content, and one-pixel rules. Focus and active states use outline and tonal inversion rather than movement or lift.

### Named Rules

**The Flat Correspondence Rule.** Do not introduce shadows, floating cards, translucency, or glass effects; change tone or draw one crisp rule when a boundary is necessary.

## Shapes

Fields, buttons, proof tiles, composer frames, workbench stations, and mode switches use square corners. The messenger connection indicator is the only round status form. Image thumbnails remain rectangular and are never masked into avatars or bubbles.

**The Unmasked Image Rule.** A carrier is evidence, not an avatar: keep its rectangular silhouette and show its PNG size directly beneath or beside it.

## Components

### Connection Rail

- **Structure:** A fixed Darkroom Black column with brand, connection fields, carrier control, connection actions, current status, and a bottom safety note.
- **Fields:** Black interiors, Reading White text, one-pixel Secondary Graphite resting outlines, and white focus outlines.
- **Status:** A small round mark may reinforce connection state, but adjacent text must name the state or current action.

### Buttons

- **Connection action:** Reading White on Darkroom Black, flat and square, with semibold 9pt text.
- **Message action:** Correspondence Ink with Reading White text inside the composer.
- **Rail secondary:** Darkroom Black with Reading White text and a one-pixel outline.
- **Active / Focus:** Use Light Rule or Secondary Graphite for active tone and retain a visible one-pixel native focus outline.
- **Disabled:** Keep the silhouette stable and use a muted color that retains readable contrast on its surface.

### Conversation Header

- **Style:** Room / name in 22pt serif, participant count and transport status below, and `PNG FIRST / TEXT ON REQUEST` aligned at the far edge in monospace.
- **Boundary:** A single Light Rule separates the header from the transcript.

### Image Message

- **Proof tile:** A 224 x 148 Correspondence Ink block with a carrier thumbnail above a `PNG` plus byte-size label.
- **Reveal:** A focused `Reveal` control initially keeps text out of sight; the validated 11pt message copy appears below the proof only on request.
- **Direction:** Received records lead left; local records lead right. Mirroring must not change the information hierarchy.

### System Event

- **Style:** A 42 x 30 image thumbnail, a one-pixel leader, event sentence, and local time.
- **Use:** Join and leave events. Do not inflate them to the visual weight of human messages.

### Composer

- **Container:** Composer Paper with 26 x 20 pixel padding.
- **Input:** Reading White, Correspondence Ink, square one-pixel outline, 11pt Segoe UI, and a three-line default height.
- **Capacity:** Monospace copy reports text bytes, complete hidden-envelope bytes, and fit state. Send remains disabled until the user is connected and the envelope fits.

### Workbench Proof and Stations

- **Scope:** Secondary surface only.
- **Proof:** The carrier remains dominant inside a ruled frame with crop marks and a handwritten measurement margin.
- **Stations:** Workbench Light Paper with one-pixel Workbench Rule boundaries; Proof Brick marks selection and the primary action, while Muted Sage or Error Oxide report capacity alongside explicit text.

## Do's and Don'ts

### Do:

- **Do** keep revealed message text attached to the PNG that carried it.
- **Do** keep connection setup in the black rail and conversation in the light room.
- **Do** use monospace for image, capacity, timestamp, and protocol evidence.
- **Do** preserve visible focus and Ctrl+K, Ctrl+O, and Ctrl+Enter operation in the messenger.
- **Do** keep the warm proof-paper, brick, sage, crop-mark, and handwritten language confined to the secondary workbench.
- **Do** pair every status color or indicator with explicit text.

### Don't:

- **Don't** render revealed messages as detached chat bubbles or hide the carrier evidence.
- **Don't** add terminal green, neon cyber styling, scan lines, gradients, glass, shadows, rounded cards, or pill controls.
- **Don't** use people avatars; the image carrier is the record's visual identity.
- **Don't** use Proof Brick or Muted Sage as messenger decoration.
- **Don't** imply encryption, relay blindness, identity verification, delivery guarantees, or persistent history.
- **Don't** collapse the Hide/Recover workbench into the conversation composer; keep the two task models distinct.
