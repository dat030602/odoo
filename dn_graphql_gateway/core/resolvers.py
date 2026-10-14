import ast
import base64
import json
import logging
from datetime import datetime, timedelta

import odoo
from odoo.exceptions import AccessError, UserError, ValidationError
from graphql import GraphQLError

from .errors import ForbiddenResourceError, UploadNotAllowedError

_logger = logging.getLogger(__name__)


def decode_cursor(cursor_str):
    if not cursor_str:
        return 0
    try:
        raw = base64.b64decode(cursor_str).decode('utf-8')
        return int(raw)
    except Exception:
        return 0


def encode_cursor(offset):
    return base64.b64encode(str(offset).encode('utf-8')).decode('utf-8')


def parse_safe_domain(domain_val, deny_checker, model_name):
    """
    Safely parses domain argument and verifies no denied field is accessed.
    """
    if not domain_val:
        return []
    if isinstance(domain_val, list):
        parsed = domain_val
    elif isinstance(domain_val, str):
        domain_str = domain_val.strip()
        if not domain_str:
            return []
        try:
            parsed = json.loads(domain_str)
        except Exception:
            try:
                parsed = ast.literal_eval(domain_str)
            except Exception as e:
                raise GraphQLError(f"Invalid search domain syntax: {e}", extensions={'code': 'BAD_USER_INPUT'})
    else:
        return []

    # Guard: check domain tokens for denied fields
    if deny_checker and isinstance(parsed, (list, tuple)):
        for item in parsed:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                field_expr = str(item[0])
                # Check direct field or dot-navigated field
                field_parts = field_expr.split('.')
                direct_field = field_parts[0]
                denied, reason = deny_checker.is_denied(model_name, field=direct_field, operation='read')
                if denied:
                    raise ForbiddenResourceError(f"Field '{direct_field}' in domain is restricted: {reason}")

    return parsed


def sanitize_odoo_value(val, field_type):
    """
    Converts Odoo values to GraphQL standard representations:
    - Booleans preserve True / False
    - Non-booleans convert False to None (null in GraphQL)
    - Datetime/Date objects convert to ISO strings
    """
    if field_type == 'boolean':
        return bool(val)
    if val is False or val is None:
        return None
    if hasattr(val, '_name'):
        if not val:
            return None
        return val
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return val


def make_field_resolver(field_name, field_type, model_name):
    def field_resolver(record, info, **args):
        if not record:
            return None
        deny_checker = info.context.get('deny_checker')
        if deny_checker:
            denied, reason = deny_checker.is_denied(model_name, field=field_name, operation='read')
            if denied:
                raise ForbiddenResourceError(f"Access to field '{field_name}' on model '{model_name}' is forbidden: {reason}")

        try:
            val = getattr(record, field_name)
            return sanitize_odoo_value(val, field_type)
        except AccessError as e:
            raise GraphQLError(str(e), extensions={'code': 'FORBIDDEN'})
        except Exception as e:
            _logger.warning("Error reading field %s on %s: %s", field_name, model_name, e)
            return None
    return field_resolver


def make_connection_resolver(model_name, default_limit=20, max_limit=100):
    def connection_resolver(root, info, **args):
        env = info.context['env']
        deny_checker = info.context.get('deny_checker')

        if deny_checker:
            denied, reason = deny_checker.is_denied(model_name, field=None, operation='read')
            if denied:
                raise ForbiddenResourceError(f"Access to model '{model_name}' is forbidden: {reason}")

        first = args.get('first', default_limit)
        if first <= 0:
            first = default_limit
        if first > max_limit:
            first = max_limit

        after = args.get('after')
        offset = decode_cursor(after)

        order = args.get('order') or 'id asc'

        domain = []
        if 'id' in args and args['id'] is not None:
            domain.append(('id', '=', args['id']))
        elif 'ids' in args and args['ids']:
            domain.append(('id', 'in', args['ids']))
        elif 'domain' in args and args['domain']:
            domain += parse_safe_domain(args['domain'], deny_checker, model_name)

        try:
            Model = env[model_name]
            total_count = Model.search_count(domain)
            records = Model.search(domain, offset=offset, limit=first, order=order)

            edges = []
            for i, rec in enumerate(records):
                edges.append({
                    'cursor': encode_cursor(offset + i + 1),
                    'node': rec
                })

            page_info = {
                'hasNextPage': (offset + len(records)) < total_count,
                'hasPreviousPage': offset > 0,
                'startCursor': edges[0]['cursor'] if edges else None,
                'endCursor': edges[-1]['cursor'] if edges else None,
            }

            # Increment node count in request context for metrics
            info.context['node_count'] = info.context.get('node_count', 0) + len(records)

            return {
                'totalCount': total_count,
                'pageInfo': page_info,
                'edges': edges
            }
        except AccessError as e:
            raise GraphQLError(str(e), extensions={'code': 'FORBIDDEN'})
        except Exception as e:
            _logger.error("Error executing connection query for %s: %s", model_name, e)
            raise GraphQLError(f"Query error on {model_name}: {e}", extensions={'code': 'INTERNAL_SERVER_ERROR'})

    return connection_resolver


def make_create_resolver(model_name):
    def create_resolver(root, info, values):
        env = info.context['env']
        deny_checker = info.context.get('deny_checker')

        if deny_checker:
            denied, reason = deny_checker.is_denied(model_name, field=None, operation='create')
            if denied:
                raise ForbiddenResourceError(f"Creation on model '{model_name}' is forbidden: {reason}")
            for fname in values.keys():
                denied, reason = deny_checker.is_denied(model_name, field=fname, operation='create')
                if denied:
                    raise ForbiddenResourceError(f"Field '{fname}' on model '{model_name}' is forbidden: {reason}")

        try:
            rec = env[model_name].create(values)
            return {
                'node': rec,
                'userErrors': []
            }
        except (ValidationError, UserError) as e:
            return {
                'node': None,
                'userErrors': [{'message': str(e), 'field': None, 'code': 'BAD_USER_INPUT'}]
            }
        except AccessError as e:
            raise GraphQLError(str(e), extensions={'code': 'FORBIDDEN'})
        except Exception as e:
            _logger.error("Error creating record on %s: %s", model_name, e)
            return {
                'node': None,
                'userErrors': [{'message': str(e), 'field': None, 'code': 'INTERNAL_SERVER_ERROR'}]
            }
    return create_resolver


def make_update_resolver(model_name):
    def update_resolver(root, info, id, values):
        env = info.context['env']
        deny_checker = info.context.get('deny_checker')

        if deny_checker:
            denied, reason = deny_checker.is_denied(model_name, field=None, operation='write')
            if denied:
                raise ForbiddenResourceError(f"Update on model '{model_name}' is forbidden: {reason}")
            for fname in values.keys():
                denied, reason = deny_checker.is_denied(model_name, field=fname, operation='write')
                if denied:
                    raise ForbiddenResourceError(f"Field '{fname}' on model '{model_name}' is forbidden: {reason}")

        try:
            rec = env[model_name].browse(id)
            if not rec.exists():
                return {
                    'node': None,
                    'userErrors': [{'message': f"Record ID {id} not found on {model_name}.", 'field': 'id', 'code': 'NOT_FOUND'}]
                }
            rec.write(values)
            return {
                'node': rec,
                'userErrors': []
            }
        except (ValidationError, UserError) as e:
            return {
                'node': None,
                'userErrors': [{'message': str(e), 'field': None, 'code': 'BAD_USER_INPUT'}]
            }
        except AccessError as e:
            raise GraphQLError(str(e), extensions={'code': 'FORBIDDEN'})
        except Exception as e:
            _logger.error("Error updating record %s on %s: %s", id, model_name, e)
            return {
                'node': None,
                'userErrors': [{'message': str(e), 'field': None, 'code': 'INTERNAL_SERVER_ERROR'}]
            }
    return update_resolver


def make_delete_resolver(model_name):
    def delete_resolver(root, info, id):
        env = info.context['env']
        deny_checker = info.context.get('deny_checker')

        if deny_checker:
            denied, reason = deny_checker.is_denied(model_name, field=None, operation='unlink')
            if denied:
                raise ForbiddenResourceError(f"Deletion on model '{model_name}' is forbidden: {reason}")

        try:
            rec = env[model_name].browse(id)
            if not rec.exists():
                return {
                    'success': False,
                    'id': id,
                    'userErrors': [{'message': f"Record ID {id} not found on {model_name}.", 'field': 'id', 'code': 'NOT_FOUND'}]
                }
            rec.unlink()
            return {
                'success': True,
                'id': id,
                'userErrors': []
            }
        except (ValidationError, UserError) as e:
            return {
                'success': False,
                'id': id,
                'userErrors': [{'message': str(e), 'field': None, 'code': 'BAD_USER_INPUT'}]
            }
        except AccessError as e:
            raise GraphQLError(str(e), extensions={'code': 'FORBIDDEN'})
        except Exception as e:
            _logger.error("Error unlinking record %s on %s: %s", id, model_name, e)
            return {
                'success': False,
                'id': id,
                'userErrors': [{'message': str(e), 'field': None, 'code': 'INTERNAL_SERVER_ERROR'}]
            }
    return delete_resolver


def resolve_rotate_api_key(root, info, expiresInDays=30):
    env = info.context['env']
    user = env.user
    api_key_record = info.context.get('api_key_record')

    if not api_key_record:
        return {
            'newKey': None,
            'expirationDate': None,
            'userErrors': [{'message': "Cannot rotate key: authentication did not use a manageable API key.", 'field': 'key', 'code': 'UNAUTHENTICATED'}]
        }

    days = int(expiresInDays or 30)
    if days <= 0 or days > 365:
        days = 30

    exp = datetime.utcnow() + timedelta(days=days)
    new_key_name = f"Rotated Key ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')})"

    try:
        new_token = env['res.users.apikeys'].with_user(user).sudo()._generate('graphql', new_key_name, exp)
        # Unlink the old key record
        api_key_record.sudo().unlink()

        # Track in context so log writer masks it!
        info.context['new_rotated_key'] = new_token

        return {
            'newKey': new_token,
            'expirationDate': exp.isoformat(),
            'userErrors': []
        }
    except Exception as e:
        _logger.error("Error rotating API key for user %s: %s", user.login, e)
        return {
            'newKey': None,
            'expirationDate': None,
            'userErrors': [{'message': f"Failed to rotate key: {e}", 'field': None, 'code': 'INTERNAL_SERVER_ERROR'}]
        }


def make_call_resolver(model_name):
    def call_resolver(root, info, method, id=None, ids=None, args=None, kwargs=None):
        return _execute_model_method(info, model_name, method, id=id, ids=ids, args=args, kwargs=kwargs)
    return call_resolver


def resolve_generic_call_method(root, info, model, method, id=None, ids=None, args=None, kwargs=None):
    return _execute_model_method(info, model, method, id=id, ids=ids, args=args, kwargs=kwargs)


def _execute_model_method(info, model_name, method, id=None, ids=None, args=None, kwargs=None):
    env = info.context['env']
    deny_checker = info.context.get('deny_checker')

    # 1. Private method check (Absolute Security Guardrail)
    if not method or method.startswith('_'):
        raise GraphQLError(
            f"Calling private or internal method '{method}' is strictly prohibited.",
            extensions={'code': 'FORBIDDEN_RESOURCE'}
        )

    # 2. Model existence check
    if model_name not in env:
        return {
            'success': False,
            'result': None,
            'userErrors': [{'message': f"Model '{model_name}' does not exist.", 'field': 'model', 'code': 'NOT_FOUND'}]
        }

    # 3. Deny policy check
    if deny_checker:
        denied, reason = deny_checker.is_denied(model_name, field=method, operation='call')
        if not denied:
            denied, reason = deny_checker.is_denied(model_name, field=None, operation='call')
        if denied:
            raise ForbiddenResourceError(f"Calling method '{method}' on model '{model_name}' is forbidden: {reason}")

    try:
        Model = env[model_name]
        if not hasattr(Model, method):
            return {
                'success': False,
                'result': None,
                'userErrors': [{'message': f"Method '{method}' does not exist on model '{model_name}'.", 'field': 'method', 'code': 'METHOD_NOT_FOUND'}]
            }

        # Resolve recordset (or model if no ID provided)
        rec_ids = []
        if id is not None:
            rec_ids = [id]
        elif ids:
            rec_ids = [i for i in ids if i is not None]

        records = Model.browse(rec_ids) if rec_ids else Model

        # Verify attribute is callable
        func = getattr(records, method)
        if not callable(func):
            return {
                'success': False,
                'result': None,
                'userErrors': [{'message': f"Attribute '{method}' on model '{model_name}' is not callable.", 'field': 'method', 'code': 'NOT_CALLABLE'}]
            }

        # Parse optional JSON args & kwargs
        parsed_args = []
        if args:
            try:
                parsed_args = json.loads(args) if isinstance(args, str) else list(args)
            except Exception as e:
                return {
                    'success': False,
                    'result': None,
                    'userErrors': [{'message': f"Invalid JSON in 'args': {e}", 'field': 'args', 'code': 'BAD_USER_INPUT'}]
                }

        parsed_kwargs = {}
        if kwargs:
            try:
                parsed_kwargs = json.loads(kwargs) if isinstance(kwargs, str) else dict(kwargs)
            except Exception as e:
                return {
                    'success': False,
                    'result': None,
                    'userErrors': [{'message': f"Invalid JSON in 'kwargs': {e}", 'field': 'kwargs', 'code': 'BAD_USER_INPUT'}]
                }

        # Execute method under service user's security context!
        raw_res = func(*parsed_args, **parsed_kwargs)

        # Format result string
        res_str = None
        if raw_res is not None:
            if isinstance(raw_res, (dict, list)):
                try:
                    res_str = json.dumps(raw_res, default=str)
                except Exception:
                    res_str = str(raw_res)
            else:
                res_str = str(raw_res)

        return {
            'success': True,
            'result': res_str,
            'userErrors': []
        }
    except (ValidationError, UserError) as e:
        return {
            'success': False,
            'result': None,
            'userErrors': [{'message': str(e), 'field': None, 'code': 'BAD_USER_INPUT'}]
        }
    except AccessError as e:
        raise GraphQLError(str(e), extensions={'code': 'FORBIDDEN'})
    except Exception as e:
        _logger.exception("Error executing method %s on %s: %s", method, model_name, e)
        return {
            'success': False,
            'result': None,
            'userErrors': [{'message': str(e), 'field': None, 'code': 'INTERNAL_SERVER_ERROR'}]
        }
