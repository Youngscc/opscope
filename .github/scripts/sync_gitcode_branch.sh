#!/usr/bin/env bash
set -euo pipefail

target_url=${1:?target repository is required}
target_branch=${2:?target branch is required}
dry_run=${3:-false}
case "$dry_run" in true|false) ;; *) echo 'Invalid dry-run value' >&2; exit 2 ;; esac
git check-ref-format "refs/heads/$target_branch"
source_sha=$(git rev-parse --verify 'HEAD^{commit}')
target_ref="refs/heads/$target_branch"

# A shallow source can falsely appear unrelated to an older target commit.
if [ "$(git rev-parse --is-shallow-repository)" = true ]; then
  echo 'Source history is shallow; checkout with fetch-depth: 0.' >&2
  exit 1
fi

remote_state=$(git ls-remote --heads "$target_url" "$target_ref")
if [ -n "$remote_state" ]; then
  git fetch --no-tags "$target_url" "$target_ref"
  target_sha=$(git rev-parse 'FETCH_HEAD^{commit}')
  if ! git merge-base --is-ancestor "$target_sha" "$source_sha"; then
    echo 'Target contains commits absent from the source; refusing to overwrite.' >&2
    exit 1
  fi
fi

push_options=()
if [ "$dry_run" = true ]; then push_options+=(--dry-run); fi
# Explicit refspec and disabled followTags keep every other branch/tag untouched.
git -c push.followTags=false push "${push_options[@]}" \
  "$target_url" "$source_sha:$target_ref"
if [ "$dry_run" = true ]; then
  echo "Dry run passed: $source_sha -> $target_ref (no writes)."
  exit 0
fi

remote_state=$(git ls-remote --heads "$target_url" "$target_ref")
actual_sha=${remote_state%%[[:space:]]*}
if [ "$actual_sha" != "$source_sha" ]; then
  echo 'Target SHA differs after push; inspect concurrent updates.' >&2
  exit 1
fi
echo "Verified: $source_sha -> $target_ref"
