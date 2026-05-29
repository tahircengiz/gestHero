# Technical Journal

## 2025-12-29

- Created this journal to track all work.
- GitHub private repo setup requested; using default repo name `prj_GestureHero` unless changed.
- Initialized local git repository and renamed default branch to `main`.
- Started `gh auth login` flow; device code issued and awaiting user completion.
- Verified SSH authentication to GitHub works for user `tahircengiz`.
- PAT-based `gh auth login` failed due to missing `read:org` scope; need token with that scope or use API workaround.
- Created private GitHub repo `tahircengiz/prj_GestureHero` via API and added `origin` SSH remote.
- Committed `technical_journey.md` and pushed initial commit to `main`.
- Removed temporary `testfile`.
- Added `build_extension.py` generator script for the MV3 extension scaffolding.
- Prepared `gestHero.svg` to be tracked in git.
- Committed and pushed the build script, journal update, and SVG asset to `main`.
- Extended `build_extension.py` with link-based actions and tab switching actions.
- Expanded the gesture engine with advanced actions, presets, import/export, visual customization, and per-site disabling.
- Added configurable mouse button selection for gesture activation.
- Fixed disabled-sites regex in generated content script to prevent runtime syntax error.
- Suppressed context menu on gesture button and added gesture cancellation on blur/contextmenu.
- Adjusted contextmenu handling to avoid cancelling gestures prematurely.
- Updated build script to copy `gestHero.svg` into the extension and use it as the icon.
- Added SVG-to-PNG conversion for icons with fallbacks to built-in PNGs.
- Allowed JSON backups without strict MIME type in the options import control.
- Added corner smoothing settings for rounded gesture turns (tolerance and min length).
- Switched to segment-based direction commits to reduce duplicate tokens like UUURRR.
- Added optional collapsing of repeated direction steps before matching gestures.
- Tightened direction detection using axis-based thresholds inspired by existing gesture extensions.
- Made repeated-direction collapsing mandatory to avoid U U / R R duplication.
- Added debug logging toggle with export/clear controls for gesture analysis.
- Made debug log export/clear work from the options page without needing the same active tab.
- Auto-save debug toggle and show status when no events are collected.
- Added diagonal-to-cardinal simplification for turn smoothing (e.g., U UR R -> U R).
- Added project README with setup, usage, and debug notes.
- Renamed generated extension folder to `GestHero` and updated README install steps.
- Changed repository visibility to public.
- Renamed the journal file to `technical_journey.md`.
- Added `.gitignore` for generated/build folders and editor artifacts.
- Updated README with public repository link.
- Added MIT LICENSE and README badges/security notes.
- Updated README tone and added direct import instructions for `gestHero/`.
- Allowed default right-click context menu when no gesture is performed.
- Added hold-delay activation for right-click gestures to allow short-click context menu.
- Exposed hold delay (ms) control in options and wired it to gesture activation.
- Refined right-click gating to allow context menu only on quick release and suppress it during holds.
- Allowed context menu during pending right-click when elapsed is below hold delay and no movement detected.
- Cleared pending gesture state when allowing the context menu to prevent stuck drawing overlays.
- Switched right-click decision to time-based gating: wait hold delay before activating gestures, short release always opens menu.
- Added defensive release handling: finalize/cancel gestures when button state drops or mouseup is missing; added pending release logs.
- Buffered right-click movements during the hold delay and replayed them on activation so gestures drawn immediately after delay.
- Limited button-state release checks to non-right mouse buttons to avoid premature gesture finalization on macOS.
- On blur/visibility, right-click gestures now finalize or release instead of hard canceling to avoid losing gestures.
- Deferred early contextmenu events during right-click hold and attempted to re-trigger the menu on short release.
- Switched macOS to double right-click for native context menu; single right-click reserved for gestures.
- Documented macOS double right-click behavior and Windows/Linux short-click menu note in README.
- Refreshed options UI styling with a cleaner layout, typography, and button hierarchy.

## 2025-12-30

- Fixed right-click menu vs gesture drawing stability issues.
- Added return value to `activateGesture()` to prevent double activation from both timer and mousemove.
- Improved pending state cleanup: added `destroyCanvas()` and `hideLabel(0)` calls in `handlePendingRelease()`.
- Enhanced context menu handler cleanup: added canvas/label cleanup when allowing context menu.
- Added debug logging to context menu handler for better troubleshooting (context_menu_allowed, context_menu_during_pending, context_menu_blocked_pending, context_menu_blocked_active).
- Removed redundant `gestureActive` check after activation in `onMouseMove()` to prevent gesture move processing issues.
- **Critical fix**: Added full state cleanup in `onContextMenu()` when context menu opens during pending state (elapsed < delay). This prevents canvas/label staying visible and gesture continuing to draw after short right-click.
- **Major fix**: Removed conditional `preventDefault()` in `onMouseDown()` for right-click. Now all gesture button presses are prevented immediately, allowing proper hold-delay timing before context menu can appear on short release.
- **Critical fix**: Moved `preventDefault()` and `stopPropagation()` to top of `onContextMenu()` handler (after allowContextMenuUntil check). This ensures context menu is ALWAYS blocked unless explicitly allowed via allowContextMenuUntil flag.
- **Fix**: Reverted `onMouseDown()` preventDefault for right-click - only prevent for non-right buttons. Right-click needs default behavior to allow contextmenu event to fire, which is then controlled by `onContextMenu()` handler based on timing and state.
- **Research-based fix**: After researching mouse gesture extensions (Simple Mouse Gestures, FoxyGestures), discovered that contextmenu event timing differs by OS (macOS: mousedown, Windows: mouseup) and preventDefault() cannot be undone. Solution: Only call preventDefault() in onContextMenu when gesture is actually active/used, not during pending state. This allows short clicks to open menu naturally.
- **Final fix**: Added `pendingGesture` to the preventDefault condition in onContextMenu. This ensures that when contextmenu fires immediately on mousedown (macOS), it's blocked during the pending delay period. Menu only opens when allowContextMenuUntil is explicitly set after short release.
- **Latest fix**: Gestures worked but menu didn't open. Added special handling in onContextMenu during pendingGesture state: if elapsed time < hold delay AND no movement detected (pendingPoints.length === 0), allow the context menu to open naturally by cleaning up state and returning early. This allows short clicks to open the menu while still blocking it for gesture drawing.
- **Critical realization**: The previous fix didn't work because contextmenu event fires on mousedown (macOS) before mouseup can set allowContextMenuUntil flag. The fix was checking elapsed time in onContextMenu, but this still blocked short clicks.
- **Final working fix**: Simplified onContextMenu logic - if in pendingGesture state and NO movement detected (pendingPoints.length === 0), immediately allow context menu regardless of elapsed time. This works because: (1) if user moves mouse, hasMoved becomes true and menu is blocked, (2) if no movement, menu opens naturally on short click, (3) if hold delay passes without movement, gesture activation happens from timer and menu is blocked by gestureActive flag.
- **Root cause identified via research**: The check `pendingPoints.length > 0` was always true because pendingPoints is initialized with the mousedown point on line 744: `pendingPoints = [{ x: startX, y: startY, t: downTime }]`. This meant hasMoved was ALWAYS true, preventing menu from ever opening.
- **Correct fix**: Calculate actual movement distance by iterating through pendingPoints and summing the distance between consecutive points. Use a 5-pixel threshold to allow menu if total movement < 5px (accounting for accidental micro-movements). This properly detects intentional gesture movement vs static clicks.
- **Research breakthrough**: Studied real production code from Gesturefy, FoxyGestures, and Chrome-Mouse-Gestures. Discovered the CORRECT solution used by all major gesture extensions: **Dynamic event listener registration**. When gesture becomes active, add contextmenu/click/auxclick preventDefault listeners. When gesture ends, remove them after 200ms delay.
- **Final implementation**: Added `enableContextMenuPrevention()` and `disableContextMenuPrevention()` functions that dynamically add/remove `blockEvent` listeners. Called `enableContextMenuPrevention()` in `activateGesture()`, and `disableContextMenuPrevention()` in `cancelGesture()` and `finalizeGesture()` (with 200ms delay). Simplified `onContextMenu()` to only handle `allowContextMenuUntil` and `suppressClickUntil` checks - all gesture-active prevention now handled by dynamic listeners.
- This is the production-proven pattern used by all major gesture extensions. It works because: (1) short right-click has no gesture activation, no dynamic listeners added, menu opens naturally, (2) long hold + movement activates gesture, adds dynamic listeners that block all subsequent contextmenu events.
- **Critical bug fix**: On macOS, contextmenu event fires during mousedown while still in `pendingGesture` state (before gesture activates). This opened the menu BUT left pending state active, so mouseup or timer would still trigger gesture. Fixed by adding `pendingGesture` check in `onContextMenu()` - if pending, cancel the entire gesture state (clear timer, reset flags) and allow menu to open. This prevents gesture from activating after menu is already shown.
- Updated both `gestHero/content.js` and `build_extension.py` with complete dynamic listener implementation and pending state cancellation fix.

## 2026-05-29

- Added a project analysis report (`PROJE_ANALIZ_RAPORU.md`) covering issues, fixes, and improvement suggestions.
- **Phase 1 (technical debt, no behaviour change):**
  - S2 — Branding aligned to "GestHero" across `manifest.json` (name + default_title) and the settings export filename (`gesthero_settings.json`).
  - S1 — Removed the ~2000 lines of source embedded as Python strings in `build_extension.py`. `gestHero/` is now the single source of truth; the build script only refreshes SVG→PNG icons and produces a distributable `gestHero.zip`.
  - S3 — Extracted the pure gesture helpers into `gestHero/gestures-core.js` (shared by content script, options page, and tests; exposed as both a global and a CommonJS module). Added `node:test` unit tests under `tests/`, ESLint + Prettier configs, `package.json` scripts, and a GitHub Actions CI workflow (lint + format + test + build).
  - Tooling artefacts (`node_modules/`, `gestHero.zip`) added to `.gitignore`.
- **Phase 2 (hardening):**
  - S4 — Debug log now persists to `chrome.storage.local` (hydrate on startup, debounced flush, capped at 500) so it survives MV3 service-worker suspension/restart. `getDebugLog`/`clearDebugLog` respond asynchronously.
  - S5 — Added `chrome.runtime.lastError` guards to fire-and-forget `sendMessage` calls in `content.js` and `tabs.sendMessage` in `background.js` to silence "Unchecked runtime.lastError" noise.
  - S7 — `IS_MAC` now prefers `navigator.userAgentData.platform`, falling back to the deprecated `navigator.platform` and then the user-agent string.
  - S6 — Documented permission rationale, top-frame-only injection (no `all_frames`), pointer-input limitation, and debug-log persistence in the README.
