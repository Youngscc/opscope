"""Return the locked macOS 12 SciPy wheel used after a verified loader failure."""
import platform
from pathlib import Path
import sys
import tomllib

if platform.system() != 'Darwin' or platform.machine() != 'arm64' or sys.version_info[:2] != (3, 11):
    raise SystemExit('compatible wheel fallback is only for macOS arm64 / Python 3.11')
lock = tomllib.loads((Path(__file__).resolve().parents[1] / 'uv.lock').read_text())
package = next(item for item in lock['package'] if item['name'] == 'scipy')
match = next(item for item in package['wheels'] if
             'cp311-cp311-macosx_12_0_arm64.whl' in item['url'])
assert match['hash'].startswith('sha256:')
print(match['url'] + '#sha256=' + match['hash'].split(':', 1)[1])
