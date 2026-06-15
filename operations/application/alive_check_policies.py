from django.conf import settings


class AliveCheckPhotoPolicy:
    """Single source of truth for alive check selfie requirement."""

    @classmethod
    def is_required(cls):
        return getattr(settings, "ALIVE_CHECK_REQUIRE_SELFIE", False)
