import unittest

from api.env import parse_env_value


class ParseEnvValueTests(unittest.TestCase):
    def test_strips_matching_double_quotes_from_env_values(self) -> None:
        self.assertEqual(parse_env_value('"vercel_blob_rw_store_secret"'), "vercel_blob_rw_store_secret")

    def test_strips_matching_single_quotes_from_env_values(self) -> None:
        self.assertEqual(parse_env_value("'http://localhost:3000'"), "http://localhost:3000")

    def test_preserves_unquoted_values(self) -> None:
        self.assertEqual(parse_env_value("plain-value"), "plain-value")


if __name__ == "__main__":
    unittest.main()
