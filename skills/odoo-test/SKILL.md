---
name: odoo-test
description: Run Odoo unit tests (TransactionCase/HttpCase) and end-to-end XML-RPC scenarios against a throw-away test database, and read the resulting logs. Use whenever Odoo code must be verified, a test must be written or run, or a log must be inspected.
---

# odoo-test

Everything needed to verify Odoo code lives in this folder. Stdlib Python + bash, no installs.

```
odoo-test/
  SKILL.md            this file
  odoo_test.sh        unit tests, background test server, scenario runner
  rpc_test.py         XML-RPC client + assertions (run directly or from scenarios)
  scenarios/          XML-RPC scenarios; put module flows in scenarios/<module>/NN_name.py
  .env.example        settings template
```

## Quick start

```bash
cd odoo-test
cp .env.example .env            # set ODOO_TEST_DB (name must contain "test")
./odoo_test.sh all my_module    # unit tests -> test server -> XML-RPC scenarios -> stop
```

Individual steps:

| Goal | Command |
|---|---|
| Unit tests, first run (installs module on a fresh test DB) | `./odoo_test.sh unit my_module` |
| Unit tests after code changes | `ODOO_TEST_ACTION=-u ./odoo_test.sh unit my_module` |
| Only some tests | `./odoo_test.sh unit my_module '/my_module:TestSaleFlow.test_confirm'` |
| Start / stop the test server | `./odoo_test.sh serve my_module` / `./odoo_test.sh stop` |
| Smoke test (login + module installed) | `./odoo_test.sh rpc --module my_module` |
| Run scenario files | `./odoo_test.sh rpc --scenario-dir scenarios/my_module` |
| Ad-hoc read-only look at data | `./odoo_test.sh rpc --call res.partner search_read --args '[[]]' --kwargs '{"limit":3}'` |

`rpc_test.py` also works standalone: `python rpc_test.py --help`.

Exit code is 0 only when everything passed. Output ends with `RESULT: PASS` or `RESULT: FAIL`.

## Reading logs

| Log | Written by |
|---|---|
| `/tmp/odoo_unit_<module>.log` | `odoo_test.sh unit` |
| `/tmp/odoo_test_server.log` | `odoo_test.sh serve` |
| path in `logfile =` of `odoo.conf` | your normal debug instance (set it, otherwise the VS Code terminal output is not readable by agents) |

Read with `tail -n 200 <log>` and `grep -nE " (ERROR|CRITICAL|WARNING) |Traceback" <log>`.
Search upward from the first `Traceback` or `FAIL:` line; the root cause is usually the last frame inside the module under test.

## Writing unit tests (inside the module)

```python
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMyFeature(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})

    def test_happy_path(self):
        ...

    def test_rejects_bad_input(self):
        with self.assertRaises(ValidationError):
            ...

    def test_restricted_user(self):
        user = self.env["res.users"].create({...})
        with self.assertRaises(AccessError):
            self.partner.with_user(user).unlink()
```

* Files: `<module>/tests/__init__.py` (imports each test file) and `tests/test_*.py`.
* `TransactionCase` for model logic, `HttpCase` for controllers/tours.
* One behaviour per test; assert results, not just "no error".
* Verify the import path of helpers against the installed Odoo source - the version may differ from any reference skill.

## Multi-User Access Testing (mandatory)

**Every feature that touches security-sensitive data, creates accounting entries, or exposes menus/actions MUST be tested with multiple users, not just admin.**

### Why this matters

A common failure mode: a warehouse user clicks a button that opens a Journal Entry view — Odoo raises `window action not found` or `AccessError` because the action requires `account.group_account_user` and the button has no `groups=` guard. These bugs are invisible until a real user hits them.

### Standard user matrix

For every test class, define at least these users in `setUpClass`:

```python
@classmethod
def setUpClass(cls):
    super().setUpClass()

    # User with the primary operational role (e.g. warehouse)
    cls.user_warehouse = cls.env["res.users"].create({
        "name": "Test Warehouse User",
        "login": "test_warehouse",
        "groups_id": [(6, 0, [
            cls.env.ref("stock.group_stock_user").id,
        ])],
    })

    # User with the secondary role that sees related documents (e.g. accountant)
    cls.user_accountant = cls.env["res.users"].create({
        "name": "Test Accountant",
        "login": "test_accountant",
        "groups_id": [(6, 0, [
            cls.env.ref("account.group_account_user").id,
        ])],
    })

    # Manager / full-access user (optional, for positive-path baseline)
    cls.user_manager = cls.env["res.users"].create({
        "name": "Test Manager",
        "login": "test_manager",
        "groups_id": [(6, 0, [
            cls.env.ref("stock.group_stock_manager").id,
            cls.env.ref("account.group_account_manager").id,
        ])],
    })
```

### What to test per user

For each feature, write separate test methods per role:

```python
def test_warehouse_user_can_validate_picking(self):
    """Warehouse user can confirm and validate a picking."""
    picking = self._create_picking()
    picking.with_user(self.user_warehouse).button_validate()
    self.assertEqual(picking.state, "done")

def test_warehouse_user_cannot_open_journal_entry(self):
    """Warehouse user must NOT be able to open the linked JE view — no account group."""
    move = self._create_stock_move_with_svl()
    with self.assertRaises(AccessError):
        move.stock_valuation_layer_ids.account_move_id.with_user(
            self.user_warehouse
        ).check_access("read")

def test_accountant_can_read_journal_entry(self):
    """Accountant user CAN read the JE created by stock valuation."""
    move = self._create_stock_move_with_svl()
    je = move.stock_valuation_layer_ids.account_move_id
    # Must not raise
    je.with_user(self.user_accountant).read(["name", "state"])
```

### Menu and window action reachability

**Always test that every menu item and button the feature adds is reachable by the intended user role.** The most frequent production bug is a menu/button with no `groups=` guard pointing to an action that the user cannot load.

```python
def test_svl_menu_reachable_by_warehouse_user(self):
    """
    The 'Stock Valuation' menu must be visible and its action loadable
    for warehouse users. If the action requires account group, the menu
    itself must carry groups="stock.group_stock_manager" or similar guard.
    """
    action_xmlid = "stock_account.action_stock_account_valuation"
    action = self.env.ref(action_xmlid).with_user(self.user_warehouse)
    try:
        # read() triggers access check on ir.actions.act_window
        action.read(["name", "res_model"])
    except AccessError:
        self.fail(
            f"Window action {action_xmlid!r} is not accessible to warehouse user. "
            "Add groups= to the menu item or the action, or grant the right group."
        )

def test_button_open_je_has_group_guard_or_raises_gracefully(self):
    """
    Any button that opens a Journal Entry view must either:
    (a) carry groups="account.group_account_user" so it is hidden, or
    (b) raise UserError with a friendly message — never an unhandled AccessError
        that shows as 'window action not found'.
    """
    move = self._create_stock_move_with_svl()
    # Simulate clicking the button as a warehouse-only user
    with self.assertRaises((AccessError, UserError)):
        move.with_user(self.user_warehouse).action_open_journal_entry()
```

### Checklist before marking a test suite complete

- [ ] Admin / manager positive path tested
- [ ] Primary operational user (e.g. warehouse, sales) tested for every action they can trigger
- [ ] Cross-domain access (e.g. warehouse → accounting) tested and **expected to fail with AccessError or be hidden via `groups=`**
- [ ] Every new menu item: reachability tested with the target user role
- [ ] Every button that opens a window action: tested that it either works or is hidden (`groups=`) for users without the required access
- [ ] No test only tests `self.env` (admin); at least one `.with_user(non_admin)` per feature

## Writing XML-RPC scenarios

A scenario is a file with `run(t)`; see `scenarios/_example_partner.py`.

```python
def run(t):
    rpc = t.rpc                                   # admin client
    order_id = rpc.create("sale.order", {...})    # tracked, auto-deleted afterwards
    rpc.call("sale.order", "action_confirm", [order_id])
    t.eq("state", rpc.read("sale.order", order_id, ["state"])[0]["state"], "sale")
    t.raises("cannot delete confirmed", lambda: rpc.unlink("sale.order", order_id), contains="UserError")
    user = rpc.as_user("limited_login", "password")
    t.raises("no access", lambda: user.read("sale.order", order_id, ["name"]), contains="AccessError")
```

Helpers on `t.rpc`: `call, search, search_read, search_count, read, create, write, unlink, module_state, as_user, cleanup`.
Assertions on `t`: `check, eq, close, raises, step, info`.
Files starting with `_` are skipped by `--scenario-dir`; run them explicitly with `--scenario`.
Number files (`10_`, `20_`) when order matters.

## Safety rules (enforced by the scripts)

* The database name must contain `test`; the URL must be local. Overrides exist (`--allow-any-db`, `--allow-remote`) and must not be used by agents.
* `odoo_test.sh stop` kills only the pid it started itself.
* Scenarios must clean up through tracked `create()`; never run them on a database with real data.
* Never run `dropdb`, destructive SQL or edit `odoo.conf` / `.env` from an agent.

## Notes on the API

The scripts use only the `common` and `object` XML-RPC services. Per Odoo's documentation the `db` service was removed in Odoo 20, and `common`/`object` are deprecated and scheduled for removal in Odoo 22 in favour of the JSON-2 API (`POST /json/2/<model>/<method>` with an API key). If a future Odoo drops XML-RPC, only `OdooRPC` in `rpc_test.py` needs to change; scenarios keep working.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `database ... does not contain 'test'` | rename `ODOO_TEST_DB` |
| `cannot reach Odoo` | server not started or still booting: `./odoo_test.sh serve`, or add `--wait 120` |
| `authentication failed` | wrong `ODOO_USER`/`ODOO_PASSWORD` for the test DB |
| unit run finds 0 tests | module not installed on that DB yet (use `-i` once), missing `tests/__init__.py`, or wrong tag |
| `Address already in use` | another Odoo is using the port: change `ODOO_UNIT_PORT` / `ODOO_TEST_PORT` |
| new field "does not exist" | module not upgraded: rerun with `ODOO_TEST_ACTION=-u` |