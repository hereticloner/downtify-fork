from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / 'mirror' / 'entrypoint.sh'


def _fake_bin(
    tmp_path: Path, *, ready_after: int
) -> tuple[dict[str, str], Path, Path]:
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    log = tmp_path / 'calls.log'
    count = tmp_path / 'info.count'
    (bin_dir / 'pulseaudio').write_text(
        '#!/bin/sh\necho "pulseaudio $*" >> "$CALL_LOG"\nexit 0\n',
        encoding='utf-8',
    )
    (bin_dir / 'pactl').write_text(
        '#!/bin/sh\n'
        'echo "pactl $*" >> "$CALL_LOG"\n'
        'if [ "$1" = info ]; then\n'
        '  n=0\n'
        '  [ ! -f "$INFO_COUNT" ] || n=$(cat "$INFO_COUNT")\n'
        '  n=$((n + 1))\n'
        '  echo "$n" > "$INFO_COUNT"\n'
        '  [ "$n" -ge "$INFO_READY_AFTER" ]\n'
        '  exit $?\n'
        'fi\n'
        'exit 0\n',
        encoding='utf-8',
    )
    (bin_dir / 'soloist').write_text(
        '#!/bin/sh\necho "soloist $*" >> "$CALL_LOG"\nexit 0\n',
        encoding='utf-8',
    )
    for path in bin_dir.iterdir():
        path.chmod(0o755)
    env = {
        **os.environ,
        'PATH': f'{bin_dir}:/usr/bin:/bin',
        'CALL_LOG': str(log),
        'INFO_COUNT': str(count),
        'INFO_READY_AFTER': str(ready_after),
        'SOLOIST_DEVICE_NAME': 'Downtify Mirror',
        'SOLOIST_API_KEY': 'test-key',
    }
    return env, log, count


def test_entrypoint_waits_for_audio_and_sets_null_sink_before_soloist(
    tmp_path: Path,
) -> None:
    env, log, count = _fake_bin(tmp_path, ready_after=3)

    result = subprocess.run(
        ['sh', str(ENTRYPOINT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert count.exists(), 'entrypoint never checked PulseAudio readiness'
    calls = log.read_text(encoding='utf-8').splitlines()
    assert int(count.read_text(encoding='utf-8').strip()) >= 3
    assert calls[0].startswith('pulseaudio --start')
    assert calls[-1].startswith('soloist --device-name Downtify Mirror')
    assert 'pactl load-module module-null-sink sink_name=mirror' in calls
    assert 'pactl set-default-sink mirror' in calls
    assert calls.index('pactl set-default-sink mirror') < len(calls) - 1


def test_entrypoint_fails_instead_of_starting_soloist_without_audio(
    tmp_path: Path,
) -> None:
    env, log, _count = _fake_bin(tmp_path, ready_after=999)

    result = subprocess.run(
        ['sh', str(ENTRYPOINT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode != 0
    assert 'PulseAudio' in result.stderr
    calls = log.read_text(encoding='utf-8').splitlines()
    assert not any(call.startswith('soloist ') for call in calls)
