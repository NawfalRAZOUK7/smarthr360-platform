"""smarthr360-integration — shared enterprise-integration toolkit.

Written once, vendored/installed into every SmartHR360 microservice so that
cross-cutting concerns are never copy-pasted (the platform's anti-duplication
rule). Data that a service does not own is read through :mod:`clients`, not
re-modelled locally.

Sub-packages:
    observability  idempotent Prometheus metric factories
    api            standardized response envelope, pagination and errors
    history        reusable Slowly Changing Dimension (Type 2) base + service
    clients        inter-service HTTP clients (e.g. CoreHRClient)
"""

__version__ = "0.1.0"

STANDARD = "SmartHR360"
