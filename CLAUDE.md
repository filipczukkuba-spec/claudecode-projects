# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session startup

Read `_claude/index.md` first, then the relevant project file from `_claude/`. This gives full project context in ~50 lines instead of exploring the codebase from scratch. Update the relevant `_claude/*.md` note whenever significant changes are made.

## Projects

This repo is a monorepo containing multiple projects:

- **`jarvis.py`** — Voice-controlled AI assistant (JARVIS). See `_claude/jarvis.md`.
- **`agent.py`** — Multi-agent workflow foundation. See `_claude/agent_workflow.md`.
- **`geometrydash.html`** — Side-scrolling platformer browser game. See `_claude/games.md`.
- **`tictactoe.html`** — Two-player Tic Tac Toe browser game. See `_claude/games.md`.
- **`*.mq4`** — MetaTrader 4 Expert Advisors (APEX SMC, TrendMomentum). See `_claude/trading.md`.
- **`onedesign.html`** — Standalone marketing/design page. See `_claude/onedesign.md`.

## Games — architecture pattern

All games: single `.html` file, inline CSS + JS, no build system, open directly in browser. State as module-level `let` vars → `update(dt)` → `render()` each frame.

## Adding a new level or obstacle (Geometry Dash)

Edit the data arrays near the top of the script. Tile coordinates use a 48px grid (`TILE = 48`). The HUD occupies the top 60px, so world Y = `tileRow * 48 + 60`. The level ends at tile X = `LEVEL_LENGTH - 1` (currently 200).
