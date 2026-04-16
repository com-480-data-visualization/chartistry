#!/usr/bin/env bash
# Publish website/ from a feature branch to the repo root on gh-pages (GitHub Pages).
# Usage: ./scripts/deploy-gh-pages.sh [source_branch]
# Default source branch: osc_branch

set -euo pipefail

SOURCE_BRANCH="${1:-osc_branch}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if ! git rev-parse --verify "origin/$SOURCE_BRANCH" >/dev/null 2>&1; then
  echo "error: origin/$SOURCE_BRANCH does not exist. Fetch first: git fetch origin" >&2
  exit 1
fi

if ! git rev-parse --verify origin/gh-pages >/dev/null 2>&1; then
  echo "error: origin/gh-pages not found. Is the branch on the remote?" >&2
  exit 1
fi

CURRENT="$(git branch --show-current || true)"
echo "==> fetch"
git fetch origin

echo "==> switch to gh-pages (track remote; creates local branch if missing)"
git switch -C gh-pages origin/gh-pages

echo "==> remove old published root files (gh-pages only)"
rm -rf css js public index.html website

echo "==> copy website/ from origin/$SOURCE_BRANCH"
git checkout "origin/$SOURCE_BRANCH" -- website/
test -f website/index.html || { echo "error: website/index.html missing after checkout" >&2; exit 1; }

cp -r website/css .
cp -r website/js .
cp -r website/public .
cp website/index.html .
rm -rf website
# checkout -- website/ leaves paths staged; remove from index so we only commit root layout
git rm -rf --cached website 2>/dev/null || true

git add index.html css js public

if git diff --cached --quiet; then
  echo "Nothing new to commit on gh-pages."
else
  git commit -m "Deploy website from $SOURCE_BRANCH"
fi

echo "==> push gh-pages"
git push origin gh-pages

echo "==> restore working branch"
if [[ -n "$CURRENT" && "$CURRENT" != "gh-pages" ]]; then
  git switch "$CURRENT"
else
  git switch "$SOURCE_BRANCH" 2>/dev/null || git switch -c "$SOURCE_BRANCH" "origin/$SOURCE_BRANCH"
fi

echo "Done."
