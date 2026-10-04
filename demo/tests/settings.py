from config.settings import *  # noqa: F403

if "demo" not in INSTALLED_APPS:
    INSTALLED_APPS = [*INSTALLED_APPS, "demo"]
