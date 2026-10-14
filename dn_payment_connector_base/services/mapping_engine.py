# -*- coding: utf-8 -*-

from odoo import models, api, _
import urllib.parse


class MappingEngine(models.AbstractModel):
    _name = 'connector.mapping.engine'
    _description = 'Connector Mapping Engine'
    
    @api.model
    def build_mapping(self, context, mapping_type):
        """
        Build mapping dictionary from connector.mapping records for this API.
        """
        if not hasattr(context, 'api') or not context.api:
            return {}
            
        mapping = context.api.get_mapping(mapping_type)
        if mapping:
            return mapping.build_dict(context)
        return {}

    @api.model
    def build_sorted_params(self, params, exclude_keys=None):
        """
        Generic: Sort params alphabetically, URL-encode keys and values.
        """
        if not params:
            return ''
        exclude = set(exclude_keys or [])
        sorted_keys = sorted(params.keys())
        parts = []
        for k in sorted_keys:
            if k in exclude:
                continue
            v = params[k]
            if v is not None and str(v) != '':
                parts.append(f"{urllib.parse.quote_plus(str(k))}={urllib.parse.quote_plus(str(v))}")
        return '&'.join(parts)

    @api.model
    def resolve_mapping_for_record(self, api_record, source_record, mapping_type, context=None):
        """
        Generic: Resolve a full mapping dict for a given source record.
        """
        if not api_record:
            return {}
        mapping = api_record.get_mapping(mapping_type)
        if not mapping:
            return {}
        if context is None:
            # Build minimal dummy context
            provider = api_record.provider_id
            environment = provider.get_environment()
            endpoint = api_record.get_endpoint(environment.id) if environment else None
            execution_engine = self.env['connector.execution.engine']
            context = execution_engine._build_context(
                provider, environment, api_record, endpoint, source_record, None
            )
        return mapping.build_dict(context)
