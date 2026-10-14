import logging
from typing import Dict

import odoo
from graphql import (
    GraphQLArgument,
    GraphQLBoolean,
    GraphQLField,
    GraphQLFloat,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
)

from .resolvers import (
    make_connection_resolver,
    make_create_resolver,
    make_delete_resolver,
    make_field_resolver,
    make_update_resolver,
    make_call_resolver,
    resolve_generic_call_method,
    resolve_rotate_api_key,
)

_logger = logging.getLogger(__name__)

# Global cache of compiled schemas by db name and version token
_SCHEMA_CACHE = {}


def pascal_case(s: str) -> str:
    """Converts 'sale.order' -> 'SaleOrder', 'res.partner' -> 'ResPartner'"""
    parts = s.replace('_', '.').split('.')
    return ''.join(p.capitalize() for p in parts if p)


# Reusable static GraphQL types
UserErrorType = GraphQLObjectType(
    name='UserError',
    fields={
        'message': GraphQLField(GraphQLNonNull(GraphQLString), description="Error description"),
        'field': GraphQLField(GraphQLString, description="Field path causing error"),
        'code': GraphQLField(GraphQLString, description="Error classification code"),
    }
)

PageInfoType = GraphQLObjectType(
    name='PageInfo',
    fields={
        'hasNextPage': GraphQLField(GraphQLNonNull(GraphQLBoolean)),
        'hasPreviousPage': GraphQLField(GraphQLNonNull(GraphQLBoolean)),
        'startCursor': GraphQLField(GraphQLString),
        'endCursor': GraphQLField(GraphQLString),
    }
)

DeletePayloadType = GraphQLObjectType(
    name='DeletePayload',
    fields={
        'success': GraphQLField(GraphQLNonNull(GraphQLBoolean)),
        'id': GraphQLField(GraphQLInt),
        'userErrors': GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(UserErrorType)))),
    }
)

CallPayloadType = GraphQLObjectType(
    name='CallPayload',
    fields={
        'success': GraphQLField(GraphQLNonNull(GraphQLBoolean), description="True if method executed successfully"),
        'result': GraphQLField(GraphQLString, description="Method return value (JSON string or representation)"),
        'userErrors': GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(UserErrorType)))),
    }
)

RotateApiKeyPayloadType = GraphQLObjectType(
    name='RotateApiKeyPayload',
    fields={
        'newKey': GraphQLField(GraphQLString, description="Newly generated API Key (displayed once)"),
        'expirationDate': GraphQLField(GraphQLString, description="Expiration ISO timestamp"),
        'userErrors': GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(UserErrorType)))),
    }
)

GenericM2ONodeType = GraphQLObjectType(
    name='GenericMany2oneRecord',
    fields={
        'id': GraphQLField(GraphQLInt),
        'name': GraphQLField(GraphQLString, resolve=lambda rec, *_: getattr(rec, 'name', rec.display_name if hasattr(rec, 'display_name') else str(rec))),
        'display_name': GraphQLField(GraphQLString, resolve=lambda rec, *_: rec.display_name if hasattr(rec, 'display_name') else str(rec)),
    }
)


def get_graphql_scalar(field_type: str):
    """Maps Odoo field types to GraphQL scalar types."""
    if field_type in ('char', 'text', 'html', 'selection', 'reference'):
        return GraphQLString
    elif field_type == 'integer':
        return GraphQLInt
    elif field_type in ('float', 'monetary'):
        return GraphQLFloat
    elif field_type == 'boolean':
        return GraphQLBoolean
    elif field_type in ('date', 'datetime'):
        return GraphQLString
    return None


class SchemaBuilder:
    def __init__(self, env):
        self.env = env
        self.object_types: Dict[str, GraphQLObjectType] = {}
        self.input_types: Dict[str, GraphQLInputObjectType] = {}
        self.connection_types: Dict[str, GraphQLObjectType] = {}

    def build_schema(self) -> GraphQLSchema:
        whitelist_models = self.env['dn.graphql.model'].sudo().search([('active', '=', True)])
        if not whitelist_models:
            # Fallback minimal schema if no models configured yet
            return GraphQLSchema(
                query=GraphQLObjectType('Query', {'ping': GraphQLField(GraphQLString, resolve=lambda *_: 'GraphQL Gateway Active')}),
                mutation=GraphQLObjectType('Mutation', {'rotateApiKey': GraphQLField(RotateApiKeyPayloadType, resolve=resolve_rotate_api_key)})
            )

        # Pass 1: Build Object Types & Input Types for all whitelisted models
        for wm in whitelist_models:
            model_name = wm.model_name
            if model_name not in self.env:
                continue
            self._create_types_for_model(wm)

        # Pass 2: Build Query Fields
        query_fields = {}
        for wm in whitelist_models:
            model_name = wm.model_name
            if model_name not in self.connection_types:
                continue

            field_ident = model_name.replace('.', '__')
            conn_type = self.connection_types[model_name]

            query_fields[field_ident] = GraphQLField(
                type_=conn_type,
                args={
                    'first': GraphQLArgument(GraphQLInt, default_value=wm.default_limit or 20, description="Page limit"),
                    'after': GraphQLArgument(GraphQLString, description="Cursor for pagination"),
                    'domain': GraphQLArgument(GraphQLString, description="Odoo domain filter expression"),
                    'order': GraphQLArgument(GraphQLString, default_value="id asc", description="Sort order expression"),
                    'id': GraphQLArgument(GraphQLInt, description="Single record ID lookup"),
                    'ids': GraphQLArgument(GraphQLList(GraphQLInt), description="Multiple record IDs lookup"),
                },
                resolve=make_connection_resolver(model_name, wm.default_limit or 20, wm.max_limit or 100),
                description=f"Query connection for Odoo model {model_name}"
            )

        # Pass 3: Build Mutation Fields
        mutation_fields = {
            'rotateApiKey': GraphQLField(
                type_=RotateApiKeyPayloadType,
                args={'expiresInDays': GraphQLArgument(GraphQLInt, default_value=30)},
                resolve=resolve_rotate_api_key,
                description="Rotate the current API Key and generate a new key token."
            ),
            'callMethod': GraphQLField(
                type_=CallPayloadType,
                args={
                    'model': GraphQLArgument(GraphQLNonNull(GraphQLString), description="Target Odoo model e.g. 'sale.order'"),
                    'method': GraphQLArgument(GraphQLNonNull(GraphQLString), description="Public business method to call e.g. 'action_confirm'"),
                    'id': GraphQLArgument(GraphQLInt, description="Single record ID"),
                    'ids': GraphQLArgument(GraphQLList(GraphQLNonNull(GraphQLInt)), description="List of record IDs"),
                    'args': GraphQLArgument(GraphQLString, description="Optional positional arguments JSON array string e.g. '[1, 2]'"),
                    'kwargs': GraphQLArgument(GraphQLString, description="Optional keyword arguments JSON object string e.g. '{\"force\": true}'"),
                },
                resolve=resolve_generic_call_method,
                description="Invoke a public business method on an Odoo model or recordset."
            ),
        }

        for wm in whitelist_models:
            model_name = wm.model_name
            field_ident = model_name.replace('.', '__')
            obj_type = self.object_types.get(model_name)
            input_type = self.input_types.get(model_name)

            if not obj_type or not input_type:
                continue

            # Payload Type
            payload_type = GraphQLObjectType(
                name=f"{pascal_case(model_name)}Payload",
                fields={
                    'node': GraphQLField(obj_type),
                    'userErrors': GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(UserErrorType)))),
                }
            )

            # Create mutation
            if wm.allow_create:
                mutation_fields[f"{field_ident}__create"] = GraphQLField(
                    type_=payload_type,
                    args={'values': GraphQLArgument(GraphQLNonNull(input_type))},
                    resolve=make_create_resolver(model_name),
                    description=f"Create a new {model_name} record"
                )

            # Update mutation
            if wm.allow_write:
                mutation_fields[f"{field_ident}__update"] = GraphQLField(
                    type_=payload_type,
                    args={
                        'id': GraphQLArgument(GraphQLNonNull(GraphQLInt)),
                        'values': GraphQLArgument(GraphQLNonNull(input_type)),
                    },
                    resolve=make_update_resolver(model_name),
                    description=f"Update an existing {model_name} record"
                )

            # Delete mutation
            if wm.allow_unlink:
                mutation_fields[f"{field_ident}__delete"] = GraphQLField(
                    type_=DeletePayloadType,
                    args={'id': GraphQLArgument(GraphQLNonNull(GraphQLInt))},
                    resolve=make_delete_resolver(model_name),
                    description=f"Delete an existing {model_name} record"
                )

            # Business Method Call mutation
            mutation_fields[f"{field_ident}__call"] = GraphQLField(
                type_=CallPayloadType,
                args={
                    'method': GraphQLArgument(GraphQLNonNull(GraphQLString), description=f"Public business method to invoke on {model_name}"),
                    'id': GraphQLArgument(GraphQLInt, description="Single record ID"),
                    'ids': GraphQLArgument(GraphQLList(GraphQLNonNull(GraphQLInt)), description="List of record IDs"),
                    'args': GraphQLArgument(GraphQLString, description="Optional positional arguments JSON array string e.g. '[1, 2]'"),
                    'kwargs': GraphQLArgument(GraphQLString, description="Optional keyword arguments JSON object string e.g. '{\"force\": true}'"),
                },
                resolve=make_call_resolver(model_name),
                description=f"Invoke a public business method on {model_name} records (e.g. action_confirm, button_validate, action_cancel)"
            )

        schema = GraphQLSchema(
            query=GraphQLObjectType('Query', query_fields),
            mutation=GraphQLObjectType('Mutation', mutation_fields)
        )
        return schema

    def _get_or_create_type_for_model(self, model_name: str, depth: int = 0) -> GraphQLObjectType:
        """Lazily creates or returns GraphQLObjectType for any Odoo model in the system."""
        if model_name in self.object_types:
            return self.object_types[model_name]

        if model_name not in self.env or depth > 4:
            return GenericM2ONodeType

        type_name = pascal_case(model_name)

        def get_fields():
            return self._build_fields_for_model(model_name, depth)

        obj_type = GraphQLObjectType(
            name=type_name,
            fields=get_fields,
            description=f"Odoo model {model_name}"
        )
        self.object_types[model_name] = obj_type
        return obj_type

    def _build_fields_for_model(self, model_name: str, depth: int = 0) -> Dict[str, GraphQLField]:
        if model_name not in self.env:
            return {'id': GraphQLField(GraphQLInt)}

        Model = self.env[model_name]
        fields_dict = {
            'id': GraphQLField(GraphQLInt, description="Primary Record ID"),
            'display_name': GraphQLField(
                GraphQLString,
                description="Display Name",
                resolve=lambda rec, *_: rec.display_name if hasattr(rec, 'display_name') else str(rec)
            ),
        }

        # Check whitelist if specified
        wm = self.env['dn.graphql.model'].sudo().search([('model_name', '=', model_name), ('active', '=', True)], limit=1)
        exposed_fnames = set(wm.field_ids.mapped('name')) if (wm and wm.field_ids) else set(Model._fields.keys())

        for fname in exposed_fnames:
            if fname in ('id', 'display_name') or fname not in Model._fields:
                continue
            f = Model._fields[fname]
            ftype = f.type

            if ftype == 'binary':
                continue

            scalar = get_graphql_scalar(ftype)
            if scalar:
                fdef = GraphQLField(
                    type_=scalar,
                    resolve=make_field_resolver(fname, ftype, model_name),
                    description=f.string or fname
                )
                fdef.extensions = {'odoo_model': model_name, 'odoo_field': fname}
                fields_dict[fname] = fdef

            elif ftype == 'many2one':
                target_model = f.comodel_name
                target_obj_type = self._get_or_create_type_for_model(target_model, depth=depth + 1)

                def make_m2o_resolver(f_name=fname):
                    def m2o_resolver(rec, info, **_):
                        rel_rec = getattr(rec, f_name)
                        return rel_rec if rel_rec else None
                    return m2o_resolver

                fdef = GraphQLField(
                    type_=target_obj_type,
                    resolve=make_m2o_resolver(),
                    description=f.string or fname
                )
                fdef.extensions = {'odoo_model': model_name, 'odoo_field': fname}
                fields_dict[fname] = fdef

            elif ftype in ('one2many', 'many2many') and depth < 2:
                target_model = f.comodel_name
                target_obj_type = self._get_or_create_type_for_model(target_model, depth=depth + 1)

                def make_x2m_resolver(f_name=fname):
                    def x2m_resolver(rec, info, **_):
                        rel_recs = getattr(rec, f_name)
                        return list(rel_recs) if rel_recs else []
                    return x2m_resolver

                fdef = GraphQLField(
                    type_=GraphQLList(target_obj_type),
                    resolve=make_x2m_resolver(),
                    description=f.string or fname
                )
                fdef.extensions = {'odoo_model': model_name, 'odoo_field': fname}
                fields_dict[fname] = fdef

        # Special convenience aliases for inventory & movements:
        if model_name == 'stock.picking.type':
            if 'default_location_src_id' in fields_dict and 'location_src_id' not in fields_dict:
                fields_dict['location_src_id'] = fields_dict['default_location_src_id']
            if 'default_location_dest_id' in fields_dict and 'location_dest_id' not in fields_dict:
                fields_dict['location_dest_id'] = fields_dict['default_location_dest_id']
        elif model_name == 'stock.picking':
            if 'location_id' in fields_dict and 'location_src_id' not in fields_dict:
                fields_dict['location_src_id'] = fields_dict['location_id']
        elif model_name == 'stock.move':
            if 'quantity' in fields_dict and 'quantity_done' not in fields_dict:
                fields_dict['quantity_done'] = fields_dict['quantity']

        return fields_dict

    def _create_types_for_model(self, wm):
        model_name = wm.model_name
        Model = self.env[model_name]
        type_name = pascal_case(model_name)
        obj_type = self._get_or_create_type_for_model(model_name, depth=0)

        # Build Edge and Connection Types
        edge_type = GraphQLObjectType(
            name=f"{type_name}Edge",
            fields={
                'cursor': GraphQLField(GraphQLNonNull(GraphQLString)),
                'node': GraphQLField(obj_type),
            }
        )

        conn_type = GraphQLObjectType(
            name=f"{type_name}Connection",
            fields={
                'totalCount': GraphQLField(GraphQLInt, description="Total matching records count"),
                'pageInfo': GraphQLField(GraphQLNonNull(PageInfoType)),
                'edges': GraphQLField(GraphQLList(edge_type)),
            }
        )
        self.connection_types[model_name] = conn_type

        # Build Input Type for Create / Update (scalars and Many2one ID only; strictly NO binary fields)
        exposed_field_names = set(wm.field_ids.mapped('name')) if wm.field_ids else set(Model._fields.keys())
        input_fields = {}
        for fname in exposed_field_names:
            if fname == 'id' or fname not in Model._fields:
                continue
            f = Model._fields[fname]
            if f.readonly:
                continue
            ftype = f.type

            # File upload strictly disallowed
            if ftype == 'binary':
                continue

            scalar = get_graphql_scalar(ftype)
            if scalar:
                input_fields[fname] = GraphQLInputField(scalar, description=f.string or fname)
            elif ftype == 'many2one':
                input_fields[fname] = GraphQLInputField(GraphQLInt, description=f"Relational ID for {f.string or fname}")

        if input_fields:
            input_type = GraphQLInputObjectType(
                name=f"{type_name}Input",
                fields=input_fields,
                description=f"Input parameters for {model_name}"
            )
            self.input_types[model_name] = input_type


def get_schema(env) -> GraphQLSchema:
    """Thread-safe schema accessor with database-level caching."""
    db_name = env.cr.dbname
    # Invalidate key can be bumped by model changes
    cache_key = f"{db_name}"
    if cache_key in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[cache_key]

    builder = SchemaBuilder(env)
    schema = builder.build_schema()
    _SCHEMA_CACHE[cache_key] = schema
    return schema


def invalidate_schema_cache(db_name=None):
    global _SCHEMA_CACHE
    if db_name and db_name in _SCHEMA_CACHE:
        del _SCHEMA_CACHE[db_name]
    else:
        _SCHEMA_CACHE.clear()
