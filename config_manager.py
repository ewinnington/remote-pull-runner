#!/usr/bin/env python3
"""
Manage configuration for remote-pull-runner.
"""
import argparse
import json
import os
import uuid
import re


def normalize_repo_url(repo):
    m = re.match(r'https?://github\.com/([^/]+/[^/]+)(?:\.git)?', repo)
    return m.group(1) if m else repo


CONFIG_FILE = 'config.json'


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'repos': [], 'servers': [], 'commands': []}


def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


def add_repo(args):
    cfg = load_config()
    repo_name = normalize_repo_url(args.repo)
    for r in cfg['repos']:
        if r['name'] == repo_name:
            print(f"Repository {repo_name} already enrolled.")
            return
    entry = {
        'name': repo_name,
        'token': args.token or '',
        'branch': args.branch or 'main',
        'active': True,
        'last_check': '1970-01-01T00:00:00'
    }
    cfg['repos'].append(entry)
    save_config(cfg)
    print(f"Enrolled repository {repo_name}")


def list_repos(args):
    cfg = load_config()
    if not cfg['repos']:
        print("No repositories enrolled.")
        return
    for r in cfg['repos']:
        status = 'active' if r.get('active') else 'inactive'
        print(f"{r['name']} (branch={r.get('branch')}, status={status}, last_check={r.get('last_check')})")


def remove_repo(args):
    cfg = load_config()
    original = len(cfg['repos'])
    cfg['repos'] = [r for r in cfg['repos'] if r['name'] != args.repo]
    if len(cfg['repos']) < original:
        save_config(cfg)
        print(f"Removed repository {args.repo}")
    else:
        print(f"No repository named {args.repo} found.")


def add_server(args):
    cfg = load_config()
    for s in cfg['servers']:
        if s['host'] == args.host:
            print(f"Server {args.host} already enrolled.")
            return
    entry = {
        'host': args.host,
        'user': args.user,
        'key': args.key,
        'active': True,
        'last_check': '1970-01-01T00:00:00'
    }
    cfg['servers'].append(entry)
    save_config(cfg)
    print(f"Enrolled server {args.host}")


def list_servers(args):
    cfg = load_config()
    if not cfg['servers']:
        print("No servers enrolled.")
        return
    for s in cfg['servers']:
        status = 'active' if s.get('active') else 'inactive'
        print(f"{s['host']} (user={s.get('user')}, status={status}, last_check={s.get('last_check')})")


def remove_server(args):
    cfg = load_config()
    original = len(cfg['servers'])
    cfg['servers'] = [s for s in cfg['servers'] if s['host'] != args.host]
    if len(cfg['servers']) < original:
        save_config(cfg)
        print(f"Removed server {args.host}")
    else:
        print(f"No server with host {args.host} found.")


def add_command(args):
    cfg = load_config()
    cmd_id = uuid.uuid4().hex
    entry = {
        'id': cmd_id,
        'repo': args.repo,
        'server': args.server,
        'command': args.command,
        'active': True,
        'last_run': '1970-01-01T00:00:00'
    }
    cfg.setdefault('commands', [])
    cfg['commands'] = [c for c in cfg['commands'] if c['id'] != cmd_id]
    cfg['commands'].append(entry)
    save_config(cfg)
    print(f"Enrolled command {cmd_id}")


def list_commands(args):
    cfg = load_config()
    cmds = cfg.get('commands', [])
    if not cmds:
        print("No commands enrolled.")
        return
    for c in cmds:
        status = 'active' if c.get('active') else 'inactive'
        print(f"{c['id']} - repo:{c['repo']} server:{c['server']} cmd:'{c['command']}' status:{status} last_run:{c['last_run']}")


def remove_command(args):
    cfg = load_config()
    original = len(cfg.get('commands', []))
    cfg['commands'] = [c for c in cfg.get('commands', []) if c['id'] != args.id]
    if len(cfg['commands']) < original:
        save_config(cfg)
        print(f"Removed command {args.id}")
    else:
        print(f"No command with id {args.id} found.")


def main():
    parser = argparse.ArgumentParser(description='Manage remote-pull-runner config')
    subs = parser.add_subparsers(dest='command')

    parser_add = subs.add_parser('add-repo', help='Enroll a GitHub repository')
    parser_add.add_argument('--repo', required=True, help='GitHub repo full name (user/repo)')
    parser_add.add_argument('--token', help='GitHub personal access token')
    parser_add.add_argument('--branch', default='main', help='Branch to monitor')
    parser_add.set_defaults(func=add_repo)

    parser_list = subs.add_parser('list-repos', help='List enrolled repositories')
    parser_list.set_defaults(func=list_repos)

    parser_remove = subs.add_parser('remove-repo', help='Remove enrolled repository')
    parser_remove.add_argument('--repo', required=True, help='GitHub repo full name to remove')
    parser_remove.set_defaults(func=remove_repo)

    parser_add = subs.add_parser('add-server', help='Enroll a remote server')
    parser_add.add_argument('--host', required=True, help='Server host or IP')
    parser_add.add_argument('--user', default=os.getlogin(), help='SSH username')
    parser_add.add_argument('--key', default=os.path.expanduser('~/.ssh/id_rsa'), help='Path to SSH private key')
    parser_add.set_defaults(func=add_server)

    parser_list = subs.add_parser('list-servers', help='List enrolled servers')
    parser_list.set_defaults(func=list_servers)

    parser_remove = subs.add_parser('remove-server', help='Remove enrolled server')
    parser_remove.add_argument('--host', required=True, help='Server host or IP to remove')
    parser_remove.set_defaults(func=remove_server)

    parser_cmd_add = subs.add_parser('add-command', help='Enroll a command mapping')
    parser_cmd_add.add_argument('--repo', required=True, help='Repository name (user/repo)')
    parser_cmd_add.add_argument('--server', required=True, help='Server host')
    parser_cmd_add.add_argument('--command', required=True, help='Command to run on server')
    parser_cmd_add.set_defaults(func=add_command)

    parser_cmd_list = subs.add_parser('list-commands', help='List enrolled commands')
    parser_cmd_list.set_defaults(func=list_commands)

    parser_cmd_remove = subs.add_parser('remove-command', help='Remove enrolled command')
    parser_cmd_remove.add_argument('--id', required=True, help='Command ID to remove')
    parser_cmd_remove.set_defaults(func=remove_command)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
    else:
        args.func(args)


if __name__ == '__main__':
    main()