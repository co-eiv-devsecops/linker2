import os

try:
    import ldclient
    from ldclient import Context
    from ldclient.config import Config
except ImportError:
    ldclient = None
    Context = None
    Config = None


FLAG_ENV_VARS = {
    "custom_alias": "LINKER_ENABLE_CUSTOM_ALIAS",
}

LAUNCHDARKLY_FLAG_KEYS = {
    "custom_alias": "custom-alias",
}

LAUNCHDARKLY_SDK_KEY_ENV = "LAUNCHDARKLY_SDK_KEY"
LAUNCHDARKLY_CONTEXT_KEY_ENV = "LAUNCHDARKLY_CONTEXT_KEY"
DEFAULT_CONTEXT_KEY = "linker-python"
TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
FALSE_VALUES = {"0", "false", "no", "off", "disabled"}
_launchdarkly_client = None
_launchdarkly_sdk_key = None


def parse_bool(value, default=False):
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def local_flag_value(flag_name, environ=os.environ):
    env_var = FLAG_ENV_VARS.get(flag_name)
    if env_var is None:
        return False
    return parse_bool(environ.get(env_var), default=False)


def launchdarkly_context(environ=os.environ):
    context_key = environ.get(LAUNCHDARKLY_CONTEXT_KEY_ENV, DEFAULT_CONTEXT_KEY)
    if Context is None:
        return context_key
    return Context.builder(context_key).name("Linker Python").build()


def get_launchdarkly_client(environ=os.environ):
    global _launchdarkly_client, _launchdarkly_sdk_key

    sdk_key = environ.get(LAUNCHDARKLY_SDK_KEY_ENV)
    if not sdk_key or ldclient is None or Config is None:
        return None

    if _launchdarkly_client is None or _launchdarkly_sdk_key != sdk_key:
        ldclient.set_config(Config(sdk_key))
        _launchdarkly_client = ldclient.get()
        _launchdarkly_sdk_key = sdk_key

    return _launchdarkly_client


def is_enabled(flag_name, environ=os.environ, launchdarkly_client=None):
    default = local_flag_value(flag_name, environ)
    flag_key = LAUNCHDARKLY_FLAG_KEYS.get(flag_name)
    if flag_key is None:
        return False

    client = launchdarkly_client or get_launchdarkly_client(environ)
    if client is None:
        return default

    try:
        return bool(client.variation(flag_key, launchdarkly_context(environ), default))
    except Exception:
        return default
