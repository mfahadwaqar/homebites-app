from copy import deepcopy

from config.settings import *  # noqa: F403

DATABASES = deepcopy(DATABASES)
DATABASES["default"]["TEST"] = {"NAME": "test_homebites_sellers"}
ROOT_URLCONF = "sellers.test_urls"
