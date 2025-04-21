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
    gh = Github()  # For token support, extend to read per-repo token if needed

    for repo_entry in repos:
        if not repo_entry.get('active', False):
            continue
        repo_name = repo_entry['name']
        token = repo_entry.get('token') or None
        branch = repo_entry.get('branch', 'main')
        try:
            g = Github(token) if token else gh
            repo = g.get_repo(repo_name)
            commit = repo.get_commits(sha=branch)[0].commit.committer.date
            last_check = datetime.fromisoformat(repo_entry.get('last_check'))
            if commit > last_check:
                msg = f"New commit detected in {repo_name}@{branch}: {commit.isoformat()}"
                logger.info(msg)
            else:
                logger.info(f"No new commits for {repo_name}@{branch}")
        except Exception as e:
            logger.error(f"Error checking {repo_name}: {e}")
        finally:
            # Update last_check regardless of result
            repo_entry['last_check'] = now_iso

    cfg['repos'] = repos
    save_config(cfg)


def check_servers():
    cfg = load_config()
    servers = cfg.get('servers', [])
    now_iso = datetime.utcnow().isoformat()
    for srv in servers:
        if not srv.get('active', False):
            continue
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
        if not success:
            conn_logger.warning(f"[{host}] unreachable after {retries} attempts")
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

    # SSH into server
    host = cmd_entry['server']
    user = cmd_entry.get('user') or None
    key_path = os.path.expanduser(cmd_entry.get('key', '~/.ssh/id_rsa'))
    command = cmd_entry['command']
    now_iso = datetime.utcnow().isoformat()
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=user, key_filename=key_path, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        ssh.close()
        # Log output
        logger.info(f"[COMMAND {cmd_id}] {out}")
        if err:
            logger.error(f"[COMMAND {cmd_id}] ERR: {err}")
        # Update last_run
        cmd_entry['last_run'] = now_iso
        save_config(cfg)
        return {'status': 'ok', 'output': out, 'error': err, 'last_run': now_iso}
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