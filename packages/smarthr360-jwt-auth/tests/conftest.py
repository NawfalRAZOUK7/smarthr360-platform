"""Minimal Django configuration for the package's own test suite.

Most tests here need no settings at all, but anything constructing an
HttpResponse (the read-only middleware returns a JsonResponse) requires
Django to be configured. Configure once, lazily, before any test imports.
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=False,
        DEFAULT_CHARSET="utf-8",
        USE_TZ=True,
        DATABASES={},
        INSTALLED_APPS=[],
    )
    django.setup()
