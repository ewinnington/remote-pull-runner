#!/usr/bin/env python3
import os
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


def run_command(cmd_id):
    # Load configuration
    cfg = load_config()
    cmds = cfg.get('commands', [])
    cmd_entry = next((c for c in cmds if c['id'] == cmd_id), None)
    if not cmd_entry:
        return {'error': f'Command {cmd_id} not found'}
    if not cmd_entry.get('active', False):
        return {'error': f'Command {cmd_id} is inactive'}

    # Gather repo info
    repo_name = cmd_entry['repo']
    repo_entry = next((r for r in cfg.get('repos', []) if r['name'] == repo_name), {})
    token = repo_entry.get('token') or None
    branch = repo_entry.get('branch', 'main')
    # Retrieve latest commit SHA
    gh = Github(token) if token else Github()
    api_repo = gh.get_repo(repo_name)
    commit_sha = api_repo.get_commits(sha=branch)[0].sha

    # SSH into server
    host = cmd_entry['server']
    srv_entry = next((s for s in cfg.get('servers', []) if s['host'] == host), {})
    user = srv_entry.get('user')
    key_path = os.path.expanduser(srv_entry.get('key', '~/.ssh/id_rsa'))
    # Prepare remote repo directory
    dir_name = repo_name.replace('/', '_')
    remote_base = '~/rpr'
    remote_path = f"{remote_base}/{dir_name}"

    command = cmd_entry['command']
    now_iso = datetime.utcnow().isoformat()
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, key_filename=key_path, timeout=10)
        # Clone or update repo on remote
        git_cmds = [
            f"mkdir -p {remote_base}",
            f"cd {remote_base}",
            f"if [ ! -d \"{dir_name}\" ]; then git clone https://github.com/{repo_name}.git {dir_name}; fi",
            f"cd {dir_name}",
            "git fetch --all",
            f"git checkout {commit_sha} --force"
        ]
        full_setup = ' && '.join(git_cmds)
        stdin, stdout, stderr = ssh.exec_command(full_setup)
        # Wait for setup to finish
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            setup_err = stderr.read().decode().strip()
            logger.error(f"[COMMAND {cmd_id}] setup failed: {setup_err}")
            ssh.close()
            return {'error': 'setup_failed', 'details': setup_err}
        # Execute user command in repo directory
        full_cmd = f"cd {remote_path} && {command}"
        stdin, stdout, stderr = ssh.exec_command(full_cmd)
        # Wait for command to complete
        cmd_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        ssh.close()
        if cmd_status != 0:
            logger.error(f"[COMMAND {cmd_id}] command exited with {cmd_status}")
        # Log output
        logger.info(f"[COMMAND {cmd_id}] {out}")
        if err:
            logger.error(f"[COMMAND {cmd_id}] ERR: {err}")
        # Update last_run and last_commit
        cmd_entry['last_run'] = now_iso
        repo_entry['last_commit'] = commit_sha
        save_config(cfg)
        return {'status': 'ok', 'commit': commit_sha, 'output': out, 'error': err, 'last_run': now_iso}
    except Exception as e:
        logger.error(f"[COMMAND {cmd_id}] execution failed: {e}")
        return {'error': str(e)}


def main():
    logger.info("Runner started")
    check_repos()
    check_servers()
    logger.info("Runner finished")


if __name__ == '__main__':
    main()