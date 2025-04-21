# Micro CI/CD Plan

**Date:** 2025-04-21

## Initial Plan

1. Set up project structure
2. Create requirements.txt for package dependencies
3. Configure virtual environment instructions
4. Add basic CI/CD skeleton scripts

---

## Virtual Environment Setup (Completed)

**Date:** 2025-04-21

- Created Python virtual environment `.venv`
- Windows activation: `.venv\Scripts\activate`
- Linux activation: `source .venv/bin/activate`

---

## Basic CI Check Script (Completed)

**Date:** 2025-04-21

- Added `ci_check.py` to detect new commits via GitHub API
- Supports arguments: `--repo`, `--token`, `--last-check` (ISO timestamp)

---

## Configuration CLI (Completed)

**Date:** 2025-04-21

- Added `config_manager.py` with commands:
  - `add-repo`, `list-repos`, `remove-repo`
  - `add-server`, `list-servers`, `remove-server`
- Configuration stored in `config.json`

---

## Runner Script (Completed)

**Date:** 2025-04-21

- Added `runner.py` to:
  - Iterate enrolled repositories and detect new commits
  - Iterate enrolled servers and check connectivity via SSH
  - Log activity to `logs/activity.log` and connectivity to `logs/connectivity.log`
  - Update `last_check` timestamps in `config.json`

---

## Flask API/UI (Skeleton Completed)

**Date:** 2025-04-21

- Added `app.py` with endpoints for:
  - CRUD repos and servers
  - Manual triggers
  - Log viewing
  - Token authentication
  - Background scheduler

---

## Web UI Templates & Static Assets (Completed)

**Date:** 2025-04-21

- Added HTML templates: `layout.html`, `login.html`, `repos.html`, `servers.html`, `logs.html`
- Implemented `static/main.js` for UI interactions
- Integrated UI routes and login/logout in `app.py`

---

## Commands Feature (Completed)

**Date:** 2025-04-21

- Added command management in `config_manager.py`, API endpoints in `app.py`, UI template and JS support

---

## User Testing Results (2025-04-21)

- Login, repos and servers CRUD and views working
- Logs and health endpoint working
- Issues found:
  - Trigger Check button does not refresh UI; Last Check not updating immediately
  - No display of "Next check" time in UI
  - `/commands/view` route missing (commands page inaccessible)
  - Error when enrolling a repo URL (404 if full URL used instead of owner/repo)

---

*Next:*
- Add auto-refresh after triggering checks on repos and servers pages
- Display next scheduled check times in UI
- Implement `/commands/view` route in `app.py`
- Support full GitHub repo URLs by parsing input to owner/repo
- Adjust documentation if needed
