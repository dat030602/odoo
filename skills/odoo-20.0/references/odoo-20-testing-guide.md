# Odoo 20 Testing Guide

Guide for testing Odoo 20: Python unit tests, HTTP tests, and JavaScript tests with Hoot.

## Table of Contents

- [Testing Overview](#testing-overview)
- [Python Tests (`TransactionCase`)](#python-tests-transactioncase)
- [Testing Security & Access Rights](#testing-security--access-rights)
- [Testing HTTP Endpoints (`HttpCase`)](#testing-http-endpoints-httpcase)
- [JavaScript Tests with `@odoo/hoot`](#javascript-tests-with-odoohoot)
- [Running Tests via CLI](#running-tests-via-cli)

---

## Testing Overview

| Test Type | Base Class / Framework | Purpose |
|-----------|------------------------|---------|
| **Python Unit Tests** | `TransactionCase` | Business logic, ORM, models, compute fields |
| **Python HTTP / Tour Tests** | `HttpCase` | Web controllers, HTTP endpoints, browser tours |
| **JavaScript Unit Tests** | **`@odoo/hoot`** | OWL 3 components, views, frontend widgets |

---

## Python Tests (`TransactionCase`)

Create test files in `tests/` directory:

File: `tests/test_task.py`

```python
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError

class TestProjectTask(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set up shared test fixtures
        cls.user = cls.env['res.users'].create({
            'name': "Test Worker",
            'login': "test_worker",
            'email': "worker@example.com",
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    def test_task_creation_and_state(self):
        task = self.env['project.task'].create({
            'name': "Build feature X",
            'user_id': self.user.id,
        })
        self.assertEqual(task.state, 'draft')

        task.action_start()
        self.assertEqual(task.state, 'in_progress')
```

---

## Testing Security & Access Rights

In Odoo 20, test permissions and restrictions using `.with_user()`:

```python
from odoo.exceptions import AccessError

def test_access_rights(self):
    # Create task as admin
    task = self.env['project.task'].create({
        'name': "Secret Management Task",
        'user_id': self.env.ref('base.user_admin').id,
    })

    # Switch environment to standard worker
    task_as_worker = task.with_user(self.user)

    # Verify worker cannot write or delete admin's task
    with self.assertRaises(AccessError):
        task_as_worker.write({'name': "Hacked Task"})

    with self.assertRaises(AccessError):
        task_as_worker.unlink()
```

---

## Testing HTTP Endpoints (`HttpCase`)

```python
from odoo.tests.common import HttpCase

class TestTaskController(HttpCase):

    def test_jsonrpc_endpoint(self):
        self.authenticate("test_worker", "test_worker")
        response = self.url_open(
            url="/api/v1/task/create",
            data="""{"params": {"title": "Automated API Task"}}""",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['result']['success'])
```

---

## JavaScript Tests with `@odoo/hoot`

In Odoo 20, frontend tests are authored using the **Hoot** testing framework.

File: `static/tests/my_component.test.js`

```javascript
import { expect, test } from "@odoo/hoot";
import { contains, defineActions, defineModels, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { Dropzone } from "@web/core/dropzone/dropzone";

test("Dropzone renders and reacts to drag events", async () => {
    await mountWithCleanup(Dropzone, {
        props: {
            extraClass: "custom-class",
            onDrop: () => {},
        },
    });

    expect(".o-Dropzone").toBeVisible();
    expect(".o-Dropzone").toHaveClass("custom-class");

    // Test dragging interaction
    await contains(".o-Dropzone").trigger("dragenter");
    expect(".o-Dropzone").toHaveClass("o-dragging-inside");

    await contains(".o-Dropzone").trigger("dragleave");
    expect(".o-Dropzone").not.toHaveClass("o-dragging-inside");
});
```

---

## Running Tests via CLI

```bash
# Run tests for a specific module
python3 odoo-bin -c odoo.conf -d test_db --test-enable --stop-after-init -u my_module

# Run tests with tag filter
python3 odoo-bin -c odoo.conf -d test_db --test-enable --stop-after-init --test-tags /my_module
```

