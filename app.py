#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template, send_file, make_response, redirect, flash
from flask_wtf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
import os, json, uuid
import runner
import secrets_manager
from datetime import datetime
import config_manager
import netifaces  # type: ignore
import socket

CONFIG_FILE = 'config.json'
LOG_DIR = 'logs'
ACTIVITY_LOG = os.path.join(LOG_DIR, 'activity.log')
CONN_LOG = os.path.join(LOG_DIR, 'connectivity.log')

app = Flask(__name__)
app.secret_key = uuid.uuid4().hex
csrf = CSRFProtect(app)

# Load or initialize config and token
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

# Load or generate API token and encryption key
keys = secrets_manager.load_keys()
TOKEN = keys['api_key']

# Auth decorator
def require_token(fn):
    def wrapper(*args, **kwargs):
        auth = request.headers.get('X-Auth-Token') or request.cookies.get('auth_token')
        if auth != TOKEN:
            return jsonify({'error':'Unauthorized'}), 401
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@app.context_processor
def inject_auth():
    auth = request.cookies.get('auth_token')
    return {'is_auth': auth == TOKEN}

def normalize_repo(name):
    return config_manager.normalize_repo_url(name)

# Serve index page
@app.route('/')
def index():
    return '<h1>Remote Pull Runner</h1><p>Use the API endpoints to manage repos and servers.</p>'

# UI routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        token_in = request.form.get('token')
        if token_in == TOKEN:
            resp = make_response(redirect('/repos/view'))
            resp.set_cookie('auth_token', token_in, httponly=True, secure=True, samesite='Lax')
            return resp
        else:
            flash('Invalid token', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    resp = make_response(redirect('/login'))
    resp.set_cookie('auth_token', '', expires=0, httponly=True, secure=True, samesite='Lax')
    return resp

@app.route('/repos/view')
def view_repos():
    return render_template('repos.html')

@app.route('/servers/view')
def view_servers():
    return render_template('servers.html')

@app.route('/logs/view')
def view_logs():
    return render_template('logs.html')

@app.route('/commands/view')
def view_commands():
    return render_template('commands.html')

@app.route('/settings/view')
@require_token
def view_settings():
    return render_template('settings.html')

# Repositories CRUD
@app.route('/api/repos', methods=['GET'])
def get_repos():
    cfg = load_config()
    return jsonify(cfg.get('repos', []))

@app.route('/api/repos', methods=['POST'])
@require_token
def add_repo():
    data = request.json or {}
    name = normalize_repo(data.get('name',''))
    # Move token to secrets storage
    secrets_list = []
    token_val = data.get('token')
    if token_val:
        secret_id = secrets_manager.store_secret(f"{name}_token", token_val)
        secrets_list.append({'key': 'token', 'id': secret_id})
    repo = {'name': name,
            'branch': data.get('branch','main'), 'active': True,
            'last_check': '1970-01-01T00:00:00', 'last_commit': ''}
    if secrets_list:
        repo['secrets'] = secrets_list
    cfg = load_config()
    cfg.setdefault('repos', [])
    cfg['repos'] = [r for r in cfg['repos'] if r['name']!=name]
    cfg['repos'].append(repo)
    save_config(cfg)
    return jsonify({'status':'ok'}),201

@app.route('/api/repos/<path:name>', methods=['DELETE'])
@require_token
def delete_repo(name):
    cfg = load_config()
    cfg['repos'] = [r for r in cfg.get('repos',[]) if r['name']!=name]
    save_config(cfg)
    return jsonify({'status':'ok'})

# Servers CRUD
@app.route('/api/servers', methods=['GET'])
def get_servers():
    cfg = load_config()
    return jsonify(cfg.get('servers', []))

@app.route('/api/servers', methods=['POST'])
@require_token
def add_server():
    data = request.json or {}
    srv = {'host':data.get('host'), 'user':data.get('user'),
           'key':data.get('key'), 'active':True, 'last_check':'1970-01-01T00:00:00'}
    cfg = load_config()
    cfg.setdefault('servers', [])
    cfg['servers'] = [s for s in cfg['servers'] if s['host']!=srv['host']]
    cfg['servers'].append(srv)
    save_config(cfg)
    return jsonify({'status':'ok'}),201

@app.route('/api/servers/<host>', methods=['DELETE'])
@require_token
def delete_server(host):
    cfg = load_config()
    cfg['servers'] = [s for s in cfg.get('servers',[]) if s['host']!=host]
    save_config(cfg)
    return jsonify({'status':'ok'})

# Commands CRUD
@app.route('/api/commands', methods=['GET'])
def get_commands():
    cfg = load_config()
    return jsonify(cfg.get('commands', []))

@app.route('/api/commands', methods=['POST'])
@require_token
def add_command_api():
    data = request.json or {}
    cmd = {
        'id': uuid.uuid4().hex,
        'repo': data.get('repo'),
        'server': data.get('server'),
        'command': data.get('command'),
        'active': True,
        'last_run': '1970-01-01T00:00:00'
    }
    cfg = load_config()
    cfg.setdefault('commands', [])
    cfg['commands'] = [c for c in cfg['commands'] if c['id'] != cmd['id']]
    cfg['commands'].append(cmd)
    save_config(cfg)
    return jsonify(cmd), 201

@app.route('/api/commands/<cmd_id>', methods=['DELETE'])
@require_token
def delete_command_api(cmd_id):
    cfg = load_config()
    cfg['commands'] = [c for c in cfg.get('commands', []) if c['id'] != cmd_id]
    save_config(cfg)
    return jsonify({'status':'ok'})

@app.route('/api/commands/<cmd_id>/run', methods=['POST'])
@require_token
def run_command_api(cmd_id):
    result = runner.run_command(cmd_id)
    return jsonify(result)

@app.route('/api/commands/<cmd_id>/secrets', methods=['GET'])
@require_token
def get_command_secrets(cmd_id):
    cfg = load_config()
    cmd = next((c for c in cfg.get('commands', []) if c['id'] == cmd_id), None)
    if not cmd:
        return jsonify({'error':'Command not found'}), 404
    masked_list = []
    for s in cmd.get('secrets', []):
        try:
            full = secrets_manager.get_secret(s['id'])
            masked = secrets_manager.mask_secret(full)
        except Exception:
            masked = None
        masked_list.append({'key': s['key'], 'id': s['id'], 'value': masked})
    return jsonify(masked_list)

@app.route('/api/commands/<cmd_id>/secrets', methods=['POST'])
@require_token
def add_command_secret(cmd_id):
    data = request.json or {}
    key = data.get('key')
    value = data.get('value')
    if not key or value is None:
        return jsonify({'error':'Missing key or value'}), 400
    cfg = load_config()
    for c in cfg.get('commands', []):
        if c['id'] == cmd_id:
            secret_id = secrets_manager.store_secret(key, value)
            sec = c.setdefault('secrets', [])
            sec.append({'key': key, 'id': secret_id})
            save_config(cfg)
            masked = secrets_manager.mask_secret(value)
            return jsonify({'key': key, 'id': secret_id, 'value': masked}), 201
    return jsonify({'error':'Command not found'}), 404

@app.route('/api/commands/<cmd_id>/secrets/<secret_id>', methods=['DELETE'])
@require_token
def delete_command_secret(cmd_id, secret_id):
    cfg = load_config()
    for c in cfg.get('commands', []):
        if c['id'] == cmd_id:
            new_list = []
            removed = False
            for s in c.get('secrets', []):
                if s['id'] == secret_id:
                    secrets_manager.delete_secret(secret_id)
                    removed = True
                else:
                    new_list.append(s)
            if removed:
                c['secrets'] = new_list
                save_config(cfg)
                return jsonify({'status':'ok'})
            return jsonify({'error':'Secret not found'}), 404
    return jsonify({'error':'Command not found'}), 404

# Manual triggers
@app.route('/api/check/repos', methods=['POST'])
@require_token
def trigger_repos():
    runner.check_repos()
    return jsonify({'status':'ok','checked_at':datetime.utcnow().isoformat()})

@app.route('/api/check/servers', methods=['POST'])
@require_token
def trigger_servers():
    runner.check_servers()
    return jsonify({'status':'ok','checked_at':datetime.utcnow().isoformat()})

# Log viewing
def tail_lines(filepath, lines=10):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r') as f: data=f.readlines()
    return data[-lines:]

@app.route('/logs/activity', methods=['GET'])
def view_activity():
    return '<br>'.join(tail_lines(ACTIVITY_LOG)) or 'No activity logs'

@app.route('/logs/connectivity', methods=['GET'])
def view_connectivity():
    return '<br>'.join(tail_lines(CONN_LOG)) or 'No connectivity logs'

# Health endpoint
@app.route('/health')
def health():
    return jsonify({'status':'ok', 'time': datetime.utcnow().isoformat()})

# Schedule API
@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    jr = sched.get_job('repo_check')
    js = sched.get_job('server_check')
    return jsonify({
        'next_repo': jr.next_run_time.isoformat() if jr and jr.next_run_time else None,
        'next_server': js.next_run_time.isoformat() if js and js.next_run_time else None
    })

# Settings API
@app.route('/api/settings', methods=['GET'])
@require_token
def get_settings():
    cfg = load_config()
    return jsonify({
        'repo_interval': cfg.get('repo_interval', 24),
        'server_interval': cfg.get('server_interval', 12)
    })

@app.route('/api/settings', methods=['POST'])
@require_token
def update_settings():
    data = request.json or {}
    cfg = load_config()
    cfg['repo_interval'] = data.get('repo_interval', cfg.get('repo_interval', 24))
    cfg['server_interval'] = data.get('server_interval', cfg.get('server_interval', 12))
    save_config(cfg)
    # Reschedule jobs
    sched.reschedule_job('repo_check', trigger='interval', hours=cfg['repo_interval'])
    sched.reschedule_job('server_check', trigger='interval', hours=cfg['server_interval'])
    return jsonify({'status':'ok'})


def get_names_4_ips(ips):
    names = []
    for ip in ips:
        try:
            name = socket.gethostbyaddr(ip)[0]
            names.append(name)
        except Exception:
            names.append(None)
    return names

def get_all_ip():
    all_addrs = []
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
        for addr in addrs:
            all_addrs.append(addr['addr'])
    if not all_addrs:
        raise RuntimeError("No IP addresses found")
    return all_addrs

# find the ip that is on the ts.net domain
def get_ip_on_ts_net_domain():
    all_addrs = get_all_ip()
    for addr in all_addrs:
        try:
            name = socket.gethostbyaddr(addr)[0]
            if name.endswith('.ts.net.'):
                return addr
        except Exception:
            continue
    raise RuntimeError("No IP address found on ts.net domain")




# Scheduler setup with configurable intervals
cfg = load_config()
repo_interval = cfg.get('repo_interval', 24)
server_interval = cfg.get('server_interval', 12)
sched = BackgroundScheduler()
sched.add_job(runner.check_repos, 'interval', hours=repo_interval, id='repo_check')
sched.add_job(runner.check_servers, 'interval', hours=server_interval, id='server_check')
sched.start()

if __name__ == '__main__':
    #ts_ip = get_tailscale_ip('Unknown adapter Tailscale')  # or the exact adapter name from ipconfig
    #app.run(host=ts_ip, port=5000)
    app.run(host=get_ip_on_ts_net_domain(), port=5000)
    #app.run(host='0.0.0.0', port=5000)