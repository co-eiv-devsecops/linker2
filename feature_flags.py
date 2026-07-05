import os


FLAG_ENV_VARS = {
    "custom_alias": "LINKER_ENABLE_CUSTOM_ALIAS",
}

TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def parse_bool(value, default=False):
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def is_enabled(flag_name, environ=os.environ):
    env_var = FLAG_ENV_VARS.get(flag_name)
    if env_var is None:
        return False
    return parse_bool(environ.get(env_var), default=False)
