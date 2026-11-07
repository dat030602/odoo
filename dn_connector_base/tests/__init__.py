# -*- coding: utf-8 -*-
from contextlib import ExitStack, contextmanager
import odoo.tests.common
from odoo.exceptions import AccessError

_orig_assertRaises = odoo.tests.common.BaseCase._assertRaises

@contextmanager
def _safe_assertRaises(self, exception, *, msg=None):
    """Test helper allowing tuple of exception types in self.assertRaises."""
    if isinstance(exception, tuple):
        has_access = any(isinstance(e, type) and issubclass(e, AccessError) for e in exception)
    else:
        has_access = isinstance(exception, type) and issubclass(exception, AccessError)
    with ExitStack() as init:
        if getattr(self, "env", None):
            init.enter_context(self.env.cr.savepoint())
            if has_access:
                self.env.cr.clear()
        with ExitStack() as inner:
            cm = inner.enter_context(super(odoo.tests.common.BaseCase, self).assertRaises(exception, msg=msg))
            inner.push(init.pop_all())
            yield cm

odoo.tests.common.BaseCase._assertRaises = _safe_assertRaises

from . import test_inbound_framework
from . import test_inbound_endpoint
from . import test_inbound_receiver
from . import test_inbound_processor
from . import test_python_handler
from . import test_odoo19_compliance
from . import test_doc_link
