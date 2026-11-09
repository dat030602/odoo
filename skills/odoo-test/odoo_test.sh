#!/usr/bin/env bash
# odoo_test.sh - run Odoo unit tests and XML-RPC scenarios against a THROW-AWAY test database.
#
#   ./odoo_test.sh unit  <module> [test-tags]   Odoo unit tests (first run installs: -i; afterwards use ODOO_TEST_ACTION=-u)
#   ./odoo_test.sh serve [module]               start a background test server on the existing test DB
#   ./odoo_test.sh stop                         stop the server started by 'serve' (only that pid)
#   ./odoo_test.sh rpc   [rpc_test.py args]     run rpc_test.py against the test server
#   ./odoo_test.sh all   <module>               unit -> serve -> rpc (smoke + scenarios/<module>/) -> stop
#
# Settings (env or ODOO_* keys in .env):
#   ODOO_TEST_DB    test database name, must contain "test"   (default for unit/all: test_<module>)
#   ODOO_ROOT       folder containing odoo-bin                (default: first parent dir with odoo-bin)
#   ODOO_CONF       default $ODOO_ROOT/odoo.conf
#   ODOO_PYTHON     default $ODOO_ROOT/venv/bin/python3
#   ODOO_TEST_PORT  test server port (default 8070)    ODOO_UNIT_PORT  unit-test port (default 8071)
#   ODOO_TEST_ACTION  -i (default) or -u    ODOO_TEST_LOGDIR  default /tmp    ODOO_WAIT  startup wait, default 180s
#
# Logs: $ODOO_TEST_LOGDIR/odoo_unit_<module>.log and $ODOO_TEST_LOGDIR/odoo_test_server.log
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "ERROR: $*" >&2; exit 2; }

find_root() {
  local d="$HERE"
  while [ "$d" != "/" ]; do
    [ -f "$d/odoo-bin" ] && { echo "$d"; return; }
    d="$(dirname "$d")"
  done
  echo "$PWD"
}

ROOT="${ODOO_ROOT:-$(find_root)}"

load_env() {   # import ODOO_* keys from .env files without overriding real env vars
  local dir f line key val
  for dir in "$HERE" "$PWD" "$ROOT" "$ROOT/.agents"; do
    f="$dir/.env"
    [ -f "$f" ] || continue
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line#export }"
      case "$line" in ODOO_*=*) ;; *) continue ;; esac
      key="${line%%=*}"; val="${line#*=}"
      val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
      if [ -z "${!key:-}" ]; then export "$key=$val"; fi
    done < "$f"
  done
}
load_env

ROOT="${ODOO_ROOT:-$ROOT}"
PY="${ODOO_PYTHON:-$ROOT/venv/bin/python3}"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
CONF="${ODOO_CONF:-$ROOT/odoo.conf}"
PORT="${ODOO_TEST_PORT:-8070}"
UNIT_PORT="${ODOO_UNIT_PORT:-8071}"
LOGDIR="${ODOO_TEST_LOGDIR:-/tmp}"
PIDFILE="$LOGDIR/odoo_test_server.pid"
SERVER_LOG="$LOGDIR/odoo_test_server.log"
DB=""

check_env() {
  [ -f "$ROOT/odoo-bin" ] || die "odoo-bin not found under '$ROOT' (set ODOO_ROOT)"
  [ -f "$CONF" ] || die "odoo.conf not found at '$CONF' (set ODOO_CONF)"
  [ -n "$PY" ] || die "no python interpreter found (set ODOO_PYTHON)"
  mkdir -p "$LOGDIR"
}

guard_db() {
  local lc
  lc="$(printf '%s' "$DB" | tr '[:upper:]' '[:lower:]')"
  case "$lc" in
    *test*) ;;
    *) die "database '$DB' does not contain 'test' - refusing to touch it" ;;
  esac
}

resolve_db() {   # $1 = optional module name, used for the default db name
  DB="${ODOO_TEST_DB:-}"
  [ -n "$DB" ] || DB="${1:+test_$1}"
  [ -n "$DB" ] || die "set ODOO_TEST_DB (the name must contain 'test')"
  guard_db
}

is_running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

summarize() {   # $1 = log file, $2 = odoo exit code
  local log="$1" rc="$2" errs
  echo "---- test summary ($log) ----"
  grep -E "failed, .*error\(s\) of|odoo\.tests\.stats" "$log" 2>/dev/null | tail -5
  errs="$(grep -E " (ERROR|CRITICAL) |^FAIL:|^ERROR:|Traceback" "$log" 2>/dev/null | head -40)"
  if [ -n "$errs" ]; then
    echo "---- error lines (first 40) ----"
    echo "$errs"
  fi
  if [ "$rc" -eq 0 ]; then
    if [ -n "$errs" ]; then
      echo "RESULT: PASS (exit code 0, but the log has ERROR lines - review them)"
    else
      echo "RESULT: PASS"
    fi
    return 0
  fi
  if [ -s "$log.out" ]; then
    echo "---- console output (last 20 lines) ----"
    tail -n 20 "$log.out"
  fi
  echo "RESULT: FAIL (odoo exit code $rc) - full log: $log"
  return 1
}

cmd_unit() {
  local module="${1:-}"
  [ -n "$module" ] || die "usage: odoo_test.sh unit <module> [test-tags]"
  check_env
  local tags="${2:-/$module}"
  local action="${ODOO_TEST_ACTION:--i}"
  resolve_db "$module"
  local log="$LOGDIR/odoo_unit_${module}.log"
  : > "$log"
  echo ">> unit tests: module=$module db=$DB tags=$tags action=$action port=$UNIT_PORT"
  "$PY" "$ROOT/odoo-bin" -c "$CONF" -d "$DB" "$action" "$module" \
      --test-tags "$tags" --stop-after-init --http-port "$UNIT_PORT" \
      --max-cron-threads=0 --log-level=test --logfile "$log" >"$log.out" 2>&1
  local rc=$?
  summarize "$log" "$rc"
}

cmd_serve() {
  check_env
  resolve_db "${1:-}"
  if is_running; then
    echo ">> test server already running (pid $(cat "$PIDFILE"))"
    return 0
  fi
  : > "$SERVER_LOG"
  echo ">> starting test server: db=$DB port=$PORT log=$SERVER_LOG"
  nohup "$PY" "$ROOT/odoo-bin" -c "$CONF" -d "$DB" --http-port "$PORT" \
      --max-cron-threads=0 --logfile "$SERVER_LOG" >"$SERVER_LOG.out" 2>&1 &
  echo $! > "$PIDFILE"
  if ! ODOO_URL="http://localhost:$PORT" "$PY" "$HERE/rpc_test.py" \
        --db "$DB" --wait "${ODOO_WAIT:-180}" --ping; then
    echo ">> server did not come up - last log lines:"
    tail -n 30 "$SERVER_LOG" 2>/dev/null
    tail -n 10 "$SERVER_LOG.out" 2>/dev/null
    cmd_stop
    return 1
  fi
}

cmd_stop() {
  if ! is_running; then
    rm -f "$PIDFILE"
    echo ">> no test server of ours is running"
    return 0
  fi
  local pid i
  pid="$(cat "$PIDFILE")"
  kill "$pid" 2>/dev/null
  for i in $(seq 1 30); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  rm -f "$PIDFILE"
  echo ">> test server stopped"
}

cmd_rpc() {
  check_env
  [ -n "$DB" ] || resolve_db ""
  ODOO_URL="http://localhost:$PORT" "$PY" "$HERE/rpc_test.py" --db "$DB" "$@"
}

cmd_all() {
  local module="${1:-}"
  [ -n "$module" ] || die "usage: odoo_test.sh all <module>"
  cmd_unit "$module" || { echo ">> unit tests failed - skipping the XML-RPC scenarios"; return 1; }
  cmd_serve "$module" || return 1
  local sc=()
  [ -d "$HERE/scenarios/$module" ] && sc=(--scenario-dir "$HERE/scenarios/$module")
  cmd_rpc --module "$module" ${sc[@]+"${sc[@]}"}
  local rc=$?
  cmd_stop
  return $rc
}

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

case "${1:-help}" in
  unit)  shift; cmd_unit "$@";  exit $? ;;
  serve) shift; cmd_serve "$@"; exit $? ;;
  stop)  cmd_stop;              exit $? ;;
  rpc)   shift; cmd_rpc "$@";   exit $? ;;
  all)   shift; cmd_all "$@";   exit $? ;;
  *)     usage ;;
esac
