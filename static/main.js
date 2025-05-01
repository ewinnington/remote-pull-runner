document.addEventListener('DOMContentLoaded', async () => {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  const token = getCookie('auth_token');
  const headers = token ? { 'X-Auth-Token': token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };

  // Error-handling fetch wrapper
  async function request(url, opts = {}) {
    // Attach CSRF token for state-changing requests
    const method = opts.method ? opts.method.toUpperCase() : 'GET';
    if (method !== 'GET' && method !== 'HEAD') {
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      opts.headers = {
        ...opts.headers,
        'X-CSRFToken': csrfToken
      };
    }
    try {
      const res = await fetch(url, opts);
      const data = res.headers.get('Content-Type')?.includes('application/json')
        ? await res.json()
        : await res.text();
      if (!res.ok) throw new Error(data.error || data);
      return data;
    } catch (e) {
      alert(e.message);
      throw e;
    }
  }

  // Load schedule for Next Check
  async function loadSchedule() {
    try {
      const sched = await request('/api/schedule', { method: 'GET', headers });
      const nr = document.getElementById('next-repo');
      const ns = document.getElementById('next-server');
      if (nr && sched.next_repo) nr.textContent = new Date(sched.next_repo).toLocaleString();
      if (ns && sched.next_server) ns.textContent = new Date(sched.next_server).toLocaleString();
    } catch (e) { console.error(e); }
  }

  // Sanitize to reject any script tags in values
  function sanitizeVal(val) {
    if (typeof val === 'string' && val.toLowerCase().includes('<script>')) {
      throw new Error('Invalid content detected');
    }
    return val;
  }

  // Repos Page
  if (document.getElementById('repos-table')) {
    const triggerBtn = document.getElementById('trigger-repos');
    async function loadRepos() {
      await loadSchedule();
      const repos = await request('/api/repos', { method: 'GET', headers });
      const tbody = document.querySelector('#repos-table tbody'); tbody.innerHTML = '';
      repos.forEach(r => {
        const name = sanitizeVal(r.name);
        const branch = sanitizeVal(r.branch);
        const active = sanitizeVal(String(r.active));
        const last_check = sanitizeVal(r.last_check);
        const last_commit = r.last_commit || '';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${name}</td><td>${branch}</td><td>${active}</td><td>${last_check}</td><td>${last_commit}</td><td><button class="btn btn-danger btn-sm" onclick="deleteRepo('${encodeURIComponent(name)}')">Delete</button></td>`;
        tbody.appendChild(tr);
      });
    }
    window.deleteRepo = async (name) => {
      await request(`/api/repos/${name}`, { method: 'DELETE', headers });
      loadRepos();
    };
    triggerBtn.addEventListener('click', async () => {
      triggerBtn.disabled = true;
      triggerBtn.textContent = 'Checking...';
      await request('/api/check/repos', { method: 'POST', headers });
      await loadRepos();
      triggerBtn.textContent = 'Trigger Check';
      triggerBtn.disabled = false;
    });
    document.getElementById('add-repo-form').addEventListener('submit', async e => {
      e.preventDefault();
      const name = e.target.repo.value;
      const branch = e.target.branch.value;
      const tokenVal = e.target.token.value;
      await request('/api/repos', { method: 'POST', headers, body: JSON.stringify({ name, branch, token: tokenVal }) });
      e.target.reset(); loadRepos();
    });
    loadRepos();
  }

  // Servers Page
  if (document.getElementById('servers-table')) {
    const triggerBtnS = document.getElementById('trigger-servers');
    async function loadServers() {
      await loadSchedule();
      const svs = await request('/api/servers', { method: 'GET', headers });
      const tbody = document.querySelector('#servers-table tbody'); tbody.innerHTML = '';
      svs.forEach(s => {
        const host = sanitizeVal(s.host);
        const user = sanitizeVal(s.user);
        const statusBadge = s.active === true ? '<span class="badge bg-success">active</span>' :
                            s.active === false ? '<span class="badge bg-danger">inactive</span>' :
                            s.active === 'retry' ? '<span class="badge bg-warning">retry</span>' :
                            `<span class=\"badge bg-secondary\">${s.active}</span>`;
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${host}</td><td>${user}</td><td>${statusBadge}</td><td>${sanitizeVal(s.last_check)}</td><td><button class="btn btn-danger btn-sm" onclick="deleteServer('${encodeURIComponent(host)}')">Delete</button></td>`;
        tbody.appendChild(tr);
      });
    }
    window.deleteServer = async (host) => { await request(`/api/servers/${host}`, { method: 'DELETE', headers }); loadServers(); };
    triggerBtnS.addEventListener('click', async () => {
      triggerBtnS.disabled = true;
      triggerBtnS.textContent = 'Checking...';
      await request('/api/check/servers', { method: 'POST', headers });
      await loadServers();
      triggerBtnS.textContent = 'Trigger Check';
      triggerBtnS.disabled = false;
    });
    document.getElementById('add-server-form').addEventListener('submit', async e => {
      e.preventDefault();
      const host = e.target.host.value;
      const user = e.target.user.value;
      const key = e.target.key.value;
      await request('/api/servers', { method: 'POST', headers, body: JSON.stringify({ host, user, key }) });
      e.target.reset(); loadServers();
    });
    loadServers();
  }

  // Logs Page
  if (document.getElementById('activity-log')) {
    async function loadLogs() {
      const act = await request('/logs/activity', { method: 'GET', headers });
      const conn = await request('/logs/connectivity', { method: 'GET', headers });
      document.getElementById('activity-log').innerHTML = act.replace(/\n/g,'<br>');
      document.getElementById('connectivity-log').innerHTML = conn.replace(/\n/g,'<br>');
    }
    document.getElementById('refresh-logs').addEventListener('click', loadLogs);
    loadLogs();
  }

  // Commands Page
  if (document.getElementById('commands-table')) {
    const repoSelect = document.getElementById('repo');
    const serverSelect = document.getElementById('server');
    async function loadDropdowns() {
      const repos = await request('/api/repos', { method: 'GET', headers });
      repos.filter(r => r.active === true).forEach(r => { repoSelect.add(new Option(r.name, r.name)); });
      const svs = await request('/api/servers', { method: 'GET', headers });
      svs.filter(s => s.active === true).forEach(s => { serverSelect.add(new Option(s.host, s.host)); });
    }
    async function loadCommands() {
      const cmds = await request('/api/commands', { method: 'GET', headers });
      const tbody = document.querySelector('#commands-table tbody'); tbody.innerHTML = '';
      cmds.forEach(c => {
        const repoName = sanitizeVal(c.repo);
        const serverName = sanitizeVal(c.server);
        const id = c.id;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${id}</td>
          <td>${repoName}</td>
          <td>${serverName}</td>
          <td>${c.command}</td>
          <td>${sanitizeVal(String(c.active))}</td>
          <td>${sanitizeVal(c.last_run)}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="manageSecrets('${id}')">Secrets</button>
            <button class="btn btn-primary btn-sm" onclick="runCommand('${id}')">Run</button>
            <button class="btn btn-danger btn-sm" onclick="deleteCommand('${id}')">Delete</button>
          </td>`;
        tbody.appendChild(tr);
      });
    }
    window.deleteCommand = async (id) => { await request(`/api/commands/${id}`, { method: 'DELETE', headers }); loadCommands(); };
    window.runCommand = async (id) => { const json = await request(`/api/commands/${id}/run`, { method: 'POST', headers }); alert(JSON.stringify(json)); };
    window.manageSecrets = async (id) => {
      // Fetch existing secrets (masked)
      const secrets = await request(`/api/commands/${id}/secrets`, { method: 'GET', headers });
      alert('Current secrets:\n' + (secrets.map(s => `${s.key} (id=${s.id}) = ${s.value}`).join('\n') || '<none>'));
      const action = prompt('Type "add" to add a secret or "delete" to remove', 'add');
      if (action === 'add') {
        const key = prompt('Enter new secret key');
        const value = prompt('Enter secret value');
        if (key && value !== null) {
          const res = await request(`/api/commands/${id}/secrets`, {
            method: 'POST', headers, body: JSON.stringify({ key, value })
          });
          const r = await res.json();
          alert(`Added ${r.key} (id=${r.id}) = ${r.value}`);
        }
      } else if (action === 'delete') {
        const sid = prompt('Enter secret id to delete');
        if (sid) {
          await request(`/api/commands/${id}/secrets/${encodeURIComponent(sid)}`, { method: 'DELETE', headers });
          alert('Deleted secret ' + sid);
        }
      }
      loadCommands();
    };
    document.getElementById('add-command-form').addEventListener('submit', async e => {
      e.preventDefault();
      await request('/api/commands', { method: 'POST', headers, body: JSON.stringify({ 
        repo: repoSelect.value,
        server: serverSelect.value,
        command: e.target.command.value
      }) });
      e.target.reset(); loadCommands();
    });
    await loadDropdowns(); loadCommands();
  }

  // Settings Page
  if (document.getElementById('settings-form')) {
    const form = document.getElementById('settings-form');
    // Load existing settings
    (async () => {
      const settings = await request('/api/settings', { method: 'GET', headers });
      document.getElementById('repo_interval').value = settings.repo_interval;
      document.getElementById('server_interval').value = settings.server_interval;
    })();
    // Handle form submit
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const repoVal = parseInt(document.getElementById('repo_interval').value, 10);
      const srvVal = parseInt(document.getElementById('server_interval').value, 10);
      await request('/api/settings', {
        method: 'POST', headers,
        body: JSON.stringify({ repo_interval: repoVal, server_interval: srvVal })
      });
      alert('Settings saved and schedule updated');
    });
  }
});