---
name: Lattice
description: A calm photographic proofing bench for local PNG steganography.
colors:
  paper: "#E7E6DD"
  paper-light: "#F3F1E9"
  ink: "#26241F"
  muted-ink: "#595750"
  rule: "#AAA89F"
  sage: "#75877B"
  sage-dark: "#53685C"
  brick: "#A74838"
  brick-active: "#8C382D"
  field-white: "#FBFAF5"
  error: "#8E2F2A"
  preview-placeholder: "#D8D8D0"
  secondary-active: "#D8D6CD"
  capacity-track: "#D0CEC5"
typography:
  display:
    fontFamily: "Libre Caslon Text, Book Antiqua, serif"
    fontSize: "42pt"
    fontWeight: 400
  station-title:
    fontFamily: "Libre Caslon Text, Book Antiqua, serif"
    fontSize: "12pt"
    fontWeight: 400
  action:
    fontFamily: "Libre Caslon Text, Book Antiqua, serif"
    fontSize: "11pt"
    fontWeight: 400
  body:
    fontFamily: "Segoe UI, sans-serif"
    fontSize: "9pt"
    fontWeight: 400
  carrier-label:
    fontFamily: "Segoe UI Semibold, Segoe UI, sans-serif"
    fontSize: "10pt"
    fontWeight: 600
  data:
    fontFamily: "Consolas, monospace"
    fontSize: "9pt"
    fontWeight: 400
  annotation:
    fontFamily: "Segoe Print, cursive"
    fontSize: "11pt"
    fontWeight: 400
rounded:
  square: "0px"
spacing:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
  control-x: "15px"
  station-y: "17px"
  station-x: "20px"
  action-depth: "32px"
components:
  button-primary:
    backgroundColor: "{colors.brick}"
    textColor: "{colors.field-white}"
    typography: "{typography.action}"
    rounded: "{rounded.square}"
    padding: "8px 15px"
  button-primary-active:
    backgroundColor: "{colors.brick-active}"
    textColor: "{colors.field-white}"
    typography: "{typography.action}"
    rounded: "{rounded.square}"
    padding: "8px 15px"
  button-secondary:
    backgroundColor: "{colors.paper-light}"
    textColor: "{colors.ink}"
    typography: "{typography.data}"
    rounded: "{rounded.square}"
    padding: "6px 15px"
  mode-selected:
    backgroundColor: "{colors.brick}"
    textColor: "{colors.field-white}"
    typography: "{typography.data}"
    rounded: "{rounded.square}"
  mode-unselected:
    backgroundColor: "{colors.paper-light}"
    textColor: "{colors.ink}"
    typography: "{typography.data}"
    rounded: "{rounded.square}"
  text-field:
    backgroundColor: "{colors.field-white}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.square}"
  station:
    backgroundColor: "{colors.paper-light}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "17px 20px"
  proof-frame:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.muted-ink}"
    rounded: "{rounded.square}"
---

# Design System: Lattice

## Overview

**Creative North Star: "The Photographic Proofing Bench"**

Lattice presents local steganography as careful photographic handling. The carrier image is the artifact under inspection, given most of the window and surrounded by the familiar evidence of a proofing bench: matte stock, hairline rules, crop marks, measurement notes, and a restrained caption rail.

The interface is calm, exact, and visibly local. Editorial type gives the tool a human title and decisive actions; monospaced copy carries file facts and safety assurances; handwritten annotations make the carrier metadata feel observed rather than instrument-panel dense. The system rejects hacker-console theatrics and generic stacked-file-form composition while preserving obvious native controls, visible focus, and direct keyboard operation.

**Key Characteristics:**

- The carrier photograph remains visually dominant.
- Warm matte paper and near-black ink establish the default visual field.
- Brick red is reserved for the selected mode and primary action.
- Sage marks safe local status and usable capacity.
- Hairlines, crop marks, captions, and measurements organize the interface without elevation.
- Wide layouts use one horizontal processing bench; compact layouts turn that bench into a vertical docket beside the proof.

## Colors

The palette is a warm proof-paper neutral field with one mineral red action color and quiet botanical status cues.

### Primary

- **Proof Brick:** The only assertive accent. Use it for the selected mode, the selected payload kind, the primary processing action, and focused editable-field outlines.
- **Pressed Brick:** Use only for the active state of primary controls.

### Secondary

- **Muted Sage:** Use for capacity fill when a payload fits.
- **Local Sage:** Use for the local-only status dot and successful status text.

### Neutral

- **Matte Proof Paper:** The window and proof-frame ground.
- **Light Bench Paper:** The processing bench, stations, and unselected controls.
- **Near-Black Ink:** Primary copy, crop marks, icons, and focus indication.
- **Graphite Note:** Supporting copy, captions, metadata, and idle status.
- **Pencil Rule:** One-pixel frames, separators, and resting control outlines.
- **Field White:** Editable and read-only field interiors plus text on brick actions.
- **Empty Proof Gray:** The preview field before an image can be rendered.
- **Pressed Paper:** The active state for secondary controls.
- **Capacity Track:** The unfilled capacity rail.
- **Error Oxide:** Oversize capacity fill and error status text.

### Named Rules

**The One Red Action Rule.** Proof Brick identifies the current choice or the next decisive action; it does not decorate headings, rules, metadata, or the photograph.

**The Paper, Not Chrome Rule.** Large regions stay within the two paper neutrals. Structure comes from ink, spacing, and hairlines rather than tinted panels.

## Typography

**Display Font:** Libre Caslon Text (with Book Antiqua fallback)
**Body Font:** Segoe UI (with the native sans-serif fallback)
**Label/Mono Font:** Consolas

**Character:** The type system pairs a literary proof-title serif with quiet Windows-native reading text and technical monospace. Segoe Print appears only in carrier-side annotations, adding the human trace of a marked proof without turning the workbench whimsical.

### Hierarchy

- **Display** (regular, 42pt): The Lattice wordmark only.
- **Station title** (regular, 12pt desktop / 10pt compact): Processing-stage headings such as Payload, Capacity, and Output.
- **Action** (regular, 11pt): Primary processing controls.
- **Carrier label** (semibold, 10pt): The label directly above the proof.
- **Body** (regular, 9pt): Editable text, capacity explanation, filenames, and supporting content.
- **Data label** (regular, 9pt; 7–8pt for dense notes): Mode labels, safety copy, captions, button labels, and compact operational details.
- **Annotation** (regular, 11pt desktop / 9pt compact): Image dimensions, format, capacity, and suitability in the proof margin.

### Named Rules

**The Three Voices Rule.** Serif names and commits, monospace reports and assures, sans-serif supports input; handwriting belongs only beside the carrier proof.

## Layout

The native window opens at 1536 × 985 and does not shrink below 1200 × 800. At 1320 pixels wide and above, the composition is a wide proof: the outer proof frame occupies 97% of the window width and 61% of its height, while a four-station bench spans 96% beneath it. The carrier canvas itself uses 87% of the window width and 53% of its height, leaving a narrow handwritten metadata margin.

Below 1320 pixels, the proof and docket share the window side by side. The proof frame occupies 68% of the width, the visible carrier canvas 60%, the annotation strip 5.5%, and the bench becomes a 26%-wide vertical sequence on the right. Controls keep their native text sizes and the photograph remains substantial; the design reflows instead of scaling the entire interface down.

The wide bench distributes Payload, Capacity, Output, and Action at 27:25:25:23. Stations use 20-pixel horizontal and 17-pixel vertical padding; the compact docket uses 12 and 8 pixels. Hairline separators divide stages, while 4–12 pixel intervals handle local control rhythm.

**The Proof Leads Rule.** New layouts may change the bench flow, but they must not demote the carrier to a thumbnail or let controls become the largest visual object.

## Elevation & Depth

The system is flat by design and uses no shadows. Depth comes from tonal layering between Matte Proof Paper and Light Bench Paper, white field insets, one-pixel pencil rules, and the photographic carrier itself. Active state is expressed by color and focus outlines, not lift or motion.

### Named Rules

**The Flat Proof Rule.** Do not introduce drop shadows, floating cards, glass effects, or simulated elevation; use a paper change or a one-pixel rule when a boundary is necessary.

## Shapes

Every native surface and control is square-cornered. Frames, fields, switches, meter tracks, buttons, and crop marks use orthogonal geometry with zero radius. One-pixel rules establish most boundaries; the proof canvas uses a two-pixel focusable outline and overlaid registration marks. The only round shape is the small local-status dot.

**The Cut-Paper Rule.** Keep component silhouettes rectangular and crisp. Rounded cards, pills, and capsule toggles are outside this system.

## Components

### Buttons

- **Shape:** Flat, square, and one-pixel outlined at rest.
- **Primary:** Proof Brick with Field White text, Libre Caslon Text at 11pt, 15-pixel horizontal padding, and a four-square registration stamp on large actions. The desktop primary action gains 32 pixels of internal vertical depth; compact mode reduces that extra depth to 5 pixels.
- **Active / Focus:** Pressed Brick marks activation. Keyboard focus changes the outline to Near-Black Ink and remains visible.
- **Secondary:** Light Bench Paper with Near-Black Ink monospaced text. Its active surface shifts to Pressed Paper.

### Mode Switches

- **Style:** Two equal native buttons sit inside a one-pixel Pencil Rule frame. The chosen mode or payload kind uses Proof Brick and Field White; the alternative remains on Light Bench Paper.
- **Behavior:** Hide / Recover and Text / File use the same binary grammar. Mode changes rebuild the processing bench with the corresponding native controls.

### Cards / Containers

- **Corner Style:** Square.
- **Background:** Light Bench Paper over Matte Proof Paper.
- **Shadow Strategy:** None.
- **Border:** One-pixel Pencil Rule around the complete bench; one-pixel vertical separators in wide mode and horizontal separators in the compact docket.
- **Internal Padding:** 20 × 17 pixels in wide stations and 12 × 8 pixels in compact stations.

### Inputs / Fields

- **Style:** Field White, Near-Black Ink, square corners, flat relief, and a one-pixel Pencil Rule outline. Text entry uses Segoe UI at 9pt; recovered data uses Consolas at 9pt.
- **Focus:** Editable fields change the outline to Proof Brick. The carrier canvas changes its outline to Proof Brick on focus and supports mouse, Enter, and Space activation.
- **Read-only / Disabled:** Read-only output fields keep the same white surface for continuity. Disabled recovered previews preserve the white field and dark text instead of looking unavailable.

### Capacity Meter

- **Style:** A 18-pixel-high desktop or 12-pixel-high compact rail on Capacity Track.
- **State:** Muted Sage fills the used proportion when the payload fits; Error Oxide fills the rail when it does not. Text below always states bytes, percentage, estimated capacity, remaining space, and suitability, so color never carries the result alone.

### Proof Frame

- **Style:** A focusable image canvas inside an outer ruled field, with paired light-and-ink crop marks and central registration ticks. A narrow handwritten margin reports dimensions, PNG mode, capacity, and carrier suitability.
- **Behavior:** Clicking, pressing Enter, or pressing Space opens the native PNG chooser. The preview uses a cover crop and swaps among prepared source plates only to maintain the approved framing at shipped widths.

### Station Heading

- **Style:** A small line-drawn file, capacity, or registration icon precedes a Libre Caslon Text title. A one-pixel rule underneath separates the heading from its station controls.

## Do's and Don'ts

### Do:

- **Do** preserve the carrier image as the dominant visual artifact in both wide and compact compositions.
- **Do** reserve Proof Brick for selection, editable focus, and the primary processing action.
- **Do** pair every capacity or status color with explicit text.
- **Do** keep keyboard focus visible and preserve Alt+H, Alt+R, Ctrl+O, and Ctrl+Enter operation.
- **Do** use paper tones, rules, crop marks, captions, and measurement notes to express the photographic proofing world.

### Don't:

- **Don't** introduce terminal green, neon cyber styling, scan-line effects, or hacker-console language.
- **Don't** add shadows, rounded cards, pill controls, gradients, or decorative glass effects.
- **Don't** spread brick red across headings, borders, metadata, or passive decoration.
- **Don't** use handwriting anywhere except the proof's measurement and suitability notes.
- **Don't** shrink the carrier into a token thumbnail when the window narrows; reflow the bench into the vertical docket.
