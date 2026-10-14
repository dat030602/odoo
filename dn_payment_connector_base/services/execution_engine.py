# -*- coding: utf-8 -*-

from odoo import models, api, _
import json


class ConnectorContext:
    """
    Connector context object that carries data through the execution pipeline.
    """
    
    def __init__(self, provider, environment, api, endpoint, record, company=None, user=None):
        self.provider = provider
        self.environment = environment
        self.api = api
        self.endpoint = endpoint
        self.record = record
        self.company = company or (record.env.company if hasattr(record, 'env') else None)
        self.user = user or (record.env.user if hasattr(record, 'env') else None)
        self.variables = {}
        self.cache = {}
        self.execution = None
    
    def get_variable(self, key, default=None):
        return self.variables.get(key, default)
    
    def set_variable(self, key, value):
        self.variables[key] = value
    
    def get_cache(self, key, default=None):
        return self.cache.get(key, default)
    
    def set_cache(self, key, value):
        self.cache[key] = value


class ExecutionEngine(models.AbstractModel):
    _name = 'connector.execution.engine'
    _description = 'Connector Execution Engine'
    
    @api.model
    def execute(self, api_code, source_record, environment_code=None, mode='sync'):
        """
        Execute an API call pipeline.
        """
        provider, environment, api_rec, endpoint = self._load_configuration(api_code, environment_code)
        execution = self._create_execution(provider, api_rec, endpoint, source_record, mode)
        context = self._build_context(provider, environment, api_rec, endpoint, source_record, execution)
        
        execution.start()
        try:
            result = self._run_pipeline(context)
            execution.complete(
                success=result.get('success', False),
                error_message=result.get('error_message'),
                response_status_code=result.get('status_code'),
                response_body=result.get('response_body')
            )
            return result
        except Exception as e:
            error_message = str(e)
            execution.complete(success=False, error_message=error_message)
            self.env['connector.error.log'].create_log(
                execution=execution,
                error_type=type(e).__name__,
                error_message=error_message,
                error_traceback=self.env.context.get('error_traceback'),
                severity='error'
            )
            return {
                'success': False,
                'error_message': error_message,
            }

    @api.model
    def build_redirect_url(self, api_code, source_record, extra_params=None, environment_code=None):
        """
        Generic: Build a redirect URL for payment gateways.
        
        1. Load config (provider, environment, api, endpoint)
        2. Resolve QUERY mapping to get params dict
        3. Merge extra_params
        4. Compute hash using endpoint's hash method
        5. Build full URL with hash appended
        """
        provider, environment, api_rec, endpoint = self._load_configuration(api_code, environment_code)
        context = self._build_context(provider, environment, api_rec, endpoint, source_record, None)
        
        # Load source data
        self.env['connector.load.engine'].load_source_data(context)
        
        # Merge extra params into variables
        if extra_params:
            for k, v in extra_params.items():
                context.set_variable(k, v)
                
        # Resolve query parameters
        params = self.env['connector.mapping.engine'].build_mapping(context, 'QUERY')
        if extra_params:
            params.update({k: v for k, v in extra_params.items() if k != 'hash_secret'})

        # Secret key
        secret = (extra_params and extra_params.get('hash_secret')) or None
        if not secret:
            secret_code = endpoint.secret_setting_code or 'hash_secret'
            secret = provider.get_setting(secret_code, environment.id if environment else None)
        
        hash_value = ''
        if endpoint.hash_method_id and secret:
            hash_value = endpoint.hash_method_id.build_signature(params, secret)
            
        full_url = endpoint.get_full_url()
        hash_param_name = endpoint.hash_param_name or 'vnp_SecureHash'
        
        return self.env['connector.http.engine'].build_redirect_url(
            full_url, params, hash_key=hash_param_name, hash_value=hash_value
        )

    @api.model
    def handle_callback(self, provider_code, callback_data, hash_style='sorted_query',
                        exclude_keys=None, hash_key='vnp_SecureHash',
                        secret_setting_code='hash_secret', secret=None):
        """
        Generic: Verify and process an incoming callback (IPN/webhook/return).
        """
        provider = self.env['connector.provider'].search([('code', '=', provider_code)], limit=1)
        if not provider:
            return {
                'valid': False,
                'provider': None,
                'data': callback_data,
                'error': f"Provider not found: {provider_code}",
            }
            
        if not secret:
            secret = provider.get_setting(secret_setting_code)
        if not secret or provider_code == 'vnpay':
            pay_prov = self.env['payment.provider'].sudo().search([('code', '=', provider_code)], limit=1)
            field_name = f"{provider_code}_{secret_setting_code}"
            if pay_prov and hasattr(pay_prov, field_name):
                val = getattr(pay_prov, field_name)
                if val:
                    secret = val
        received_hash = callback_data.get(hash_key, '')
        
        exclude = list(exclude_keys or [hash_key, 'vnp_SecureHashType'])
        
        valid = self.env['connector.hash.engine'].verify_hash(
            received_hash=received_hash,
            params=callback_data,
            secret=secret,
            algorithm='hmac_sha512',
            hash_style=hash_style,
            exclude_keys=exclude
        )
        
        clean_data = {k: v for k, v in callback_data.items() if k not in exclude}
        return {
            'valid': valid,
            'provider': provider,
            'data': clean_data,
            'error': None if valid else 'Invalid checksum signature',
        }

    @api.model
    def call_api(self, api_code, payload=None, environment_code=None):
        """
        Generic: Make a server-to-server API call (POST JSON/form).
        """
        provider, environment, api_rec, endpoint = self._load_configuration(api_code, environment_code)
        context = self._build_context(provider, environment, api_rec, endpoint, None, None)
        
        if payload:
            context.set_variable('payload', payload)
            
        secret_code = endpoint.secret_setting_code or 'hash_secret'
        secret = provider.get_setting(secret_code, environment.id if environment else None)
        
        if endpoint.hash_method_id and secret and isinstance(payload, dict):
            hash_val = endpoint.hash_method_id.build_signature(payload, secret)
            hash_key = endpoint.hash_param_name or 'vnp_SecureHash'
            payload[hash_key] = hash_val
            context.set_variable('payload', payload)
            
        http_result = self.env['connector.http.engine'].send_request(context)
        parsed_response = self.env['connector.response.engine'].parse_response(context, http_result)
        
        return {
            'success': http_result.get('success', False),
            'status_code': http_result.get('status_code'),
            'data': parsed_response,
            'raw': http_result.get('response_body', ''),
            'error': http_result.get('error_message'),
        }

    def _load_configuration(self, api_code, environment_code=None):
        api_rec = self.env['connector.api'].search([('code', '=', api_code)], limit=1)
        if not api_rec:
            raise ValueError(f"API not found: {api_code}")
        
        provider = api_rec.provider_id
        if environment_code:
            environment = provider.get_environment(environment_code)
        else:
            environment = provider.get_environment()
        
        if not environment:
            raise ValueError(f"Environment not found for provider: {provider.code}")
        
        endpoint = api_rec.get_endpoint(environment.id)
        if not endpoint:
            raise ValueError(f"Endpoint not found for API: {api_rec.code} in environment: {environment.code}")
        
        return provider, environment, api_rec, endpoint

    def _create_execution(self, provider, api_rec, endpoint, source_record, mode):
        return self.env['connector.execution'].create({
            'provider_id': provider.id,
            'api_id': api_rec.id,
            'endpoint_id': endpoint.id,
            'environment_id': endpoint.environment_id.id,
            'res_model': source_record._name if source_record else False,
            'res_id': source_record.id if source_record else False,
            'mode': mode,
            'state': 'pending',
        })

    def _build_context(self, provider, environment, api_rec, endpoint, source_record, execution):
        context = ConnectorContext(
            provider=provider,
            environment=environment,
            api=api_rec,
            endpoint=endpoint,
            record=source_record,
            company=source_record.env.company if (source_record and hasattr(source_record, 'env')) else self.env.company,
            user=source_record.env.user if (source_record and hasattr(source_record, 'env')) else self.env.user,
        )
        context.execution = execution
        return context

    def _run_pipeline(self, context):
        self._run_load_engine(context)
        self._run_mapping_engine(context)
        self._run_auth_engine(context)
        self._run_hash_engine(context)
        http_result = self._run_http_engine(context)
        response_data = self._run_response_engine(context, http_result)
        self._run_business_engine(context, response_data)
        
        return {
            'success': http_result.get('success', False),
            'status_code': http_result.get('status_code'),
            'response_body': http_result.get('response_body'),
            'response_data': response_data,
        }

    def _run_load_engine(self, context):
        if context.execution:
            step = context.execution.add_step('Load Engine')
            step.start()
        try:
            self.env['connector.load.engine'].load_source_data(context)
            if context.execution:
                step.complete(success=True)
        except Exception as e:
            if context.execution:
                step.complete(success=False, error_message=str(e))
            raise

    def _run_mapping_engine(self, context):
        if context.execution:
            step = context.execution.add_step('Mapping Engine')
            step.start()
        try:
            headers = self.env['connector.mapping.engine'].build_mapping(context, 'HEADER')
            query = self.env['connector.mapping.engine'].build_mapping(context, 'QUERY')
            payload = self.env['connector.mapping.engine'].build_mapping(context, 'PAYLOAD')
            context.set_variable('headers', headers)
            context.set_variable('query_params', query)
            context.set_variable('payload', payload)
            if context.execution:
                step.complete(success=True)
        except Exception as e:
            if context.execution:
                step.complete(success=False, error_message=str(e))
            raise

    def _run_auth_engine(self, context):
        if context.execution:
            step = context.execution.add_step('Authentication Engine')
            step.start()
        try:
            self.env['connector.auth.engine'].authenticate(context)
            if context.execution:
                step.complete(success=True)
        except Exception as e:
            if context.execution:
                step.complete(success=False, error_message=str(e))
            raise

    def _run_hash_engine(self, context):
        if context.execution:
            step = context.execution.add_step('Hash Engine')
            step.start()
        try:
            hash_str = self.env['connector.hash.engine'].generate_hash(context)
            context.set_variable('hash', hash_str)
            if context.execution:
                step.complete(success=True)
        except Exception as e:
            if context.execution:
                step.complete(success=False, error_message=str(e))
            raise

    def _run_http_engine(self, context):
        if context.execution:
            step = context.execution.add_step('HTTP Engine')
            step.start()
        try:
            res = self.env['connector.http.engine'].send_request(context)
            if context.execution:
                step.complete(success=res.get('success', False))
            return res
        except Exception as e:
            if context.execution:
                step.complete(success=False, error_message=str(e))
            raise

    def _run_response_engine(self, context, http_result):
        if context.execution:
            step = context.execution.add_step('Response Engine')
            step.start()
        try:
            data = self.env['connector.response.engine'].parse_response(context, http_result)
            if context.execution:
                step.complete(success=True)
            return data
        except Exception as e:
            if context.execution:
                step.complete(success=False, error_message=str(e))
            raise

    def _run_business_engine(self, context, response_data):
        if context.execution:
            step = context.execution.add_step('Business Engine')
            step.start()
        try:
            res = self.env['connector.business.engine'].execute_actions(context, response_data)
            if context.execution:
                step.complete(success=True)
            return res
        except Exception as e:
            if context.execution:
                step.complete(success=False, error_message=str(e))
            raise
