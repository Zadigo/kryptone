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


@checks_registry.register('spider_names')
def check_spiders():
    errors = []
    for item in settings.SPIDERS:
        if not isinstance(item, str):
            errors.append(E001.format(name=item))

    for item in settings.AUTOMATERS:
        if not isinstance(item, str):
            errors.append(E001.format(name=item))

    return errors


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
        errors.append(E004.format(time=item))

    for item in settings.WAIT_TIME_RANGE:
        if not isinstance(item, int):
            errors.append(E004.format(time=item))

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

    return []
