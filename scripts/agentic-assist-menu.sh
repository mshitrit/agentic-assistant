#!/usr/bin/env bash
# Interactive menu for user-triggered agentic-assistant scripts.
#
# Usage: scripts/agentic-assist-menu.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_SCRIPTS="$REPO_ROOT/scripts/user"
# shellcheck source=lib/menu.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib/menu.sh"

run_pr_workflow() {
  local url flags=() ctx="" ctx_file=""
  url="$(prompt_required "Jira URL/key or GitHub PR URL")"
  prompt_multiline_optional ctx "Additional instructions (optional):"
  if [[ -n "$ctx" ]]; then
    ctx_file="$(mktemp)"
    printf '%s' "$ctx" >"$ctx_file"
    flags+=(-f "$ctx_file")
  fi
  cd "$REPO_ROOT"
  if [[ -n "$ctx_file" ]]; then
    trap 'rm -f "$ctx_file"' EXIT
  fi
  echo "pr-workflow: Starting (Jira or GitHub PR workflow)..." >&2
  exec "$USER_SCRIPTS/pr-workflow.sh" "${flags[@]}" "$url"
}

run_pr_review() {
  local url
  url="$(prompt_required "PR or MR URL")"
  cd "$REPO_ROOT"
  exec "$USER_SCRIPTS/pr-review.sh" "$url"
}

run_jira_assist() {
  local url flags=(--internal) ctx="" ctx_file=""
  url="$(prompt_required "Jira URL or issue key")"
  prompt_multiline_optional ctx "Additional instructions (optional):"
  if [[ -n "$ctx" ]]; then
    ctx_file="$(mktemp)"
    printf '%s' "$ctx" >"$ctx_file"
    flags+=(-f "$ctx_file")
    trap 'rm -f "$ctx_file"' EXIT
  fi
  cd "$REPO_ROOT"
  exec "$USER_SCRIPTS/jira-assist.sh" "${flags[@]}" "$url"
}

run_sync_living() {
  local remote root
  echo "Leave blank to use script defaults (root@bkr1.local, /root/gitrepos/agentic-assistant)."
  remote="$(prompt_optional "REMOTE (user@host)" "")"
  root="$(prompt_optional "REMOTE_ROOT (path on remote)" "")"
  cd "$REPO_ROOT"
  if [[ -n "$remote" ]]; then export REMOTE="$remote"; fi
  if [[ -n "$root" ]]; then export REMOTE_ROOT="$root"; fi
  exec "$USER_SCRIPTS/sync-living-from-remote.sh"
}

run_reset_living() {
  echo "This overwrites memory/living/ with memory/verified/ (rsync --delete)."
  if ! prompt_yes_no "Continue?" n; then
    echo "Cancelled."
    return 0
  fi
  cd "$REPO_ROOT"
  exec "$USER_SCRIPTS/reset-living-from-verified.sh"
}

run_pr_review_auth() {
  echo
  echo "  1) GitHub"
  echo "  2) GitLab host or MR URL"
  echo "  0) Back"
  local choice target
  read -r -p "Choice: " choice
  case "$choice" in
    1)
      cd "$REPO_ROOT"
      exec "$USER_SCRIPTS/pr-review.sh" auth github
      ;;
    2)
      target="$(prompt_required "GitLab hostname or MR URL")"
      cd "$REPO_ROOT"
      exec "$USER_SCRIPTS/pr-review.sh" auth "$target"
      ;;
    0) return 0 ;;
    *) echo "Invalid choice." >&2 ;;
  esac
}

run_pr_review_setup() {
  echo
  echo "  1) GitHub (gh)"
  echo "  2) GitLab (glab + jq)"
  echo "  3) All"
  echo "  0) Back"
  local choice
  read -r -p "Choice: " choice
  case "$choice" in
    1)
      cd "$REPO_ROOT"
      exec "$USER_SCRIPTS/pr-review.sh" setup github
      ;;
    2)
      cd "$REPO_ROOT"
      exec "$USER_SCRIPTS/pr-review.sh" setup gitlab
      ;;
    3)
      cd "$REPO_ROOT"
      exec "$USER_SCRIPTS/pr-review.sh" setup all
      ;;
    0) return 0 ;;
    *) echo "Invalid choice." >&2 ;;
  esac
}

menu_memory() {
  while true; do
    echo
    echo "Memory Management"
    echo "-----------------"
    echo "  1) Sync living from remote -> verified"
    echo "  2) Reset living from verified"
    echo "  0) Back"
    local choice
    read -r -p "Choice: " choice
    case "$choice" in
      1) run_sync_living ;;
      2) run_reset_living ;;
      0) break ;;
      *) echo "Invalid choice." >&2 ;;
    esac
  done
}

menu_setup() {
  while true; do
    echo
    echo "Setup & tools"
    echo "-------------"
    echo "  1) PR review: authenticate (gh / glab)"
    echo "  2) PR review: install CLIs (gh / glab / jq)"
    echo "  0) Back"
    local choice
    read -r -p "Choice: " choice
    case "$choice" in
      1) run_pr_review_auth ;;
      2) run_pr_review_setup ;;
      0) break ;;
      *) echo "Invalid choice." >&2 ;;
    esac
  done
}

main_menu() {
  while true; do
    echo
    echo "Agentic Assistant"
    echo "================="
    echo "  1) Implement from Jira or GitHub PR"
    echo "  2) Review PR/MR URL"
    echo "  3) Jira analysis (console only, no Jira writes)"
    echo "  4) Memory Management ..."
    echo "  5) Setup & tools ..."
    echo "  0) Exit"
    local choice
    read -r -p "Choice: " choice
    case "$choice" in
      1) run_pr_workflow ;;
      2) run_pr_review ;;
      3) run_jira_assist ;;
      4) menu_memory ;;
      5) menu_setup ;;
      0) echo "Goodbye."; exit 0 ;;
      *) echo "Invalid choice." >&2 ;;
    esac
  done
}

main_menu
