"""Typed failures exposed by the Intervals.icu boundary."""


class IntervalsError(RuntimeError):
    code = "intervals_error"


class ConfigurationMissing(IntervalsError):
    code = "configuration_missing"


class AuthenticationFailure(IntervalsError):
    code = "authentication_failure"


class RateLimited(IntervalsError):
    code = "rate_limited"


class ProviderUnavailable(IntervalsError):
    code = "provider_unavailable"


class MalformedResponse(IntervalsError):
    code = "malformed_response"


class PersistenceFailure(IntervalsError):
    code = "persistence_failure"


class PaginationFailure(IntervalsError):
    code = "pagination_failure"
