#!/usr/bin/env bash
set -euo pipefail

OWNER="${OWNER:-chenjun321}"
REPO="${REPO:-enterprise-agentops-platform}"
VISIBILITY="${VISIBILITY:-private}"
BRANCH="${BRANCH:-main}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-Initialize enterprise-agentops-platform}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Publishing ${ROOT_DIR} to https://github.com/${OWNER}/${REPO}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. Please install git first."
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "GitHub CLI is missing. Installing gh with Homebrew..."
    brew install gh
  else
    echo "GitHub CLI is missing. Install it from https://cli.github.com/ and rerun this script."
    exit 1
  fi
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not logged in. Starting gh auth login..."
  gh auth login
fi

if [ ! -d .git ]; then
  git init
fi

git branch -M "$BRANCH"

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "https://github.com/${OWNER}/${REPO}.git"
else
  git remote add origin "https://github.com/${OWNER}/${REPO}.git"
fi

if ! gh repo view "${OWNER}/${REPO}" >/dev/null 2>&1; then
  gh repo create "${OWNER}/${REPO}" "--${VISIBILITY}" --source=. --remote=origin
fi

git add -A

if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -m "$COMMIT_MESSAGE"
fi

git push -u origin "$BRANCH"

echo "Done: https://github.com/${OWNER}/${REPO}"
