"""Typed failures for Athlete Context Memory persistence and write policy."""


class ContextMemoryError(RuntimeError):
    pass


class MemoryNotFoundError(ContextMemoryError):
    pass


class MemoryCollisionError(ContextMemoryError):
    pass


class IllegalMemoryLifecycleTransitionError(ContextMemoryError):
    pass


class MemoryWriteRejectedError(ContextMemoryError):
    pass


class ExplicitAuthorizationRequiredError(ContextMemoryError):
    pass


class ForgottenMemoryReplayError(ContextMemoryError):
    pass


class MemoryPersistenceInvariantError(ContextMemoryError):
    pass
