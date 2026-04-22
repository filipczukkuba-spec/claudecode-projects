---
type: context
project: games
---

# Browser Games

All games: single `.html` file, inline CSS + JS, no build system, open directly in browser.

## Geometry Dash (`geometrydash.html`)
- Side-scroller, fixed-X player, world scrolls left
- Physics: gravity, jump velocity, coyote time, jump buffering
- Level data arrays at top of script: `gapRanges`, `spikeData`, `platformData`, `tallBlocks`, `orbData`, `checkpointTiles`
- Grid: 48px tiles, HUD = top 60px, world Y = `tileRow*48+60`
- Level ends at tile X = `LEVEL_LENGTH-1` (200)
- Audio: Web Audio API synthesis (no files)
- Loop: `requestAnimationFrame` + capped delta time

## Tic Tac Toe (`tictactoe.html`)
- Two-player, pure DOM (no canvas)
- Score persists within session, resets on reload

## Pattern (both)
All state as module-level `let` vars → `update(dt)` → `render()` each frame.
