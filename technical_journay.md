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
- Added corner smoothing settings for rounded gesture turns (tolerance and min length).
