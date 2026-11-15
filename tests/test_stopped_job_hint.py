import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.path.isdir('/proc') and shutil.which('script') and shutil.which('sleep'),
                     'requires Linux proc and a pseudo-terminal')
class StoppedJobHintTests(unittest.TestCase):
    def test_stopped_job_is_only_reported_and_not_resumed(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'codex'
            fake.symlink_to(shutil.which('sleep'))
            launcher = ROOT / 'workflow/code-shell.bash'
            # Wait until the child has exec'd before stopping it, and always
            # clean up this test-owned process after observing its state.
            command = f'''source {shlex.quote(str(launcher))}
{shlex.quote(str(fake))} 20 &
pid=$!
trap 'kill -CONT "$pid" 2>/dev/null; kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null' EXIT
for i in {{1..100}}; do [[ $(cat /proc/$pid/comm 2>/dev/null) == codex ]] && break; sleep .02; done
[[ $(cat /proc/$pid/comm) == codex ]] || exit 3
kill -STOP "$pid"
for i in {{1..100}}; do [[ $(awk '{{print $3}}' /proc/$pid/stat) == T ]] && break; sleep .02; done
_codex_workbench_stopped_job_hint
[[ $(awk '{{print $3}}' /proc/$pid/stat) == T ]] || exit 4
'''
            result = subprocess.run(
                ['script', '-q', '-e', '-c', 'bash --noprofile --norc -ic ' + shlex.quote(command), '/dev/null'],
                text=True, capture_output=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('A stopped Codex job is listed in this shell', result.stdout)
            self.assertIn('does not establish who owns a conversation', result.stdout)


if __name__ == '__main__':
    unittest.main()
