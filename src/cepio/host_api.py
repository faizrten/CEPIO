from __future__ import annotations

from . import api as legacy
from .management_remote import build_remote_management_router
from .management_runtime import build_management_service
from .public_api import app


# The hosted CEPIO process exposes two deliberately separate contracts:
# - /api/v1/*: Application Contract for industrial applications and agents;
# - /management/v1/*: authenticated, read-only Management Contract projection.
#
# The standalone `cepio-management` process remains loopback-only. Remote mutation is
# intentionally absent from this host composition.
_management_service = build_management_service(legacy.runtime)
app.include_router(build_remote_management_router(_management_service))
