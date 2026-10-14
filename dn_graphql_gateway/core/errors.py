class GraphQLGatewayError(Exception):
    """Base exception for GraphQL Gateway"""
    code = 'INTERNAL_SERVER_ERROR'
    http_status = 500

    def __init__(self, message, code=None, http_status=None, path=None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status
        self.path = path


class AuthenticationError(GraphQLGatewayError):
    code = 'UNAUTHENTICATED'
    http_status = 401


class KeyExpiredError(GraphQLGatewayError):
    code = 'KEY_EXPIRED'
    http_status = 401


class ForbiddenResourceError(GraphQLGatewayError):
    code = 'FORBIDDEN_RESOURCE'
    http_status = 403


class UploadNotAllowedError(GraphQLGatewayError):
    code = 'UPLOAD_NOT_ALLOWED'
    http_status = 415


class RateLimitExceededError(GraphQLGatewayError):
    code = 'RATE_LIMITED'
    http_status = 429


class SavepointRollbackTrigger(Exception):
    """Internal trigger exception to force savepoint rollback on mutation failure"""
    def __init__(self, errors=None):
        super().__init__("Rollback triggered due to mutation errors.")
        self.errors = errors or []


def format_error_payload(message, code='INTERNAL_SERVER_ERROR', path=None, request_id=None):
    error_dict = {
        'message': str(message),
        'extensions': {
            'code': code,
        }
    }
    if path:
        error_dict['path'] = path
    if request_id:
        error_dict['extensions']['requestId'] = request_id
    return {
        'data': None,
        'errors': [error_dict]
    }
