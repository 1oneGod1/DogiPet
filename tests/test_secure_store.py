import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from secure_store import SecureStore


class SecureStoreTests(unittest.TestCase):
    def test_credentials_are_not_written_as_plaintext(self):
        def protect(data):
            return b"DOGI" + data[::-1]

        def unprotect(data):
            self.assertTrue(data.startswith(b"DOGI"))
            return data[4:][::-1]

        with TemporaryDirectory() as folder:
            path = Path(folder) / "credentials.bin"
            store = SecureStore(path, protect=protect, unprotect=unprotect)
            store.set("openai_api_key", "sk-super-secret")

            self.assertNotIn(b"sk-super-secret", path.read_bytes())
            self.assertEqual(store.get("openai_api_key"), "sk-super-secret")
            store.delete("openai_api_key")
            self.assertIsNone(store.get("openai_api_key"))


if __name__ == "__main__":
    unittest.main()
