# Operator Console Model

## Purpose

The console should make AutoClaw understandable and operable without forcing the user to read raw DB rows, logs, or transcripts.

Default truth first.
Inspect depth only when needed.

## Core object hierarchy

Show the runtime through this hierarchy:

- task
- run
- attempt
- flow
- node

## Default views

Start with simple views:

- task inbox / summary view
- run detail view
- attempt + current flow view
- node detail / checkpoint history view

## What to show first

Surface these by default:

- current phase / mode
- overall status (`healthy`, `blocked`, `stalled`, `waiting_approval`, `failed`, `done`)
- latest meaningful progress time
- current active child or subtree
- latest checkpoint summary
- blocker / approval reason if one exists

## What to collapse by default

Keep these out of the top-level view unless explicitly expanded:

- deep descendant graph detail
- full prompt overlays
- low-level skill/tool chatter
- old superseded plan revisions

## Operator actions

Operators should be able to:

- pause / resume
- approve / reject
- request replan
- force retry
- cancel run
- inspect subtree / node history

## UI rule

The full graph is an inspect view.
It is not the default homepage.
