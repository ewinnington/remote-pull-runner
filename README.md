# Remote Pull Runner

Remote Pull Runner is a micro CI/CD tool built with Python and Flask. It monitors GitHub repositories and remote servers, and runs commands on servers upon new commits.

## Features

- Enroll GitHub repositories (public/private) for change detection
- Enroll remote servers via SSH for connectivity checks
- Configure commands to run on servers when changes are detected
- Web UI for management, manual triggers, and log viewing
- Background scheduler for periodic checks
- Token-based authentication

## Requirements

- Python 3.10+ on Windows or 3.12+ on Linux
- Git

## Setup

1. Clone the repository:
   ```bash
   git clone <repo-url> && cd remote-pull-runner
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### CLI Configuration

- Enroll a GitHub repository:
  ```bash
  python config_manager.py add-repo --repo user/repo [--token YOUR_GITHUB_TOKEN] [--branch main]
  ```
- List repositories:
  ```bash
  python config_manager.py list-repos
  ```
- Enroll a server:
  ```bash
  python config_manager.py add-server --host 10.0.0.1 --user ubuntu --key ~/.ssh/id_rsa
  ```
- List servers:
  ```bash
  python config_manager.py list-servers
  ```
- Enroll a command mapping:
  ```bash
  python config_manager.py add-command --repo user/repo --server 10.0.0.1 --command "./deploy.sh"
  ```

### Run Runner

- Manually run checks and commands:
  ```bash
  python runner.py
  ```

### Web UI

1. Start the Flask app:
   ```bash
   python app.py
   ```
2. Open browser at `http://localhost:5000/login`
3. Use the generated token from `config.json` to log in.
4. Manage repositories, servers, commands, view logs, and trigger checks.

## Testing

Use the REST API or UI to perform actions. For example, use the UI to add a repo and then trigger a check. Logs are in the `logs/` directory.

## Next Steps

- Customize check intervals via UI
- Add more detailed error pages

---
