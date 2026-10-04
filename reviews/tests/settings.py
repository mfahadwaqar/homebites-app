from config.settings import *  # noqa: F403

if "reviews" not in INSTALLED_APPS:
    INSTALLED_APPS = [*INSTALLED_APPS, "reviews"]
