import unittest

from feature_flags import is_enabled, parse_bool


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


if __name__ == "__main__":
    unittest.main()
