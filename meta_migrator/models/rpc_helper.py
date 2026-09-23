# ============================================================
# RPC HELPER
# Thin XML-RPC client wrapper for talking to ONE remote Odoo
# instance (either the "source" or the "target" link).
# Not an Odoo model - plain python, imported by connection.py
# and migration_job.py.
# ============================================================

import logging
import xmlrpc.client

_logger = logging.getLogger(__name__)


class OdooRPCError(Exception):
    """Raised for any authentication / execute_kw failure."""
    pass


class OdooRPC:

    def __init__(self, url, db, username, password):
        self.url = (url or '').rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self._uid = None
        self._object_proxy = None

    # ---------- low level ----------

    def _common_proxy(self):
        return xmlrpc.client.ServerProxy('%s/xmlrpc/2/common' % self.url)

    def _object(self):
        if self._object_proxy is None:
            self._object_proxy = xmlrpc.client.ServerProxy('%s/xmlrpc/2/object' % self.url)
        return self._object_proxy

    def authenticate(self):
        if self._uid is None:
            try:
                common = self._common_proxy()
                uid = common.authenticate(self.db, self.username, self.password, {})
            except Exception as e:
                raise OdooRPCError(
                    "Could not connect to %s (%s)" % (self.url, e)
                )
            if not uid:
                raise OdooRPCError(
                    "Login failed for %s (db=%s, user=%s). "
                    "Check the username, password, and database."
                    % (self.url, self.db, self.username)
                )
            self._uid = uid
        return self._uid

    def execute(self, model, method, *args, **kwargs):
        uid = self.authenticate()
        try:
            return self._object().execute_kw(
                self.db, uid, self.password, model, method, list(args), kwargs
            )
        except xmlrpc.client.Fault as e:
            raise OdooRPCError("%s.%s lỗi: %s" % (model, method, e.faultString))
        except Exception as e:
            raise OdooRPCError("%s.%s lỗi: %s" % (model, method, e))

    # ---------- convenience wrappers ----------

    def search_read(self, model, domain, fields=None, limit=0, order=None):
        kwargs = {'fields': fields or []}
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
        return self.execute(model, 'search_read', domain, **kwargs)

    def search(self, model, domain, limit=0):
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        return self.execute(model, 'search', domain, **kwargs)

    def read(self, model, ids, fields=None):
        return self.execute(model, 'read', ids, fields or [])

    def create(self, model, values):
        return self.execute(model, 'create', values)

    def write(self, model, ids, values):
        return self.execute(model, 'write', ids, values)
