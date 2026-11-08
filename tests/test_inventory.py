import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('inventory', Path(__file__).resolve().parents[1] / 'skills/project-bootstrap/scripts/inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_config_values_and_credentials_are_not_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config.toml').write_text('[mcp_servers.example]\ncommand="SECRET_COMMAND"\nenv={TOKEN="SECRET_TOKEN"}\n')
            result = inventory.read_config(root)
            self.assertEqual(result['mcp_server_names'], ['example'])
            self.assertNotIn('SECRET', str(result))

    def test_default_inventory_does_not_execute_tools(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(inventory.subprocess, 'run') as run:
            report = inventory.inventory(Path(directory), Path(directory))
            run.assert_not_called()
            self.assertEqual(report['probes'], {})

    def test_broken_optional_probe_is_not_a_success(self):
        with patch.object(inventory.subprocess, 'run', side_effect=FileNotFoundError):
            self.assertEqual(inventory.probe(['missing'])['status'], 'unavailable')

    def test_wrong_section_type_does_not_abort_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config.toml').write_text('mcp_servers = true\n')
            result = inventory.inventory(root, root)
            self.assertEqual(result['user_config']['status'], 'invalid_section_types')
            self.assertIn('python3', result['tools'])

    def test_invalid_config_is_reported_without_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config.toml').write_text('secret = [ malformed')
            self.assertEqual(inventory.read_config(root)['status'], 'unreadable_or_invalid')


if __name__ == '__main__':
    unittest.main()
