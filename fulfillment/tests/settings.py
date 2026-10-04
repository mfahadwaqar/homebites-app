from config.settings import *  # noqa: F401,F403

INSTALLED_APPS = [
    app for app in INSTALLED_APPS if app not in {"sellers", "catalog", "orders"}
]
if "fulfillment" not in INSTALLED_APPS:
    INSTALLED_APPS.append("fulfillment")

DATABASES["default"]["TEST"] = {"NAME": "test_homebites_fulfillment"}
