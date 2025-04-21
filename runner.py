#!/usr/bin/env python3
import os, shlex, base64, logging
import json
import logging
import paramiko
import time
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from github import Github

CONFIG_FILE = 'config.json'
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'activity.log')
CONN_LOG_FILE = os.path.join(LOG_DIR, 'connectivity.log')

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logger
logger = logging.getLogger('runner')
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(LOG_FILE, when='midnight', backupCount=7)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configure connectivity logger
conn_logger = logging.getLogger('connectivity')
conn_logger.setLevel(logging.INFO)
conn_handler = TimedRotatingFileHandler(CONN_LOG_FILE, when='midnight', backupCount=7)
conn_handler.setFormatter(formatter)
conn_logger.addHandler(conn_handler)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


def check_repos():
    cfg = load_config()
    repos = cfg.get('repos', [])
    now_iso = datetime.utcnow().isoformat()
    for repo_entry in repos:
        if not repo_entry.get('active', False):
            continue
        repo_name = repo_entry['name']
        token = repo_entry.get('token') or None
        branch = repo_entry.get('branch', 'main')
        try:
            gh_instance = Github(token) if token else Github()
            api_repo = gh_instance.get_repo(repo_name)
            latest = api_repo.get_commits(sha=branch)[0]
            latest_sha = latest.sha
            last_stored = repo_entry.get('last_commit')
            if last_stored and latest_sha != last_stored:
                msg = f"New commit {latest_sha} detected in {repo_name}@{branch}"
                logger.info(msg)
                # Auto-deploy: run all active commands for this repo
                for cmd in cfg.get('commands', []):
                    if cmd.get('active') and cmd.get('repo') == repo_name:
                        logger.info(f"Triggering command {cmd['id']} for repo {repo_name}")
                        run_result = run_command(cmd['id'])
                        logger.info(f"Command {cmd['id']} result: {run_result}")
            # Update stored commit and last_check always
            repo_entry['last_commit'] = latest_sha
            repo_entry['last_check'] = now_iso
        except Exception as e:
            logger.error(f"Error checking {repo_name}: {e}")
    cfg['repos'] = repos
    save_config(cfg)


def check_servers():
    cfg = load_config()
    servers = cfg.get('servers', [])
    now_iso = datetime.utcnow().isoformat()
    for srv in servers:
        # Only check if active or in retry state
        status = srv.get('active')
        if status == False:
            continue
        # Mark as retry when starting attempts
        srv['active'] = 'retry'
        host = srv['host']
        user = srv.get('user')
        key_path = os.path.expanduser(srv.get('key', '~/.ssh/id_rsa'))
        retries = 3
        delay = 300  # 5 minutes
        success = False
        for attempt in range(1, retries+1):
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=host, username=user, key_filename=key_path, timeout=10)
                stdin, stdout, stderr = ssh.exec_command('uptime')
                output = stdout.read().decode().strip()
                conn_logger.info(f"[{host}] {output}")
                ssh.close()
                success = True
                break
            except Exception as e:
                conn_logger.error(f"[{host}] attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)
        # Finalize status after attempts
        if success:
            srv['active'] = True
        else:
            conn_logger.warning(f"[{host}] unreachable after {retries} attempts")
            srv['active'] = False
        # Update last_check timestamp
        srv['last_check'] = now_iso
    cfg['servers'] = servers
    save_config(cfg)


def _b64_basic(token: str) -> str:
    """
    GitHub accepts HTTP Basic where the *password* is the PAT
    and the user part can be empty (':<PAT>') or the literal
    string 'x-access-token'.  Either works; we use the empty
    user because it gives the shortest header.
    """
    raw = f":{token}".encode()              # -> b":ghp_xxx..."
    return base64.b64encode(raw).decode()   # -> "OmdocGhwdF8uLi4="


def run_command(cmd_id: str):
    # ---------- config lookup ----------
    cfg       = load_config()
    cmd_entry = next((c for c in cfg.get('commands', []) if c['id'] == cmd_id), None)
    if not cmd_entry:
        return {'error': f'Command {cmd_id} not found'}
    if not cmd_entry.get('active', False):
        return {'error': f'Command {cmd_id} is inactive'}

    repo_name  = cmd_entry['repo']
    repo_entry = next((r for r in cfg.get('repos', []) if r['name'] == repo_name), {})
    token      = repo_entry.get('token') or None
    branch     = repo_entry.get('branch', 'main')

    gh         = Github(token) if token else Github()
    commit_sha = gh.get_repo(repo_name).get_commits(sha=branch)[0].sha

    host       = cmd_entry['server']
    srv_entry  = next((s for s in cfg.get('servers', []) if s['host'] == host), {})
    user       = srv_entry.get('user')
    key_path   = os.path.expanduser(srv_entry.get('key', '~/.ssh/id_rsa'))

    # ---------- paths & commands ----------
    dir_name     = repo_name.replace('/', '_')
    remote_base  = '~/rpr'
    remote_path  = f"{remote_base}/{dir_name}"
    now_iso      = datetime.utcnow().isoformat()

    # Build the git commands
    if token:
        repo_user = repo_name.split('/')[0]

        auth_b64  = _b64_basic(token)
        #auth_flag = f'git -c http.extraheader="Authorization: Basic {auth_b64}"'
        #auth_flag = f'git -c http.extraheader="Authorization: Bearer {token}"'
        # prevent any interactive prompt if auth fails
        clone_cmd = (
            f'GIT_TERMINAL_PROMPT=0 ' # {auth_flag} '
            f'git clone https://{repo_user}:{token}@github.com/{repo_name}.git {shlex.quote(dir_name)}'
        )
        fetch_cmd = f'GIT_TERMINAL_PROMPT=0 git fetch --all'
    else:
        clone_cmd = f'git clone https://github.com/{repo_name}.git {shlex.quote(dir_name)}'
        fetch_cmd = 'git fetch --all'

    git_setup = ' && '.join([
        f"mkdir -p {remote_base}",
        f"cd {remote_base}",
        f'if [ ! -d {shlex.quote(dir_name)} ]; then {clone_cmd}; fi',
        f"cd {shlex.quote(dir_name)}",
        fetch_cmd,
        f"git checkout {commit_sha} --force"
    ])

    try:
        # ---------- SSH session ----------
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, key_filename=key_path, timeout=10)

        # ---------- clone / update ----------
        stdin, stdout, stderr = ssh.exec_command(git_setup)
        if stdout.channel.recv_exit_status() != 0:
            err = stderr.read().decode().strip()
            logger.error(f"[COMMAND {cmd_id}] setup failed: {err}")
            ssh.close()
            return {'error': 'setup_failed', 'details': err}

        # ---------- user command ----------
        user_cmd = f"cd {remote_path} && {cmd_entry['command']}"
        stdin, stdout, stderr = ssh.exec_command(user_cmd)
        status = stdout.channel.recv_exit_status()
        out    = stdout.read().decode().strip()
        err    = stderr.read().decode().strip()
        ssh.close()

        if status != 0:
            logger.error(f"[COMMAND {cmd_id}] command exited with {status}")

        logger.info(f"[COMMAND {cmd_id}] {out}")
        if err:
            logger.error(f"[COMMAND {cmd_id}] ERR: {err}")

        # ---------- bookkeeping ----------
        cmd_entry['last_run']     = now_iso
        repo_entry['last_commit'] = commit_sha
        save_config(cfg)

        return {
            'status': 'ok',
            'commit': commit_sha,
            'output': out,
            'error': err,
            'last_run': now_iso
        }

    except Exception as exc:
        logger.error(f"[COMMAND {cmd_id}] execution failed: {exc}")
        return {'error': str(exc)}


def main():
    logger.info("Runner started")
    check_repos()
    check_servers()
    logger.info("Runner finished")


if __name__ == '__main__':
    main()