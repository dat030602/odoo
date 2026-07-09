# -*- coding: utf-8 -*-

from odoo import models, api, _


class LoggingEngine(models.AbstractModel):
    _name = 'connector.logging.engine'
    _description = 'Connector Logging Engine'
    
    @api.model
    def log_request(self, context, method, url, headers=None, body=None, query_params=None):
        """
        Log HTTP request.
        
        Args:
            context: ConnectorContext object
            method: HTTP method
            url: Request URL
            headers: Headers dictionary
            body: Request body
            query_params: Query parameters dictionary
            
        Returns:
            Request log record
        """
        return self.env['connector.request.log'].create_log(
            execution=context.execution,
            method=method,
            url=url,
            headers=headers,
            body=body,
            query_params=query_params,
            auth_method=context.endpoint.auth_method_id.code if context.endpoint.auth_method_id else None
        )
    
    @api.model
    def log_response(self, context, request_log, status_code, status_text=None, body=None, headers=None, duration=None):
        """
        Log HTTP response.
        
        Args:
            context: ConnectorContext object
            request_log: Request log record
            status_code: HTTP status code
            status_text: Status text
            body: Response body
            headers: Headers dictionary
            duration: Request duration
            
        Returns:
            Response log record
        """
        return self.env['connector.response.log'].create_log(
            execution=context.execution,
            request_log=request_log,
            status_code=status_code,
            status_text=status_text,
            body=body,
            body_type=context.endpoint.parser,
            headers=headers,
            duration=duration
        )
    
    @api.model
    def log_error(self, context, error_type, error_message, error_traceback=None, step_name=None, severity='error'):
        """
        Log error.
        
        Args:
            context: ConnectorContext object
            error_type: Type of error
            error_message: Error message
            error_traceback: Error traceback
            step_name: Step where error occurred
            severity: Error severity
            
        Returns:
            Error log record
        """
        return self.env['connector.error.log'].create_log(
            execution=context.execution,
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback,
            step_name=step_name,
            severity=severity
        )
