import importlib.util
import io
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('picker', Path(__file__).resolve().parents[1] / 'workflow/session_picker.py')
picker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picker)


class PickerTests(unittest.TestCase):
    def test_search_and_number_select_from_same_stable_snapshot(self):
        rows = [{'id': 'one', 'title': 'Alpha', 'project': '/a', 'status': 'pending'},
                {'id': 'two', 'title': 'Beta', 'project': '/b', 'status': 'update_available'}]
        answers = iter(['/beta', '1'])
        selected = picker.choose(rows, reader=lambda _: next(answers), output=io.StringIO())
        self.assertIs(selected, rows[1])

    def test_exact_id_and_cancel(self):
        rows = [{'id': 'original-id', 'title': 'Name'}]
        self.assertEqual(picker.choose(rows, reader=lambda _: 'original-id', output=io.StringIO()), rows[0])
        self.assertIsNone(picker.choose(rows, reader=lambda _: 'q', output=io.StringIO()))

    def test_untrusted_metadata_cannot_emit_terminal_controls(self):
        output = io.StringIO()
        picker.choose([{'id': 'id', 'title': '\x1b[31m\nInjected'}], reader=lambda _: 'q', output=output)
        self.assertNotIn('\x1b', output.getvalue())
