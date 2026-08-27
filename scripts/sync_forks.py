#!/usr/bin/env python3
"""Sync all fork repositories in the GLiNet-Community-Scripts org with their upstreams."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

GITHUB_API = "https://api.github.com"
ORG_NAME = os.environ.get("GITHUB_ORG", "GLiNet-Community-Scripts")
GITHUB_TOKEN = os.environ.get("SYNC_TOKEN") or os.environ.get("GITHUB_TOKEN", "")


def api_request(path: str, method: str = "GET", data: dict | None = None) -> dict | list | None:
    url = f"{GITHUB_API}{path}" if path.startswith("/") else path
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GLiNet-Fork-Sync/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    body = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(err_body)
        except Exception:
            return {"error": str(exc), "body": err_body, "status": exc.code}
    except Exception as exc:
        return {"error": str(exc)}


def get_all_org_repos() -> list[dict]:
    repos = []
    page = 1
    while True:
        data = api_request(f"/orgs/{ORG_NAME}/repos?per_page=100&page={page}")
        if not data or not isinstance(data, list):
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def get_repo_details(repo_name: str) -> dict:
    data = api_request(f"/repos/{ORG_NAME}/{repo_name}")
    return data if isinstance(data, dict) else {}


def sync_fork(repo_name: str, branch: str, parent_full: str) -> dict:
    """Attempt to sync a fork using the GitHub merge-upstream API."""
    data = api_request(
        f"/repos/{ORG_NAME}/{repo_name}/merge-upstream",
        method="POST",
        data={"branch": branch},
    )

    if not isinstance(data, dict):
        return {"status": "error", "message": "Invalid response"}

    msg = str(data.get("message", "")).strip()
    merge_type = str(data.get("merge_type", "")).strip()

    if "fast-forward" in msg.lower() or merge_type == "fast-forward":
        return {"status": "fast-forward", "message": f"Fast-forwarded from {parent_full}:{branch}"}
    elif "not behind" in msg.lower() or "already" in msg.lower():
        return {"status": "up-to-date", "message": f"Already up to date with {parent_full}:{branch}"}
    elif "conflict" in msg.lower() or data.get("status") == 409:
        return {"status": "conflict", "message": f"Merge conflict with {parent_full}:{branch}"}
    elif "rule violation" in msg.lower():
        return {"status": "protected", "message": f"Branch protected (requires PR): {msg}"}
    elif "workflow" in msg.lower():
        return {"status": "workflow-scope", "message": f"Needs workflow scope: {msg}"}
    else:
        return {"status": "error", "message": msg or "Unknown error"}


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN or SYNC_TOKEN environment variable is required.")
        sys.exit(1)

    print(f"=== GL.iNet Community Scripts - Nightly Fork Sync ===")
    print(f"Org: {ORG_NAME}")
    print()

    repos = get_all_org_repos()
    print(f"Found {len(repos)} total repositories in {ORG_NAME}")

    forks = []
    for r in repos:
        if r.get("fork"):
            forks.append(r)

    print(f"Found {len(forks)} fork repositories to sync")
    print("-" * 70)

    results = []
    counts = {"fast-forward": 0, "up-to-date": 0, "conflict": 0, "protected": 0, "workflow-scope": 0, "error": 0}

    for fork in sorted(forks, key=lambda x: x["name"].lower()):
        name = fork["name"]
        details = get_repo_details(name)
        parent = details.get("parent") or {}
        parent_full = parent.get("full_name", "unknown")
        branch = details.get("default_branch", "main")

        result = sync_fork(name, branch, parent_full)
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1

        icon = {
            "fast-forward": "✅",
            "up-to-date": "⏭️ ",
            "conflict": "⚠️ ",
            "protected": "🔒",
            "workflow-scope": "🔑",
            "error": "❌",
        }.get(status, "❓")

        print(f"  {icon} {name:38} | {result['message']}")
        results.append({"name": name, "parent": parent_full, "branch": branch, **result})
        time.sleep(0.3)

    print("-" * 70)
    print("Summary:")
    print(f"  ✅ Fast-forwarded:    {counts['fast-forward']}")
    print(f"  ⏭️  Already up to date: {counts['up-to-date']}")
    print(f"  ⚠️  Conflicts:          {counts['conflict']}")
    print(f"  🔒 Branch protected:  {counts['protected']}")
    print(f"  🔑 Workflow scope:    {counts['workflow-scope']}")
    print(f"  ❌ Errors:            {counts['error']}")
    print(f"  Total forks checked:  {len(forks)}")

    # Set GitHub Actions output if running in CI
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write("## 🔄 Nightly Fork Sync Summary\n\n")
            f.write(f"| Status | Count |\n|---|---|\n")
            f.write(f"| ✅ Fast-forwarded | {counts['fast-forward']} |\n")
            f.write(f"| ⏭️ Already up to date | {counts['up-to-date']} |\n")
            f.write(f"| ⚠️ Conflicts | {counts['conflict']} |\n")
            f.write(f"| 🔒 Branch protected | {counts['protected']} |\n")
            f.write(f"| 🔑 Workflow scope needed | {counts['workflow-scope']} |\n")
            f.write(f"| ❌ Errors | {counts['error']} |\n\n")
            f.write("### Details\n\n")
            f.write("| Repository | Upstream | Status | Message |\n|---|---|---|---|\n")
            for r in results:
                icon = {"fast-forward": "✅", "up-to-date": "⏭️", "conflict": "⚠️", "protected": "🔒", "workflow-scope": "🔑", "error": "❌"}.get(r["status"], "❓")
                f.write(f"| `{r['name']}` | `{r['parent']}` | {icon} {r['status']} | {r['message']} |\n")

    if counts["conflict"] > 0 or counts["error"] > 0:
        print("\nNote: Some forks need attention (conflicts or errors).")


if __name__ == "__main__":
    main()
