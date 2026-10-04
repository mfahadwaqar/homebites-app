from config.settings import *  # noqa: F401,F403


INSTALLED_APPS = [*INSTALLED_APPS, "payments"] if "payments" not in INSTALLED_APPS else INSTALLED_APPS
DATABASES["default"]["TEST"] = {"NAME": "test_homebites_payments"}
