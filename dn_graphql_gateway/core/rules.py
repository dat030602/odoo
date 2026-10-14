from graphql import GraphQLError
from graphql.validation import ValidationRule


class DenyChecker:
    """
    Evaluates global and API-key-specific blocklist policies.
    Rules are cached in memory for the duration of the request.
    Deny always wins!
    """
    def __init__(self, env, key_rec_id=None, api_key_id=None):
        self.env = env
        self.key_rec_id = key_rec_id
        self.api_key_id = api_key_id
        self.denied = {} # (model, field or None, operation) -> reason

        domain = [('active', '=', True)]
        sub = []
        if key_rec_id:
            sub.append(('key_rec_id', '=', key_rec_id))
        if api_key_id:
            sub.append(('api_key_id', '=', api_key_id))

        if len(sub) == 2:
            domain += ['|', ('is_global', '=', True), '|', sub[0], sub[1]]
        elif len(sub) == 1:
            domain += ['|', ('is_global', '=', True), sub[0]]
        else:
            domain += [('is_global', '=', True)]

        rules = env['dn.graphql.deny'].sudo().search(domain)
        for r in rules:
            m = r.model_name
            f = r.field_name or None
            op = r.operation or 'all'
            reason = r.reason or "Resource is restricted by security policy."
            self.denied[(m, f, op)] = reason

    def is_denied(self, model, field=None, operation='all'):
        if not model:
            return False, None

        checks = [
            (model, field, operation),
            (model, field, 'all'),
            (model, None, operation),
            (model, None, 'all'),
        ]
        for c in checks:
            if c in self.denied:
                return True, self.denied[c]
        return False, None


class DenyListValidationRule(ValidationRule):
    """
    GraphQL AST validation rule that inspects query fields before execution.
    Raises GraphQLError with FORBIDDEN_RESOURCE if any denied model or field is encountered.
    """
    def __init__(self, context, checker: DenyChecker):
        super().__init__(context)
        self.checker = checker

    def enter_field(self, node, *args):
        field_name = node.name.value
        # Ignore introspection fields
        if field_name.startswith('__'):
            return

        # Check if root field corresponds to a model or mutation
        parent_type = self.context.get_parent_type()
        field_def = self.context.get_field_def()

        model_name = None
        op = 'read'

        if parent_type and parent_type.name == 'Query':
            # e.g. res__partner -> res.partner
            model_name = field_name.replace('__', '.')
            op = 'read'
        elif parent_type and parent_type.name == 'Mutation':
            # e.g. res__partner__create
            parts = field_name.split('__')
            if len(parts) >= 2 and parts[-1] in ('create', 'update', 'delete', 'call'):
                op_map = {'create': 'create', 'update': 'write', 'delete': 'unlink', 'call': 'call'}
                op = op_map.get(parts[-1], 'all')
                model_name = '.'.join(parts[:-1])

        if model_name:
            denied, reason = self.checker.is_denied(model_name, field=None, operation=op)
            if denied:
                self.report_error(
                    GraphQLError(
                        f"Access to model '{model_name}' ({op}) is forbidden: {reason}",
                        [node],
                        extensions={'code': 'FORBIDDEN_RESOURCE'}
                    )
                )

        # Check field on specific model if field_def has model metadata
        if field_def and hasattr(field_def, 'extensions') and field_def.extensions:
            f_model = field_def.extensions.get('odoo_model')
            f_name = field_def.extensions.get('odoo_field')
            if f_model and f_name:
                denied, reason = self.checker.is_denied(f_model, field=f_name, operation='read')
                if denied:
                    self.report_error(
                        GraphQLError(
                            f"Access to field '{f_name}' on model '{f_model}' is forbidden: {reason}",
                            [node],
                            extensions={'code': 'FORBIDDEN_RESOURCE'}
                        )
                    )


def calculate_query_depth(node, current_depth=0):
    """Calculates max selection depth of a GraphQL AST document."""
    max_d = current_depth
    if hasattr(node, 'definitions'):
        for defn in node.definitions:
            d = calculate_query_depth(defn, current_depth)
            if d > max_d:
                max_d = d
    elif hasattr(node, 'selection_set') and node.selection_set:
        for sel in node.selection_set.selections:
            name = getattr(sel, 'name', None)
            if name and name.value.startswith('__'):
                continue
            d = calculate_query_depth(sel, current_depth + 1)
            if d > max_d:
                max_d = d
    return max_d
