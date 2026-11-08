import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('hub', Path(__file__).resolve().parents[1] / 'workflow/coordinator.py')
hub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hub)


class CoordinatorTests(unittest.TestCase):
    def test_static_configuration_does_not_execute_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.claude').mkdir()
            (home / '.claude/coordinator.env').write_text('export COORDINATOR_HUB_PRIMARY="https://hub.example/base"\nCOORDINATOR_HUB_TOKEN="literal"\nCOORDINATOR_TOKEN=$(touch bad)\n')
            endpoint, token, source = hub.configuration(home, {})
            self.assertEqual(endpoint, 'https://hub.example/base')
            self.assertEqual(token, 'literal')
            self.assertFalse((home / 'bad').exists())

    def test_modern_config_wins_without_mixing_file_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for name in ('.claude', '.coordinator'):
                (home / name).mkdir()
            (home / '.claude/coordinator.env').write_text('COORDINATOR_TOKEN=old\n')
            (home / '.coordinator/coordinator.env').write_text('COORDINATOR_HUB_PRIMARY=https://new.example\n')
            self.assertIsNone(hub.configuration(home, {})[1])

    def test_bot_credential_precedes_hub_admin_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            _, token, _ = hub.configuration(Path(directory), {
                'COORDINATOR_HUB_TOKEN': 'admin', 'COORDINATOR_BOT_TOKEN': 'bot'})
            self.assertEqual(token, 'bot')

    def test_both_supported_search_envelopes(self):
        for payload in ([{'id': 1}], {'results': [{'id': 1}]}, {'articles': [{'id': 1}]}):
            self.assertEqual(hub.articles(payload), [{'id': 1}])

    def test_redirect_never_forwards_bearer(self):
        with self.assertRaises(hub.HubError):
            hub.NoRedirect().redirect_request(None, None, None, None, None, None)

    def test_embedded_credentials_and_public_cleartext_rejected(self):
        with self.assertRaises(hub.HubError):
            hub.validate_endpoint('https://user:secret@hub.example')
        with patch.object(hub.socket, 'getaddrinfo', return_value=[(None, None, None, None, ('8.8.8.8', 80))]):
            with self.assertRaises(hub.HubError):
                hub.validate_endpoint('http://public.example')

    def test_unrecognized_search_response_is_not_verified(self):
        with self.assertRaises(hub.HubError):
            hub.articles({'error': 'access denied'})


if __name__ == '__main__':
    unittest.main()
