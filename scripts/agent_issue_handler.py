#!/usr/bin/env python3
"""
Antigravity Serverless Issue Handler for GitHub Actions.
Automates requirement analysis, implementation plan drafting, and comment-based approval.

Repository standards: Agents.md (Python 3 standard library only, strict no emojis).
"""

import json
import os
import sys
import urllib.error
import urllib.request


def get_env_var(name, default=""):
    return os.environ.get(name, default)


def post_github_comment(repo, issue_number, token, body):
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "Antigravity-Actions/1.0"
    }
    payload = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Comment successfully posted to Issue #{issue_number} (HTTP {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"Failed to post comment to Issue #{issue_number}: HTTP {e.code} - {e.reason}\n")
        return False


def generate_plan_with_gemini(api_key, issue_title, issue_body):
    prompt = f"""You are Antigravity, an AI development agent working on the repository dc-missed-collection-analysis (Washington, DC Department of Public Works missed collection analysis).

Strict repository standard from Agents.md:
- Absolutely NO emojis anywhere in output or plans.
- Lo-fi monochrome technical style.
- Pure Python 3 standard library for pipeline scripts.
- Target audience is DPW, route supervisors, and data analysts.

An issue has been opened:
Title: {issue_title}
Description:
{issue_body}

Analyze the requirements, draft a concrete implementation plan, list specific files to inspect or modify, and note that execution is paused awaiting review/approval reply before any code changes will be made. Format your response cleanly in Markdown without emojis."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception as e:
        sys.stderr.write(f"Gemini API request failed: {e}\n")
    return ""


def build_fallback_plan(issue_title, issue_body):
    return f"""### Antigravity Automated Implementation Plan

#### Requirements Analysis
- Issue: {issue_title}
- Summary of reported requirements:
{issue_body}

#### Proposed Action Steps
1. Review relevant codebase modules and architectural guidelines in `Agents.md`.
2. Inspect target data pipelines or application files (`index.html`, `map.html`, `report.html`, `scripts/`).
3. Prepare required modifications ensuring zero external pip dependencies and strict compliance with repository standards.
4. Execute validation suite and verify output data and cartography integrity.

#### Approval Gate
Pursuant to the Automated Issue Triage & Planning Protocol:
Execution is paused. Please review the plan above and reply with your approval or requested revisions to proceed with implementation."""


def handle_issue_opened(event, repo, token, gemini_key):
    issue = event.get("issue", {})
    issue_number = issue.get("number")
    issue_title = issue.get("title", "")
    issue_body = issue.get("body", "")
    user = issue.get("user", {}).get("login", "")

    if user.endswith("[bot]"):
        print(f"Skipping issue created by bot user: {user}")
        return

    print(f"Processing newly opened Issue #{issue_number}: {issue_title}")

    plan_text = ""
    if gemini_key:
        print("Querying Gemini API for customized implementation plan...")
        plan_text = generate_plan_with_gemini(gemini_key, issue_title, issue_body)

    if not plan_text:
        print("Using standard structured implementation plan template...")
        plan_text = build_fallback_plan(issue_title, issue_body)

    post_github_comment(repo, issue_number, token, plan_text)


def handle_issue_comment(event, repo, token):
    issue = event.get("issue", {})
    comment = event.get("comment", {})
    issue_number = issue.get("number")
    comment_user = comment.get("user", {}).get("login", "")
    comment_body = comment.get("body", "").strip()

    if comment_user.endswith("[bot]"):
        print(f"Skipping comment posted by bot user: {comment_user}")
        return

    print(f"Processing comment on Issue #{issue_number} from {comment_user}")

    lower_body = comment_body.lower()
    approval_keywords = ["approved", "approve", "lgtm", "proceed", "looks good"]
    is_approved = any(kw in lower_body for kw in approval_keywords)

    if is_approved:
        ack_body = f"""### Approval Received

Maintainer approval detected from @{comment_user}:
> "{comment_body}"

The implementation plan is authorized. Proceeding with execution of required changes."""
        post_github_comment(repo, issue_number, token, ack_body)
    else:
        print(f"Comment from {comment_user} did not trigger approval keywords; recorded on thread.")


def main():
    event_path = get_env_var("GITHUB_EVENT_PATH")
    event_name = get_env_var("GITHUB_EVENT_NAME")
    repo = get_env_var("GITHUB_REPOSITORY", "zacheadams/dc-missed-collection-analysis")
    token = get_env_var("GITHUB_TOKEN")
    gemini_key = get_env_var("GEMINI_API_KEY")

    if not event_path or not os.path.exists(event_path):
        print("No GITHUB_EVENT_PATH detected; exiting.")
        return 0

    if not token:
        sys.stderr.write("Error: GITHUB_TOKEN is required to interact with GitHub API.\n")
        return 1

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    action = event.get("action", "")
    print(f"Received GitHub event: {event_name}.{action}")

    if event_name == "issues" and action == "opened":
        handle_issue_opened(event, repo, token, gemini_key)
    elif event_name == "issue_comment" and action == "created":
        handle_issue_comment(event, repo, token)
    else:
        print(f"Event {event_name}.{action} is not targeted for triage; exiting.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
