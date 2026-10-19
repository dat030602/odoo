import logging
import socket
import time
import xmlrpc.client

_logger = logging.getLogger(__name__)

READ_METHODS = {
    'search', 'search_read', 'read', 'search_count',
    'fields_get', 'read_group', 'name_get',
}


class OdooRPCError(Exception):
    """Raised for any authentication / execute_kw failure."""
    pass


class _TimeoutMixin:
    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


class TimeoutTransport(_TimeoutMixin, xmlrpc.client.Transport):
    def __init__(self, timeout=60):
        super().__init__()
        self._timeout = timeout


class TimeoutSafeTransport(_TimeoutMixin, xmlrpc.client.SafeTransport):
    def __init__(self, timeout=60):
        super().__init__()
        self._timeout = timeout


class OdooRPC:

    def __init__(self, url, db, username, password, timeout=60, read_only=False):
        self.url = (url or '').rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.timeout = timeout or 60
        self.read_only = read_only
        self._uid = None
        self._object_proxy = None

    # ---------- low level ----------

    def _proxy(self, path):
        cls = TimeoutSafeTransport if self.url.startswith('https') else TimeoutTransport
        return xmlrpc.client.ServerProxy(self.url + path, transport=cls(self.timeout))

    def _common_proxy(self):
        return self._proxy('/xmlrpc/2/common')

    def _object(self):
        if self._object_proxy is None:
            self._object_proxy = self._proxy('/xmlrpc/2/object')
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

    def execute(self, model, method, *args, _retry=0, **kwargs):
        if self.read_only and method not in READ_METHODS:
            raise OdooRPCError('Blocked in test mode: %s.%s' % (model, method))

        uid = self.authenticate()
        attempt = 0
        max_attempts = 1 + (_retry if method in READ_METHODS else 0)

        while attempt < max_attempts:
            attempt += 1
            try:
                return self._object().execute_kw(
                    self.db, uid, self.password, model, method, list(args), kwargs
                )
            except (socket.timeout, TimeoutError) as e:
                if attempt < max_attempts:
                    time.sleep(attempt)
                    continue
                raise OdooRPCError("Timeout after %s seconds calling %s.%s: %s" % (self.timeout, model, method, e))
            except (ConnectionError, xmlrpc.client.ProtocolError) as e:
                if attempt < max_attempts:
                    time.sleep(attempt)
                    continue
                raise OdooRPCError("Connection error calling %s.%s: %s" % (model, method, e))
            except xmlrpc.client.Fault as e:
                raise OdooRPCError("%s.%s error: %s" % (model, method, e.faultString))
            except Exception as e:
                raise OdooRPCError("%s.%s error: %s" % (model, method, e))

    # ---------- convenience wrappers ----------

    def search_read(self, model, domain, fields=None, limit=0, order=None):
        kwargs = {'fields': fields or []}
        if limit:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
        return self.execute(model, 'search_read', domain, _retry=2, **kwargs)

    def search(self, model, domain, limit=0):
        kwargs = {}
        if limit:
            kwargs['limit'] = limit
        return self.execute(model, 'search', domain, _retry=2, **kwargs)

    def read(self, model, ids, fields=None):
        return self.execute(model, 'read', ids, fields or [], _retry=2)

    def create(self, model, values):
        return self.execute(model, 'create', values)

    def write(self, model, ids, values):
        return self.execute(model, 'write', ids, values)

    def unlink(self, model, ids):
        return self.execute(model, 'unlink', ids)
