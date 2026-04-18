#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="${AUTOCLAW_SERVICE_NAME:-autoclaw}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${AUTOCLAW_CONFIG_DIR:-$CONFIG_HOME/autoclaw}"
DATA_DIR="${AUTOCLAW_DATA_DIR:-$DATA_HOME/autoclaw}"
VENV_DIR="${AUTOCLAW_VENV_DIR:-$DATA_DIR/venv}"
CONFIG_PATH="${AUTOCLAW_CONFIG:-$CONFIG_DIR/config.toml}"
ENV_FILE_PATH="${AUTOCLAW_ENV_FILE:-$CONFIG_DIR/autoclaw.env}"
UNIT_DIR="$CONFIG_HOME/systemd/user"
UNIT_PATH="$UNIT_DIR/$SERVICE_NAME.service"
SYSTEMCTL_BIN="${AUTOCLAW_SYSTEMCTL_BIN:-systemctl}"
INSTALL_MODE="wheel"
EXTRA_SPEC=""
FORCE_INIT=0
NO_START=0

usage() {
  cat <<'EOF'
Usage: scripts/install-systemd-user.sh [options]

Installs AutoClaw into a dedicated user venv, initializes config/data,
renders a user systemd unit, and enables the service.

Options:
  --editable       Install from the repo in editable mode
  --postgres       Install the postgres extra
  --force-init     Re-write the generated config.toml during autoclaw init
  --no-start       Install/enable the unit but do not start it now
  -h, --help       Show this help

Environment overrides:
  AUTOCLAW_CONFIG_DIR, AUTOCLAW_DATA_DIR, AUTOCLAW_VENV_DIR,
  AUTOCLAW_CONFIG, AUTOCLAW_ENV_FILE, AUTOCLAW_SERVICE_NAME,
  AUTOCLAW_SYSTEMCTL_BIN
EOF
}

while (($# > 0)); do
  case "$1" in
    --editable)
      INSTALL_MODE="editable"
      ;;
    --postgres)
      EXTRA_SPEC="[postgres]"
      ;;
    --force-init)
      FORCE_INIT=1
      ;;
    --no-start)
      NO_START=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$UNIT_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip wheel

INSTALL_SPEC="$REPO_ROOT$EXTRA_SPEC"
if [[ "$INSTALL_MODE" == "editable" ]]; then
  "$VENV_DIR/bin/pip" install -e "$INSTALL_SPEC"
else
  "$VENV_DIR/bin/pip" install "$INSTALL_SPEC"
fi

INIT_ARGS=(init --config "$CONFIG_PATH" --data-dir "$DATA_DIR")
if (( FORCE_INIT )); then
  INIT_ARGS+=(--force)
fi
"$VENV_DIR/bin/autoclaw" "${INIT_ARGS[@]}"

SERVICE_INSTALL_ARGS=(
  service install
  --name "$SERVICE_NAME"
  --config "$CONFIG_PATH"
  --data-dir "$DATA_DIR"
  --env-file "$ENV_FILE_PATH"
  --unit-dir "$UNIT_DIR"
  --force
)
if (( NO_START )); then
  SERVICE_INSTALL_ARGS+=(--no-start)
fi
AUTOCLAW_SYSTEMCTL_BIN="$SYSTEMCTL_BIN" \
  "$VENV_DIR/bin/autoclaw" "${SERVICE_INSTALL_ARGS[@]}"

echo "Installed $SERVICE_NAME.service"
echo "  unit:   $UNIT_PATH"
echo "  config: $CONFIG_PATH"
echo "  data:   $DATA_DIR"
echo "  venv:   $VENV_DIR"
if (( NO_START )); then
  echo "Service was not started. Start it with: systemctl --user start $SERVICE_NAME.service"
else
  echo "Check status with: systemctl --user status $SERVICE_NAME.service --no-pager"
fi
echo "To keep the user service running after logout, enable linger separately if desired:"
echo "  sudo loginctl enable-linger $USER"
