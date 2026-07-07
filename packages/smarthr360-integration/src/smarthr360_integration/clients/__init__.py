"""Inter-service HTTP clients.

The anti-duplication rule in practice: a service reads data it does not own
through these clients instead of re-modelling it locally. All clients propagate
the caller's JWT so downstream authorization is preserved.
"""

from .base import ServiceClient, ServiceClientError
from .core_hr import CoreHRClient

__all__ = ["ServiceClient", "ServiceClientError", "CoreHRClient"]
