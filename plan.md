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

---

## User Testing Results (2nd Round, 2025-04-21)

- On Repos view, Delete button sends DELETE for full URL path (`https://github.com/...`), causing 404
- "Next Repo Check" remains "Loading..." (schedule not fetched/populated)
- "Next Server Check" remains "Loading..." (schedule not fetched/populated)
- Trigger Check button remains active immediately; would be better to disable/animate until refresh
- Commands view:
  - Repo and Server inputs are free-text; should use dropdowns of enrolled entries
  - RUN command action uses default SSH key (`~/.ssh/id_rsa`) instead of the server's configured key, causing file not found error

---

*Next:*
1. Fix DELETE endpoint routing/UI for repos with normalized names (encode slashes or strip URL schemes)
2. Fetch `/api/schedule` in JS and populate "Next Repo Check" and "Next Server Check" spans
3. Disable/animate Trigger buttons on click until checks complete or timeout
4. In Commands UI, load enrolled repos and servers for dropdown select inputs instead of text
5. Update `runner.run_command` to look up server config for key and user instead of defaults
6. Write unit tests for critical API endpoints and runner functions
7. Update documentation to reflect input normalization and UI improvements

---

## User Testing Results (3rd Round, 2025-04-21)

- When a server check fails and retries are in progress, the `active` flag remains `true`; should reflect a `retry` state until final status is determined
- Commands view dropdowns present but need verification that only valid enrolled repos and servers appear

---

*Next:*
1. Introduce a `retry` status in server entries during retry attempts; update UI to reflect this state
2. Ensure Commands page dropdowns dynamically list only active repos and servers
3. Update server check logic to transition `active` between `true`, `retry`, and `false` based on connectivity
4. Add visual indicator in UI for servers in `retry` status

---

## New Feature: Store Last Commit Hash

**Date:** 2025-04-21

- Extend repo configuration to include `last_commit` field
- Update `config_manager.py` to initialize `last_commit` when enrolling repos
- Modify `runner.check_repos` to compare commit SHA instead of only timestamps
- Update API `add-repo` endpoint to set `last_commit` initially
- Update README to document new behavior

---

## Last Commit Feature (Completed)

**Date:** 2025-04-21

- `config_manager.py` now initializes `last_commit` on enrollment
- `runner.check_repos` compares and updates `last_commit` based on commit SHA
- `runner.run_command` clones or updates the repository on the remote server before command execution and updates `last_commit`

*Next:*
- Expose `last_commit` in the API `/api/repos` response
- Update the Repos UI to display `last_commit` in the table
- Update README with `last_commit` behavior
- Verify remote command execution clones with correct checkouts

---

## Feature Check: Auto-Deploy Commands on New Commits

**Date:** 2025-04-21

- Expected: When a new commit is detected in a monitored repo (via scheduled or manual check), all enrolled commands for that repo should automatically run on their target servers.
- Current: `runner.check_repos` logs new commits but does not trigger `runner.run_command` for enrolled commands.

---

## New Feature: Configurable Check Intervals

**Date:** 2025-04-21

- Requirement: Allow users to configure the interval for repo checks (default 24h) and server connectivity checks (default 12h) via the web UI.
- Store these interval settings in `config.json` and apply them to the APScheduler jobs.

---

## Auto-Deploy & Settings API (Completed)

**Date:** 2025-04-21

- `runner.check_repos` automatically triggers `run_command` for all active commands on new commits
- Settings API endpoints (`GET/POST /api/settings`) added to `app.py`
- Scheduler job intervals now configurable via `repo_interval` and `server_interval` fields in `config.json`

*Next:*
- Create Settings UI (`settings.html`) and add navigation link
- Implement JavaScript in `main.js` to load and update settings
- Test that interval changes reschedule background jobs
- Add UI indicator/logging for automatic deployments
