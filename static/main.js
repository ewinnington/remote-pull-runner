document.addEventListener('DOMContentLoaded', () => {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  const token = getCookie('auth_token');
  const headers = token ? { 'X-Auth-Token': token, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };

  // Error-handling fetch wrapper
  async function request(url, opts) {
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

  // Repos Page
  if (document.getElementById('repos-table')) {
    async function loadRepos() {
      const repos = await request('/api/repos', { method: 'GET', headers });
      const tbody = document.querySelector('#repos-table tbody'); tbody.innerHTML = '';
      repos.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.name}</td><td>${r.branch}</td><td>${r.active}</td><td>${r.last_check}</td>
          <td><button class="btn btn-danger btn-sm" onclick="deleteRepo('${r.name}')">Delete</button></td>`;
        tbody.appendChild(tr);
      });
    }
    window.deleteRepo = async (name) => { await request(`/api/repos/${name}`, { method: 'DELETE', headers }); loadRepos(); };
    document.getElementById('add-repo-form').addEventListener('submit', async e => {
      e.preventDefault();
      const name = e.target.repo.value;
      const branch = e.target.branch.value;
      const tokenVal = e.target.token.value;
      await request('/api/repos', { method: 'POST', headers, body: JSON.stringify({ name, branch, token: tokenVal }) });
      e.target.reset(); loadRepos();
    });
    document.getElementById('trigger-repos').addEventListener('click', async () => { await request('/api/check/repos', { method: 'POST', headers }); alert('Triggered repos check'); });
    loadRepos();
  }

  // Servers Page
  if (document.getElementById('servers-table')) {
    async function loadServers() {
      const svs = await request('/api/servers', { method: 'GET', headers });
      const tbody = document.querySelector('#servers-table tbody'); tbody.innerHTML = '';
      svs.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${s.host}</td><td>${s.user}</td><td>${s.active}</td><td>${s.last_check}</td>
          <td><button class="btn btn-danger btn-sm" onclick="deleteServer('${s.host}')">Delete</button></td>`;
        tbody.appendChild(tr);
      });
    }
    window.deleteServer = async (host) => { await request(`/api/servers/${host}`, { method: 'DELETE', headers }); loadServers(); };
    document.getElementById('add-server-form').addEventListener('submit', async e => {
      e.preventDefault();
      const host = e.target.host.value;
      const user = e.target.user.value;
      const key = e.target.key.value;
      await request('/api/servers', { method: 'POST', headers, body: JSON.stringify({ host, user, key }) });
      e.target.reset(); loadServers();
    });
    document.getElementById('trigger-servers').addEventListener('click', async () => { await request('/api/check/servers', { method: 'POST', headers }); alert('Triggered servers check'); });
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
    async function loadCommands() {
      const cmds = await request('/api/commands', { method: 'GET', headers });
      const tbody = document.querySelector('#commands-table tbody'); tbody.innerHTML = '';
      cmds.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${c.id}</td>
          <td>${c.repo}</td>
          <td>${c.server}</td>
          <td>${c.command}</td>
          <td>${c.active}</td>
          <td>${c.last_run}</td>
          <td>
            <button class="btn btn-primary btn-sm" onclick="runCommand('${c.id}')">Run</button>
            <button class="btn btn-danger btn-sm" onclick="deleteCommand('${c.id}')">Delete</button>
          </td>`;
        tbody.appendChild(tr);
      });
    }
    window.deleteCommand = async (id) => { await request(`/api/commands/${id}`, { method: 'DELETE', headers }); loadCommands(); };
    window.runCommand = async (id) => { const json = await request(`/api/commands/${id}/run`, { method: 'POST', headers }); alert(JSON.stringify(json)); };
    document.getElementById('add-command-form').addEventListener('submit', async e => {
      e.preventDefault();
      const repo = e.target.repo.value;
      const server = e.target.server.value;
      const command = e.target.command.value;
      await request('/api/commands', { method: 'POST', headers, body: JSON.stringify({ repo, server, command }) });
      e.target.reset(); loadCommands();
    });
    loadCommands();
  }
});