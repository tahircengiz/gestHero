# Technical Journal

## 2025-12-29
- Created this journal to track all work.
- GitHub private repo setup requested; using default repo name `prj_GestureHero` unless changed.
- Initialized local git repository and renamed default branch to `main`.
- Started `gh auth login` flow; device code issued and awaiting user completion.
- Verified SSH authentication to GitHub works for user `tahircengiz`.
- PAT-based `gh auth login` failed due to missing `read:org` scope; need token with that scope or use API workaround.
- Created private GitHub repo `tahircengiz/prj_GestureHero` via API and added `origin` SSH remote.
- Committed `technical_journay.md` and pushed initial commit to `main`.
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
1- Added corner smoothing settings for rounded gesture turns (tolerance and min length).
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
