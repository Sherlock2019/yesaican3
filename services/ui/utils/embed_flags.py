"""Cross-module flags for pages that are also embedded elsewhere.

``services/ui/pages/how_can_ai_help.py`` is both a page in its own right and
the source of the pain-point capture panel that the home page renders. When
app.py imports it for the panel, the page's own bootstrap — set_page_config,
the solution form, the challenge feed — must not run.

app.py sets ``CAPTURE_EMBEDDED = True`` *before* importing that module, and the
module's bootstrap is guarded on it. A module attribute rather than an
environment variable because both run in the same process.
"""

from __future__ import annotations

__all__ = ["CAPTURE_EMBEDDED", "PROFILES_EMBEDDED"]

CAPTURE_EMBEDDED = False

# Same idea for the People & Skills page: Community renders its Directory,
# Create/Edit Profile and Search tabs, so that page's own chrome and tab strip
# must not run when it is imported for those functions.
PROFILES_EMBEDDED = False
