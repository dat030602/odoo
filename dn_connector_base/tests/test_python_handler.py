# -*- coding: utf-8 -*-
import json
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestPythonHandler(TransactionCase):
    """Unit tests for Python safe_eval handler, dynamic import, and context variables."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Framework = cls.env["connector.framework"]
        cls.Endpoint = cls.env["connector.inbound.endpoint"]
        cls.Message = cls.env["connector.inbound.message"]

        cls.framework = cls.Framework.create({
            "name": "Python Handler FW",
            "code": "py_handler_fw",
            "auth_type": "none",
        })

    def test_01_python_handler_basic_execution(self):
        """[AC-13] Test Python safe_eval handler execution and result assignment."""
        endpoint = self.Endpoint.create({
            "name": "Basic Python EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": """
result = {
    'status': 'success',
    'input_value': payload.get('value', 0) * 2,
}
""",
        })

        message = self.Message.create({
            "endpoint_id": endpoint.id,
            "payload": {"value": 21},
            "state": "queued",
        })

        message.process_message()

        self.assertEqual(message.state, "done")
        self.assertTrue(message.response_body)
        res_data = json.loads(message.response_body)
        self.assertEqual(res_data.get("status"), "success")
        self.assertEqual(res_data.get("input_value"), 42)

    def test_02_dynamic_import_libraries(self):
        """[AC-13] Test _dynamic_import and _import inside safe_eval without AST syntax error."""
        endpoint = self.Endpoint.create({
            "name": "Import Test EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": """
# Test dynamic import of libraries
sys_mod = _dynamic_import('sys')
math_mod = _import('math')

pi_val = math_mod.pi
py_ver = sys_mod.version_info[0]

result = {
    'pi_floor': math_mod.floor(pi_val),
    'python_major': py_ver,
}
""",
        })

        message = self.Message.create({
            "endpoint_id": endpoint.id,
            "payload": {},
            "state": "queued",
        })

        message.process_message()

        self.assertEqual(message.state, "done")
        res_data = json.loads(message.response_body)
        self.assertEqual(res_data.get("pi_floor"), 3)
        self.assertEqual(res_data.get("python_major"), 3)

    def test_03_python_handler_context_variables(self):
        """[AC-13] Test availability of all standard context variables in safe_eval."""
        endpoint = self.Endpoint.create({
            "name": "Context Test EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": """
assert payload is not None
assert headers is not None
assert message is not None
assert endpoint is not None
assert env is not None
assert datetime is not None
assert json is not None
assert re is not None
assert math is not None
assert callable(_import)
assert callable(_dynamic_import)
assert callable(log)

log("Executing test log inside handler")

result = {'context_valid': True}
""",
        })

        message = self.Message.create({
            "endpoint_id": endpoint.id,
            "payload": {"test_ctx": True},
            "headers": {"X-Custom": "header-value"},
            "state": "queued",
        })

        message.process_message()

        self.assertEqual(message.state, "done")
        res_data = json.loads(message.response_body)
        self.assertTrue(res_data.get("context_valid"))

    def test_04_python_handler_orm_operations(self):
        """[AC-13] Test Python handler executes ORM operations through env."""
        endpoint = self.Endpoint.create({
            "name": "ORM Partner Creator EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": """
partner = env['res.partner'].create({
    'name': payload.get('partner_name'),
    'email': payload.get('email'),
})
result = {'partner_id': partner.id}
""",
        })

        message = self.Message.create({
            "endpoint_id": endpoint.id,
            "payload": {
                "partner_name": "Inbound Webhook Partner",
                "email": "inbound@example.com",
            },
            "state": "queued",
        })

        message.process_message()

        self.assertEqual(message.state, "done")
        res_data = json.loads(message.response_body)
        partner_id = res_data.get("partner_id")
        self.assertTrue(partner_id)
        partner = self.env["res.partner"].browse(partner_id)
        self.assertEqual(partner.name, "Inbound Webhook Partner")
        self.assertEqual(partner.email, "inbound@example.com")

    def test_05_python_handler_exception_handling(self):
        """[AC-13] Test unhandled exception in Python code is caught and recorded."""
        endpoint = self.Endpoint.create({
            "name": "Crash EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": """
1 / 0
""",
        })

        message = self.Message.create({
            "endpoint_id": endpoint.id,
            "payload": {},
            "state": "queued",
        })

        message.process_message()

        self.assertEqual(message.state, "failed")
        self.assertIn("ZeroDivisionError", message.error_type or "")
        self.assertTrue(message.error_details)

    def test_06_code_mixin_sanitized_eval_context(self):
        """[AC-13] Test connector.code.mixin provides sanitized safe_eval context without crash (DEF-03)."""
        # Testing connector.code.mixin directly if present
        if "connector.code.mixin" in self.env:
            mixin_inst = self.env["connector.code.mixin"]
            if hasattr(mixin_inst, "_get_eval_context"):
                ctx = mixin_inst._get_eval_context()
                self.assertIn("_dynamic_import", ctx)
                self.assertIn("_import", ctx)
                self.assertTrue(callable(ctx["_dynamic_import"]))
