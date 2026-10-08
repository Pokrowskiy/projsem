class DomainError(Exception):
    code = "domain_error"
    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404


class ConflictError(DomainError):
    code = "conflict"
    status_code = 409


class ForbiddenError(DomainError):
    code = "forbidden"
    status_code = 403


class BadRequestError(DomainError):
    code = "bad_request"
    status_code = 400