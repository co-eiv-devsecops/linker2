import unittest

from feature_flags import is_enabled, local_flag_value, parse_bool


class FakeLaunchDarklyClient:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.calls = []

    def variation(self, flag_key, context, default):
        self.calls.append((flag_key, context, default))
        if self.error:
            raise self.error
        return self.value


class FeatureFlagsTest(unittest.TestCase):
    def test_parse_bool_accepts_enabled_values(self):
        for value in ("1", "true", "TRUE", "yes", "on", "enabled"):
            with self.subTest(value=value):
                self.assertTrue(parse_bool(value))

    def test_parse_bool_accepts_disabled_values(self):
        for value in ("0", "false", "FALSE", "no", "off", "disabled"):
            with self.subTest(value=value):
                self.assertFalse(parse_bool(value, default=True))

    def test_parse_bool_uses_default_for_missing_or_unknown_values(self):
        self.assertTrue(parse_bool(None, default=True))
        self.assertFalse(parse_bool("unexpected", default=False))

    def test_is_enabled_reads_known_flag_from_environment(self):
        environ = {"LINKER_ENABLE_CUSTOM_ALIAS": "true"}

        self.assertTrue(is_enabled("custom_alias", environ))

    def test_is_enabled_returns_false_for_unknown_flags(self):
        self.assertFalse(is_enabled("unknown", {"UNKNOWN": "true"}))

    def test_local_flag_value_reads_environment_fallback(self):
        environ = {"LINKER_ENABLE_CUSTOM_ALIAS": "true"}

        self.assertTrue(local_flag_value("custom_alias", environ))

    def test_is_enabled_reads_launchdarkly_variation_when_client_is_available(self):
        client = FakeLaunchDarklyClient(value=True)

        self.assertTrue(is_enabled("custom_alias", {}, launchdarkly_client=client))
        self.assertEqual(client.calls[0][0], "custom-alias")

    def test_is_enabled_uses_local_default_when_launchdarkly_fails(self):
        client = FakeLaunchDarklyClient(error=RuntimeError("LaunchDarkly unavailable"))
        environ = {"LINKER_ENABLE_CUSTOM_ALIAS": "true"}

        self.assertTrue(is_enabled("custom_alias", environ, launchdarkly_client=client))


if __name__ == "__main__":
    unittest.main()
