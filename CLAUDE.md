# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repo contains standalone browser games — each is a single self-contained `.html` file with inline CSS and JavaScript. No build system, no dependencies, no server required. Open any file directly in a browser.

## Projects

- **`geometrydash.html`** — Side-scrolling platformer. Fixed-screen-X player, tile-based world that scrolls left. Physics: gravity + jump velocity, coyote time, jump buffering. Level is defined entirely in data arrays at the top of the script (`gapRanges`, `spikeData`, `platformData`, `tallBlocks`, `orbData`, `checkpointTiles`). Audio is synthesized via Web Audio API (no external assets). Game loop uses `requestAnimationFrame` with capped delta time.

- **`tictactoe.html`** — Two-player Tic Tac Toe. Pure DOM manipulation, no canvas. Score persists across rounds within a session (resets on page reload).

## Architecture pattern

Both games follow the same pattern: all state as module-level `let` variables, a single `update(dt)` function advancing state, and a `render()` function drawing each frame. There is no framework or module system — everything is in one `<script>` block.

## Adding a new level or obstacle (Geometry Dash)

Edit the data arrays near the top of the script. Tile coordinates use a 48px grid (`TILE = 48`). The HUD occupies the top 60px, so world Y = `tileRow * 48 + 60`. The level ends at tile X = `LEVEL_LENGTH - 1` (currently 200).
