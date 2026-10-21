#!/usr/bin/env python3
"""macOS Godot script launcher: headless checks or hidden GPU captures.

Set FOUNDRY_GODOT_BINARY to the actual Godot binary. GPU scripts must support
FOUNDRY_MANUAL_RENDER=1 when using this launcher. LaunchServices cannot forward
an application's exit status; callers must also reject error logs and require a
fresh validation receipt, as the volume-fish validation wrappers already do.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    binary = Path(os.environ['FOUNDRY_GODOT_BINARY']).resolve()
    assert binary.is_file(), 'Missing real Godot binary'
    args = sys.argv[1:]
    if '--headless' in args or sys.platform != 'darwin':
        return subprocess.call([str(binary), *args])
    assert '--script' in args, 'Background GPU launcher is only for capture scripts'
    app = binary.parents[2]
    assert app.suffix == '.app', 'Expected a macOS Godot app bundle'
    with tempfile.TemporaryDirectory(prefix='foundry-godot-') as folder:
        stdout = Path(folder) / 'stdout.log'
        stderr = Path(folder) / 'stderr.log'
        command = ['/usr/bin/open', '-W', '-g', '-j', '-n', '-a', str(app)]
        for key in ['DOTNET_ROOT', 'PATH']:
            if key in os.environ:
                command += ['--env', key + '=' + os.environ[key]]
        command += ['--env', 'FOUNDRY_MANUAL_RENDER=1', '--stdout', str(stdout),
                    '--stderr', str(stderr), '--args', '--disable-render-loop',
                    '--audio-driver', 'Dummy', *args]
        result = subprocess.run(command, capture_output=True, text=True)
        for path, stream in [(stdout, sys.stdout), (stderr, sys.stderr)]:
            if path.exists():
                stream.write(path.read_text(errors='replace'))
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode


if __name__ == '__main__':
    sys.exit(main())
