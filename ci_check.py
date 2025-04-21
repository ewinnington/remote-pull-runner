#!/usr/bin/env python3
import argparse
from datetime import datetime
from github import Github

def parse_args():
    parser = argparse.ArgumentParser(description="Simple CI check script")
    parser.add_argument("--repo", required=True, help="GitHub repository full name e.g. user/repo")
    parser.add_argument("--token", help="GitHub access token")
    parser.add_argument("--last-check", required=True, help="Last check time in ISO format")
    return parser.parse_args()

def main():
    args = parse_args()
    g = Github(args.token) if args.token else Github()
    repo = g.get_repo(args.repo)
    last_commit = repo.get_commits()[0].commit.committer.date
    last_check_time = datetime.fromisoformat(args.last_check)
    if last_commit > last_check_time:
        print(f"New commit detected: {last_commit.isoformat()}")
    else:
        print("No new commits")

if __name__ == "__main__":
    main()