# Console Component System Contract

Date: 2026-06-30

This document locks visual and component expectations for implementation
review. Design references win for layout, spacing, color, shadows, typography,
component shape, active states, icon usage, visual density, and responsive
hierarchy.

## Design Anchors

- Static pages:
  `/home/ubuntu/leo/projects/autoclaw/references/frontend_design/pages`.
- Mirror pages: `/home/ubuntu/leo/design/autoclaw-v2-ui/pages`.
- Shared CSS and shell script: `shared-ui.css`, `shared-shell.js`.
- Direction docs:
  `references/frontend_design/design/DESIGN.md` and `navigation.md`.
- Page charters:
  `references/frontend_design/feature-charters/pages/*.md`.

Design pages must be served through `python3 -m http.server` and inspected in
the browser. PNGs and source reads support review but are not a replacement for
browser inspection.

## Shell And Navigation

- The console shell uses a warm paper background, dense operational content,
  left rail/top breadcrumb structure, one main page surface, and compact page
  controls.
- Tasks is the runtime entry point. Task Detail, Human Requests, and Command
  Runs are task-scoped under Tasks.
- Definitions, Task Start, and Definition Editor are authoring surfaces.
- Implementation reviews must inspect actual router/nav/source before judging
  active states. Do not infer active behavior from screenshots alone.
- At narrow widths, the prototype keeps navigation visible and wraps/stacks
  rather than hiding the full shell behind an unreviewed pattern.

## Tokens And Density

Design direction anchors:

- Background: `#F5F3F1`.
- Primary surface: `#FDFCFB`.
- High surface/container: `#EFECE9`.
- Low surface: `#FFFFFF`.
- Border tones: `#E5E7EB` and `#D1D5DB`.
- Primary blue: `#3B82F6`.
- Primary container: `#EFF6FF`.
- On-primary text: `#1E40AF`.
- Secondary container: `#E0E7FF`.
- On-secondary text: `#3730A3`.

The implementation should reuse existing app tokens and primitives where they
match the design. Do not introduce a separate visual language, decorative
orbs, marketing hero layout, oversized cards, or low-density dashboard chrome.

## Components

Required component behavior:

- Buttons, icon buttons, segmented controls, tabs, checkboxes/toggles, inputs,
  selects/menus, textareas, disclosure rows, status chips, empty states, error
  states, modals, drawers, and page cards must have visible focus states.
- Dense rows should not resize on hover, focus, or status changes.
- Modals must trap focus while open, restore focus on close, and present
  destructive actions distinctly.
- Page cards and panels should follow the served design shape and spacing; do
  not nest decorative cards inside cards.

## Icons

The current console uses `lucide-react`. Static design pages use Material
Symbols names as prototype intent only.

Rules:

- Prefer current lucide icons already used by the console.
- Add a new lucide icon only when it is a direct semantic match for a design
  affordance and review approves it.
- Do not add Material Symbols or unsupported icon font dependencies.
- Do not invent icons or chrome for unsupported backend states.

## Responsive And Accessibility Review

Every implementation scope must compare desktop and narrow viewports against
served design HTML and PNG references. Review must include:

- shell/nav wrapping and active states;
- visible and keyboard focus;
- modal focus trap and restore;
- form label/error association;
- row/action hit targets;
- no overlapping text or controls;
- no hidden required backend state at narrow width.
