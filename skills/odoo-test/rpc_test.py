#!/usr/bin/env python3
"""rpc_test.py - XML-RPC test helper for Odoo (Python standard library only).

Run it from anywhere; it reads ODOO_* settings from the environment or from a
.env file (looked up in this folder, the current dir and a few parent dirs).

  python rpc_test.py                                  # smoke test: connect + login
  python rpc_test.py --module my_module               # ...and check the module is installed
  python rpc_test.py --scenario scenarios/my_module/10_flow.py
  python rpc_test.py --scenario-dir scenarios/my_module
  python rpc_test.py --call res.partner search_read --args '[[]]' --kwargs '{"limit": 3}'
  python rpc_test.py --wait 120 --ping                # wait until the server answers

Settings (env or .env):
  ODOO_URL        default http://localhost:8070
  ODOO_TEST_DB    (or ODOO_DB) database name - MUST contain "test"
  ODOO_USER       default admin        (or ODOO_LOGIN)
  ODOO_PASSWORD   default admin        (or ODOO_API_KEY)

Safety: refuses non-local URLs and database names without "test" unless you
pass --allow-remote / --allow-any-db. Only the "common" and "object" services
are used (the "db" service was removed in Odoo 20).

Exit code: 0 = everything passed, 1 = a check failed, 2 = bad usage/config.
"""
import argparse
import importlib.util
import json
import os
import socket
import sys
import time
import traceback
import xmlrpc.client
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
FAULT_KINDS = {1: "ApplicationError", 2: "UserError", 3: "AccessError", 4: "AccessDenied"}


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #
def die(message, code=2):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _parse_env_line(line):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    if line.startswith("export "):
        line = line[7:].lstrip()
    key, _, value = line.partition("=")
    key, value = key.strip(), value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()
    return key, value


def load_env():
    """Load ODOO_* keys from .env files. Real environment variables always win."""
    dirs = []
    if os.environ.get("ODOO_ROOT"):
        dirs.append(Path(os.environ["ODOO_ROOT"]))
    dirs += [HERE, Path.cwd()] + list(HERE.parents)[:4]
    seen = set()
    for directory in dirs:
        path = directory / ".env"
        try:
            key = str(path.resolve())
            if key in seen or not path.is_file():
                continue
            seen.add(key)
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            parsed = _parse_env_line(line)
            if parsed and parsed[0].startswith("ODOO_"):
                os.environ.setdefault(*parsed)


def first_env(*names, default=None):
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


# --------------------------------------------------------------------------- #
# RPC client
# --------------------------------------------------------------------------- #
class RPCError(Exception):
    """An error answered by the Odoo server (a XML-RPC Fault)."""

    def __init__(self, message, detail="", code=None):
        super().__init__(message)
        self.detail = detail
        self.code = code

    @property
    def kind(self):
        return FAULT_KINDS.get(self.code, "RPCError")


class ConnectionProblem(RPCError):
    """The server could not be reached / answered with an HTTP error."""


class OdooRPC:
    def __init__(self, url, db, login, secret, created=None):
        self.url = url.rstrip("/")
        self.db, self.login, self.secret = db, login, secret
        self.uid = None
        # (model, id) of every record created through create(); cleaned up in reverse order
        self.created = created if created is not None else []
        self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self._object = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    # -- plumbing ----------------------------------------------------------- #
    @staticmethod
    def _wrap(fn, *args):
        try:
            return fn(*args)
        except xmlrpc.client.Fault as fault:
            text = str(fault.faultString or "")
            lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
            raise RPCError(lines[-1] if lines else f"fault {fault.faultCode}",
                           detail=text, code=fault.faultCode) from None
        except (OSError, xmlrpc.client.ProtocolError) as exc:
            raise ConnectionProblem(f"cannot reach Odoo: {exc}") from None

    def version(self):
        return self._wrap(self._common.version)

    def authenticate(self):
        uid = self._wrap(self._common.authenticate, self.db, self.login, self.secret, {})
        if not uid:
            raise RPCError(f"authentication failed for '{self.login}' on database '{self.db}'")
        self.uid = uid
        return uid

    def call(self, model, method, *args, **kwargs):
        """execute_kw(model, method, *args, **kwargs) - authenticates lazily."""
        if self.uid is None:
            self.authenticate()
        return self._wrap(self._object.execute_kw, self.db, self.uid, self.secret,
                          model, method, list(args), kwargs)

    # -- ORM helpers -------------------------------------------------------- #
    def search(self, model, domain=None, **kw):
        return self.call(model, "search", domain or [], **kw)

    def search_read(self, model, domain=None, fields=None, **kw):
        if fields:
            kw["fields"] = fields
        return self.call(model, "search_read", domain or [], **kw)

    def search_count(self, model, domain=None):
        return self.call(model, "search_count", domain or [])

    def read(self, model, ids, fields=None):
        ids = [ids] if isinstance(ids, int) else list(ids)
        return self.call(model, "read", ids, **({"fields": fields} if fields else {}))

    def create(self, model, vals, track=True):
        """Create a record; it is deleted again by cleanup() unless track=False."""
        new_id = self.call(model, "create", vals)
        ids = new_id if isinstance(new_id, list) else [new_id]
        if track:
            self.created.extend((model, rid) for rid in ids)
        return new_id

    def write(self, model, ids, vals):
        ids = [ids] if isinstance(ids, int) else list(ids)
        return self.call(model, "write", ids, vals)

    def unlink(self, model, ids):
        ids = [ids] if isinstance(ids, int) else list(ids)
        return self.call(model, "unlink", ids)

    def module_state(self, name):
        rows = self.search_read("ir.module.module", [("name", "=", name)], ["state"], limit=1)
        return rows[0]["state"] if rows else None

    def as_user(self, login, secret):
        """A second client logged in as another user (to test access rights).
        Shares the created-records list, so the admin client cleans up for both."""
        other = OdooRPC(self.url, self.db, login, secret, created=self.created)
        other.authenticate()
        return other

    def cleanup(self):
        """Delete tracked records, newest first. Returns a list of failure messages."""
        failures = []
        while self.created:
            model, rid = self.created.pop()
            try:
                self.call(model, "unlink", [rid])
            except RPCError as exc:
                failures.append(f"{model}({rid}): {exc}")
        return failures


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
class T:
    """Passed to scenarios as `t`. Use t.rpc for calls and t.check/eq/close/raises for assertions."""

    def __init__(self, rpc, verbose=False):
        self.rpc = rpc
        self.verbose = verbose
        self.passed = 0
        self.failed = 0

    def step(self, title):
        print(f"\n== {title}")

    def info(self, message):
        print(f"  INFO  {message}")

    def check(self, name, ok, detail=""):
        if ok:
            self.passed += 1
            print(f"  PASS  {name}")
        else:
            self.failed += 1
            print(f"  FAIL  {name}" + (f" -> {detail}" if detail else ""))
        return bool(ok)

    def eq(self, name, actual, expected):
        return self.check(name, actual == expected, f"expected {expected!r}, got {actual!r}")

    def close(self, name, actual, expected, tol=0.01):
        ok = actual is not None and abs(actual - expected) <= tol
        return self.check(name, ok, f"expected {expected!r} +/- {tol}, got {actual!r}")

    def raises(self, name, fn, contains=None):
        """Expect fn() to fail with a server error. `contains` is matched (case-insensitive)
        against the error kind (AccessError, UserError, ...) and the message."""
        try:
            fn()
        except ConnectionProblem:
            raise
        except RPCError as exc:
            haystack = f"{exc.kind} {exc}".lower()
            if contains is None or contains.lower() in haystack:
                return self.check(name, True)
            return self.check(name, False, f"error did not contain {contains!r}: {exc.kind}: {exc}")
        return self.check(name, False, "expected a server error, but the call succeeded")


def run_scenario(path, rpc, verbose=False):
    """Load a scenario file and call its run(t). Records are always cleaned up afterwards."""
    t = T(rpc, verbose)
    print(f"\n### scenario: {path}")
    try:
        spec = importlib.util.spec_from_file_location(f"scenario_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "run"):
            raise RuntimeError("scenario must define run(t)")
        module.run(t)
    except ConnectionProblem as exc:
        t.check("server connection", False, str(exc))
    except RPCError as exc:
        t.check("unexpected server error", False, f"{exc.kind}: {exc}")
        if verbose:
            print(exc.detail)
    except Exception:  # noqa: BLE001 - a crashing scenario is a failed scenario
        tb = traceback.format_exc().strip()
        t.check("scenario crashed", False, tb if verbose else tb.splitlines()[-1])
    finally:
        for problem in rpc.cleanup():
            print(f"  WARN  cleanup failed: {problem}")
    return t


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def wait_for_server(rpc, seconds):
    deadline = time.time() + seconds
    announced = False
    while True:
        try:
            rpc.version()
            return True
        except ConnectionProblem:
            if time.time() >= deadline:
                return False
            if not announced:
                print(f"waiting up to {seconds}s for Odoo at {rpc.url} ...")
                announced = True
            time.sleep(2)


def resolve_path(raw):
    path = Path(raw)
    if path.exists():
        return path
    alt = HERE / raw
    return alt if alt.exists() else path


def collect_scenarios(args):
    files = [resolve_path(p) for p in args.scenario]
    for directory in args.scenario_dir:
        folder = resolve_path(directory)
        if not folder.is_dir():
            die(f"scenario directory not found: {directory}")
        files += sorted(p for p in folder.glob("*.py") if not p.name.startswith("_"))
    return files


def main(argv=None):
    load_env()
    ap = argparse.ArgumentParser(description="Odoo XML-RPC test helper")
    ap.add_argument("--url")
    ap.add_argument("--db")
    ap.add_argument("--user")
    ap.add_argument("--password")
    ap.add_argument("--module", help="check that this module is installed")
    ap.add_argument("--scenario", action="append", default=[], help="scenario file (repeatable)")
    ap.add_argument("--scenario-dir", action="append", default=[],
                    help="run every *.py in the folder, sorted; files starting with _ are skipped")
    ap.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                    help="wait for the server to answer before starting")
    ap.add_argument("--ping", action="store_true", help="only wait for/verify the server, then exit")
    ap.add_argument("--call", nargs=2, metavar=("MODEL", "METHOD"), help="run one ad-hoc call")
    ap.add_argument("--args", default="[]", help="JSON list of positional args for --call")
    ap.add_argument("--kwargs", default="{}", help="JSON object of keyword args for --call")
    ap.add_argument("--allow-any-db", action="store_true", help="allow a db name without 'test'")
    ap.add_argument("--allow-remote", action="store_true", help="allow a non-local URL")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    url = args.url or first_env("ODOO_URL", default="http://localhost:8070")
    db = args.db or first_env("ODOO_TEST_DB", "ODOO_DB")
    login = args.user or first_env("ODOO_USER", "ODOO_LOGIN", default="admin")
    secret = args.password or first_env("ODOO_PASSWORD", "ODOO_API_KEY", default="admin")
    allow_any_db = args.allow_any_db or os.environ.get("ODOO_ALLOW_ANY_DB") == "1"
    allow_remote = args.allow_remote or os.environ.get("ODOO_ALLOW_REMOTE") == "1"

    if not db:
        die("no database: set ODOO_TEST_DB (or pass --db). The name must contain 'test'.")
    if not allow_any_db and "test" not in db.lower():
        die(f"database '{db}' does not contain 'test' - refusing to run (override: --allow-any-db)")
    host = urlparse(url).hostname or ""
    if not allow_remote and host not in LOCAL_HOSTS:
        die(f"URL '{url}' is not local - refusing to run (override: --allow-remote)")

    socket.setdefaulttimeout(int(os.environ.get("ODOO_RPC_TIMEOUT", "300")))
    rpc = OdooRPC(url, db, login, secret)

    # --- wait / ping ------------------------------------------------------- #
    if args.wait or args.ping:
        if not wait_for_server(rpc, args.wait or 60):
            print(f"FAIL  Odoo did not answer at {url}")
            return 1
    if args.ping:
        info = rpc.version()
        print(f"OK  Odoo {info.get('server_version')} is answering at {url}")
        return 0

    # --- ad-hoc call ------------------------------------------------------- #
    if args.call:
        try:
            pos, kw = json.loads(args.args), json.loads(args.kwargs)
        except json.JSONDecodeError as exc:
            die(f"--args/--kwargs must be valid JSON: {exc}")
        if not isinstance(pos, list) or not isinstance(kw, dict):
            die("--args must be a JSON list and --kwargs a JSON object")
        try:
            result = rpc.call(args.call[0], args.call[1], *pos, **kw)
        except RPCError as exc:
            print(f"{exc.kind}: {exc}", file=sys.stderr)
            if args.verbose:
                print(exc.detail, file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0

    # --- smoke test -------------------------------------------------------- #
    smoke = T(rpc, args.verbose)
    smoke.step(f"smoke test  url={url}  db={db}  user={login}")
    try:
        info = rpc.version()
        smoke.check("server reachable", True)
        smoke.info(f"server_version={info.get('server_version')}")
        smoke.check("authenticated", bool(rpc.authenticate()))
        smoke.info(f"uid={rpc.uid}")
        if args.module:
            state = rpc.module_state(args.module)
            smoke.check(f"module '{args.module}' installed", state == "installed", f"state={state}")
    except RPCError as exc:
        smoke.check("smoke test", False, f"{exc.kind}: {exc}")

    totals = [smoke.passed, smoke.failed]
    if smoke.failed:
        return finish(totals)

    # --- scenarios --------------------------------------------------------- #
    scenarios = collect_scenarios(args)
    for path in scenarios:
        if not path.is_file():
            print(f"\n### scenario: {path}\n  FAIL  file not found")
            totals[1] += 1
            continue
        result = run_scenario(path, rpc, args.verbose)
        totals[0] += result.passed
        totals[1] += result.failed
    return finish(totals)


def finish(totals):
    passed, failed = totals
    print()
    if failed:
        print(f"RESULT: FAIL ({failed} failed, {passed} passed)")
        return 1
    print(f"RESULT: PASS ({passed} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
