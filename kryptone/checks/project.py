import re

from kryptone.checks.core import checks_registry
from kryptone.conf import settings

E001 = (
    "Spider or Automater name should be a string. Got {name}"
)

E002 = (
    "Browser name should be either Chrome or Edge"
)

E003 = (
    "MEDIA settings should be a string"
)


E004 = (
    "WAIT_TIME should be an integer. Got {time}"
)

E005 = (
    'WEBHOOK_INTERVAL and WEBHOOK_PAGINATION should be integers'
)

E006 = (
    '{name} cannot be negative integers'
)

E007 = (
    'WAIT_TIME_RANGE should have just two values'
)


@checks_registry.register('webdriver_name')
def check_webdriver():
    allowed_browsers = ['Chrome', 'Edge']
    if settings.WEBDRIVER not in allowed_browsers:
        return [E002]
    return []


@checks_registry.register('wait_time')
def check_wait_time():
    errors = []
    if not isinstance(settings.WAIT_TIME, int):
        errors.append(E004.format(time=settings.WAIT_TIME))

    if settings.WAIT_TIME < 0:
        errors.append(E006.format(name='WAIT_TIME'))

    if len(settings.WAIT_TIME_RANGE) != 2:
        errors.append(E007)

    for i, value in enumerate(settings.WAIT_TIME_RANGE):
        if not isinstance(value, int):
            errors.append(E004.format(time=value))

        if value < 0:
            errors.append(f"WAIT_TIME_RANGE[{i}] cannot be a negative number")

    return errors


@checks_registry.register()
def check_strings():
    errors = []
    if not isinstance(settings.MEDIA_FOLDER, str):
        errors.append([E003])

    if not isinstance(settings.CACHE_FILE_NAME, str):
        errors.append(["CACHE_FILE_NAME should be a string"])

    if not isinstance(settings.EMAIL_HOST, str):
        errors.append(["EMAIL_HOST should be a string"])

    if not isinstance(settings.EMAIL_USE_TLS, bool):
        errors.append(["EMAIL_HOST should be a string"])

    if not isinstance(settings.WEBSITE_LANGUAGE, str):
        errors.append(["WEBSITE_LANGUAGE should be a string"])

    if not isinstance(settings.HEADLESS, bool):
        errors.append(["HEADLESS should be a boolean"])

    if not isinstance(settings.LOAD_IMAGES, bool):
        errors.append(["LOAD_IMAGES should be a boolean"])

    if not isinstance(settings.LOAD_JS, bool):
        errors.append(["LOAD_JS should be a boolean"])

    return []


@checks_registry.register(tag='webhook_intervals')
def check_webkook_interval():
    errors = []
    # TODO: There is a problem checking the webhook interval
    # if (not isinstance(settings.WEBHOOK_INTERVAL, int) or
    #         not isinstance(settings.WEBHOOK_PAGINATION, int)):
    #     errors.append(E005)

    # if settings.WEBHOOK_INTERVAL < 0 or settings.WEBHOOK_PAGINATION < 0:
    #     errors.append(E006.format(
    #         name='WEBHOOK_INTERVAL and WEBHOOK_PAGINATION')
    #     )

    return errors


@checks_registry.register(tag='proxy_ip_address')
def check_proxy_ip():
    errors = []
    # TODO: Implement check for proxy address
    # if settings.PROXY_IP_ADDRESS is not None:
    #     result = re.match(r'^(\d+\.)+(\:\d+)$', settings.PROXY_IP_ADDRESS)
    #     if not result:
    #         return [f"PROXY_IP_ADDRESS is not a valid_urlsalid IP address"]
    return errors
