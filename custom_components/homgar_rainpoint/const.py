from datetime import timedelta

DOMAIN = "homgar_rainpoint"
PLATFORMS = ["sensor"]

CONF_AREA_CODE = "area_code"
CONF_POLL_INTERVAL = "poll_interval"
CONF_APP_CODE = "app_code"
CONF_HOME_ID = "home_id"
CONF_HOME_NAME = "home_name"

APP_CODE_HOMGAR = "1"
APP_CODE_RAINPOINT = "2"

DEFAULT_AREA_CODE = "27"
DEFAULT_POLL_INTERVAL = 120
DEFAULT_APP_CODE = APP_CODE_RAINPOINT
MIN_POLL_INTERVAL = 30

API_BASE_URL = "https://region3.homgarus.com"

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_POLL_INTERVAL)