# Remote-Pull-Runner

Remote-Pull-Runner is a simple CI-CD tool that integrates with Github. 

1) It allows you to enroll a remote github repository in the tool (saved in json config).
Private repos are supported with a personal access token. The tool uses the Github API to check for changes in the repo. It uses the Github API to get the last commit time and compares it with the last check time. If the last commit time is greater than the last check time, it is considered a change. The tool also uses the Github API to get the list of branches and allows you to choose which branch to monitor (default main).
1a) Stores github PATs with expiration date. 
2) It allows you to enroll a remote server (or localhost) in the tool (saved in json config) - with ssh keys only. 
3) It presents a simple html web interface where: 
  - you can enroll repos, view the list, set them active / inactive, delete them, a configurable timer to check the repo for changes (default 24 hours - down to 1 minute), this also shows the last commit time and last check time. All this information is saved in the json config. You can also choose which branch to monitor (default main). 
  - you can enroll servers, view the list, set them active / inactive, delete them. You see last login time and last check time. All this information is saved in the json config. Servers are checked for connectivity every 12 hours (configurable) with a retry policy (3 retries, 5 minutes apart). If a server is unreachable, it is marked as unreachable and the last check time is updated. This information is saved in the json config and written to a log file "connectivity-yyyy.log" in the log directory. 
  - you can choose a repo and a server combination and give a command to run on the server when a new commit is detected. This will ssh into the server and run the command. The command can be a shell script or a single command. The command is saved in the json config. This is the main feature of the tool.
4) The tool runs as a daemon and checks for changes and connectivity on the schedule. If a change is detected, it will ssh into the server and run the command. The tool also logs all activity to a log file "activity-yyyy.log" in the the log directory.
5) The tool offers a way to trigger a check manually from the web interface. This is useful for testing and debugging.
6) The tool offers a way to check server from the web interface. This triggers a ssh and runs one command - uptime. This is useful for testing and debugging.
7) The tool offers a way to check repo from the web interface. This triggers a git pull and runs one command - git status. Then it cleans out the repo from the cache. This is useful for testing and debugging.


8) The tool offers a way to check the logs activity and connectivity from the web interface. This shows the last 10 lines of the log file. This is useful for testing and debugging.


This UI is simple and straightforward. It is built using Python 3.12.3 with Flask and Bootstrap. It is responsive and works on mobile devices. It is also easy to customize and extend. 

Since the UI is served only on a Tailscale network, it is secure and does not require any authentication account - but does ask for a token that is then saved as a cookie on the device accessing the UI. If the cookie is not present, the UI is read-only. Any action requires the token field to be populated. On first startup a token is generated and saved, this token is necessary for any write activity. After that, this token is will be saved in the config file. The token is used to authenticate the user and is saved in the json config. The token is a random string of 32 characters. It is only used to authenticate the user. 

## Implementation notes
- Split the runtime into three processes:
  - API + UI: Flask app that owns config CRUD, token auth, log viewer.
  - Scheduler: Small service that enqueues “check repo” and “check server” jobs on a message queue.
  - Worker: Executes jobs (GitHub API call or SSH command) with exponential-backoff & result reporting.
- Provide a /health endpoint to respond ith the processes are running and the last time they were checked. This is useful for monitoring and debugging.


