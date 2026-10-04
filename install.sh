#!/usr/bin/env bash
# Golden Thread Quest setup for Mac, Linux and Windows WSL (Phase 2A.1).
#
# Participants paste one line from docs/guides/PILOT.md:
#   curl -fsSL https://raw.githubusercontent.com/beekeeper-lab/golden-thread-quest/v0.2.1/install.sh | bash
#
# It installs what is missing (Apple's command line tools or Git, uv, the GitHub CLI),
# asking before each install. Then it signs the participant in to GitHub, forks and clones
# the repository, puts them on their own pilot branch at the release tag, installs the
# application, creates the `gtq` command and starts the application. Running it again is
# safe: every step checks first and skips what is already done.
#
# Test hooks, used by tests/integration/test_install_script.py and never by participants:
#   GTQ_TEST_SOURCE  clone this local repository instead of forking; skips GitHub entirely
#   GTQ_NAME         the participant's name, instead of asking
#   GTQ_ASSUME_YES   answer yes to every question
#   GTQ_NO_START     do not start the application at the end
#   GTQ_TEST_GH_DOWNLOAD  download the GitHub CLI even when one is installed (with a stub curl)
set -euo pipefail

# Everything is inside main, called on the last line, so `curl | bash` has read the whole
# script before any of it runs: a command that reads standard input cannot eat the rest.
main() {
ORIGINAL_PATH="$PATH"
SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO=sudo
GTQ_VERSION="${GTQ_VERSION:-v0.2.1}"
UPSTREAM="beekeeper-lab/golden-thread-quest"
TARGET="${GTQ_DIR:-$HOME/golden-thread-quest}"
BIN_DIR="$HOME/.local/bin"
export PATH="$BIN_DIR:$PATH"

step() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok() { printf '  ✓ %s\n' "$*"; }
note() { printf '  %s\n' "$*"; }
fail() {
  printf '\n  ✗ %s\n\n  Nothing is broken: fix that and paste the same line again.\n' "$*" >&2
  printf '  Stuck? Post this message in the pilot'"'"'s Slack thread.\n\n' >&2
  exit 1
}
ask() {
  [ -n "${GTQ_ASSUME_YES:-}" ] && return 0
  local reply=""
  printf '  %s [Y/n] ' "$1"
  read -r reply </dev/tty || true
  case "$reply" in [nN]*) return 1 ;; *) return 0 ;; esac
}
have() { command -v "$1" >/dev/null 2>&1; }

cat <<'EOF'

  The Golden Thread Quest — setup
  This takes about ten minutes. It asks before it installs anything.
EOF

# 1. Which computer is this?
case "$(uname -s)" in
  Darwin) OS=mac ;;
  Linux) OS=linux ;;
  *) fail "This setup is for Mac, Linux or Windows WSL. The pilot guide says what to do on Windows." ;;
esac
case "$(uname -m)" in
  x86_64 | amd64) ARCH=amd64 ;;
  arm64 | aarch64) ARCH=arm64 ;;
  *) fail "This computer's processor ($(uname -m)) is not one the setup knows." ;;
esac

# 2. Git
step "1/7  Git"
if [ "$OS" = mac ]; then
  if ! xcode-select -p >/dev/null 2>&1; then
    note "Your Mac needs Apple's free command line tools, which include Git."
    ask "Install them now? A window will open: click Install, then wait." || fail "Git is needed."
    xcode-select --install >/dev/null 2>&1 || true
    note "Waiting for the install window to finish (this can take several minutes)..."
    waited=0
    until xcode-select -p >/dev/null 2>&1; do
      sleep 5
      waited=$((waited + 5))
      [ "$waited" -lt 1800 ] || fail "Apple's tools did not finish installing within 30 minutes."
    done
  fi
elif ! have git; then
  note "Git is not installed. Installing it needs your computer password."
  ask "Install Git now?" || fail "Git is needed."
  if have apt-get; then $SUDO apt-get update -qq && $SUDO apt-get install -y -qq git
  elif have dnf; then $SUDO dnf install -y -q git
  else fail "Install Git with your system's software installer, then paste the line again."
  fi
fi
have git || fail "Git did not install."
ok "Git is ready"

# 3. uv, which also provides Python
step "2/7  uv (it runs the application and brings its own Python)"
if ! have uv; then
  ask "Install uv now? It installs into your home folder and needs no password." ||
    fail "uv is needed."
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null ||
    fail "uv did not install. Check your internet connection."
fi
have uv || fail "uv did not install."
ok "uv is ready"

# 4. The GitHub CLI, which signs in and opens the pull request
step "3/7  The GitHub command line tool"
if [ -n "${GTQ_TEST_GH_DOWNLOAD:-}" ] || { [ -z "${GTQ_TEST_SOURCE:-}" ] && ! have gh; }; then
  ask "Install it now? It installs into your home folder and needs no password." ||
    fail "The GitHub tool is needed to hand in your work."
  # Phase 2A.2: the latest version comes from the release page's redirect, not from
  # api.github.com. The tool is not installed yet, so nothing can be signed in, and the
  # API allows 60 unsigned requests an hour per address: a room of participants behind
  # one office address would hit that. The page redirect is not counted that way.
  latest="$(curl -fsSL -o /dev/null -w '%{url_effective}' https://github.com/cli/cli/releases/latest)" ||
    fail "Could not reach GitHub to download its tool."
  tag="${latest##*/tag/v}"
  case "$tag" in
    '' | *[!0-9.]*) fail "Could not tell which version of GitHub's tool to download." ;;
  esac
  scratch="$(mktemp -d)"
  if [ "$OS" = mac ]; then
    folder="gh_${tag}_macOS_${ARCH}"
    curl -fsSL -o "$scratch/gh.zip" "https://github.com/cli/cli/releases/download/v${tag}/${folder}.zip"
    (cd "$scratch" && unzip -q gh.zip)
  else
    folder="gh_${tag}_linux_${ARCH}"
    curl -fsSL "https://github.com/cli/cli/releases/download/v${tag}/${folder}.tar.gz" |
      tar -xz -C "$scratch"
  fi
  mkdir -p "$BIN_DIR"
  mv "$scratch/$folder/bin/gh" "$BIN_DIR/gh"
  rm -rf "$scratch"
fi
[ -n "${GTQ_TEST_SOURCE:-}" ] || have gh || fail "The GitHub tool did not install."
ok "GitHub tool is ready"

# 5. Sign in to GitHub
step "4/7  Sign in to GitHub"
if [ -n "${GTQ_TEST_SOURCE:-}" ]; then
  LOGIN="pilot-test"
  EMAIL="pilot-test@example.com"
else
  if ! gh auth status >/dev/null 2>&1; then
    note "Your browser will open. Copy the code shown below, paste it on the GitHub page,"
    note "and click Authorize. No GitHub account yet? Create one first at github.com."
    gh auth login --hostname github.com --git-protocol https --web </dev/tty ||
      fail "GitHub sign-in did not finish."
  fi
  gh auth setup-git --hostname github.com || fail "Could not connect Git to your GitHub sign-in."
  LOGIN="$(gh api user --jq .login)" || fail "Could not read your GitHub account."
  id="$(gh api user --jq .id)" || fail "Could not read your GitHub account."
  EMAIL="${id}+${LOGIN}@users.noreply.github.com"
fi
ok "Signed in as $LOGIN"

# 6. Your copy and your branch
step "5/7  Your copy of the quest"
if [ -d "$TARGET/.git" ]; then
  ok "Found your copy at $TARGET"
elif [ -e "$TARGET" ]; then
  fail "$TARGET already exists and is not a copy of the quest. Move or rename it."
elif [ -n "${GTQ_TEST_SOURCE:-}" ]; then
  git clone --quiet "$GTQ_TEST_SOURCE" "$TARGET"
  git -C "$TARGET" remote set-url origin "https://github.com/$LOGIN/golden-thread-quest.git"
  git -C "$TARGET" remote add upstream "https://github.com/$UPSTREAM.git"
else
  gh repo fork "$UPSTREAM" --clone=false >/dev/null 2>&1 || true
  parent=""
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    parent="$(gh repo view "$LOGIN/golden-thread-quest" --json parent --jq .parent.nameWithOwner 2>/dev/null || true)"
    [ "$parent" = "$UPSTREAM" ] && break
    sleep 3
  done
  [ "$parent" = "$UPSTREAM" ] ||
    fail "Could not make your copy on GitHub. If you already have a repository called golden-thread-quest, rename it."
  git clone --quiet "https://github.com/$LOGIN/golden-thread-quest.git" "$TARGET" ||
    fail "Could not download your copy from GitHub."
  git -C "$TARGET" remote add upstream "https://github.com/$UPSTREAM.git"
fi
cd "$TARGET"
if [ -z "${GTQ_TEST_SOURCE:-}" ]; then
  git fetch --quiet upstream tag "$GTQ_VERSION" || fail "Could not download version $GTQ_VERSION."
  git fetch --quiet origin || true
fi

# A copy that already has a pilot branch keeps it and its name. Asking again, and making a
# new branch from a differently typed name, would hide every quest done so far.
current="$(git symbolic-ref --quiet --short HEAD || true)"
BRANCH=""
case "$current" in pilot/*) BRANCH="$current" ;; esac
[ -n "$BRANCH" ] || BRANCH="$(git for-each-ref --count=1 --format='%(refname:short)' refs/heads/pilot/)"
if [ -z "$BRANCH" ]; then
  remote="$(git for-each-ref --count=1 --format='%(refname:short)' refs/remotes/origin/pilot/)"
  [ -z "$remote" ] || BRANCH="${remote#origin/}"
fi
NAME=""
[ -z "$BRANCH" ] || NAME="$(git config --local user.name || true)"
[ -n "$NAME" ] || NAME="${GTQ_NAME:-}"
while [ -z "$NAME" ]; do
  printf '  Your first name (it labels your work for the reviewer): '
  read -r NAME </dev/tty || fail "No name given."
done
if [ -z "$BRANCH" ]; then
  SLUG="$(printf '%s' "$NAME" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//; s/-*$//')"
  BRANCH="pilot/${SLUG:-$LOGIN}"
fi
git config user.name "$NAME"
git config user.email "$EMAIL"

switch_failed="Could not open your branch $BRANCH. If you changed files by hand, ask in Slack."
if [ "$current" = "$BRANCH" ]; then :
elif git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git switch --quiet "$BRANCH" || fail "$switch_failed"
elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git switch --quiet --track "origin/$BRANCH" || fail "$switch_failed"
else
  git switch --quiet -c "$BRANCH" "$GTQ_VERSION" || fail "$switch_failed"
fi
ok "Your copy is at $TARGET, on $BRANCH"

# 7. The application
step "6/7  Installing the application"
uv venv --quiet --allow-existing --python '>=3.10' .venv || fail "Could not set up Python."
uv pip install --quiet --python .venv/bin/python -e . || fail "Could not install the application."
ok "Application installed"

# 8. The gtq command
step "7/7  The gtq command"
mkdir -p "$BIN_DIR"
cat >"$BIN_DIR/gtq" <<EOF
#!/bin/sh
# The Golden Thread Quest. Made by install.sh; running install.sh again remakes it.
if [ \$# -eq 0 ]; then
  echo "gtq start       start the application and open it in your browser"
  echo "gtq hand-in     send your quest work to your reviewer"
  echo "gtq get-review  bring in your reviewer's decision"
  exit 0
fi
cd "$TARGET" || exit 1
exec "$TARGET/.venv/bin/python" -m quest_app.cli "\$@"
EOF
chmod +x "$BIN_DIR/gtq"
case ":$ORIGINAL_PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    # Every shell start-up file that exists, and on a Mac always zsh's, the default shell.
    # With none at all, ~/.profile, which login shells read.
    wrote=""
    for profile in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
      if [ -f "$profile" ] || { [ "$OS" = mac ] && [ "$profile" = "$HOME/.zshrc" ]; }; then
        # shellcheck disable=SC2016 # the profile expands it, not this script
        grep -qs '.local/bin' "$profile" || printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >>"$profile"
        wrote=1
      fi
    done
    # shellcheck disable=SC2016
    [ -n "$wrote" ] || printf 'export PATH="$HOME/.local/bin:$PATH"\n' >>"$HOME/.profile"
    ;;
esac
ok "gtq is ready"

cat <<EOF

  All set. From now on, in any new terminal window:

    gtq start        start the application and open it in your browser
    gtq hand-in      send your quest work to your reviewer
    gtq get-review   bring in your reviewer's decision

EOF
if [ -z "${GTQ_NO_START:-}" ] && ask "Start the application now?"; then
  note "It opens in your browser. Leave this window open; press Ctrl-C here to stop it."
  exec "$BIN_DIR/gtq" start
fi
}

main "$@"
