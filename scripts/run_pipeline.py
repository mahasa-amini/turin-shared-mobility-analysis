"""Run explicitly selected, previously validated stages; no implicit upstream reruns."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def load_config(root=ROOT):
    stages = json.loads((root / 'config/pipeline.json').read_text())
    with (root / 'config/input_manifest.csv').open(newline='') as stream:
        inputs = list(csv.DictReader(stream))
    return stages, inputs


def select_stages(stages, workflow, requested=None):
    allowed = [name for name, spec in stages.items() if spec['workflow'] == workflow]
    requested = allowed if requested is None else requested
    invalid = set(requested) - set(allowed)
    if invalid:
        raise ValueError(f'Unknown stages for {workflow}: {", ".join(sorted(invalid))}')
    # Catalog order is the validated order, regardless of argument order.
    return [name for name in allowed if name in requested]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def preflight(root, stages, inputs, selected, verify_inputs=False):
    """Check supplied inputs and unscheduled upstream output contracts, not schemas."""
    errors = []
    planned = set()
    for name in selected:
        spec = stages[name]
        for script in spec['scripts']:
            if not (root / script).is_file():
                errors.append(f'Missing script: {script}')
        for dep in spec['requires']:
            if dep in planned:
                continue  # Checked again immediately before execution of this stage.
            for path in stages[dep]['outputs']:
                f = root / path
                if not f.is_file() or f.stat().st_size == 0:
                    errors.append(f'{name}: missing intermediate {path}; run {dep} first')
        for item in inputs:
            if item['stage'] != name:
                continue
            f = root / item['path']
            if not f.is_file():
                errors.append(f'{name}: missing input {item["path"]}')
            elif f.stat().st_size != int(item['bytes']):
                errors.append(f'{name}: input size mismatch {item["path"]}')
            elif verify_inputs and digest(f) != item['sha256']:
                errors.append(f'{name}: input SHA-256 mismatch {item["path"]}')
        planned.add(name)
    return list(dict.fromkeys(errors))


def execute(root, stages, inputs, selected, log_dir, verify_inputs=False):
    """Execute with this Python, write per-command logs, stop at first failure."""
    log_dir.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, MPLBACKEND='Agg', MPLCONFIGDIR=str(log_dir / 'matplotlib'))
    records = []
    summary = {'interpreter': sys.executable, 'cwd': str(root), 'stages': selected,
               'commands': records, 'status': 'running'}

    def save():
        (log_dir / 'run.json').write_text(json.dumps(summary, indent=2) + '\n')

    save()
    for name in selected:
        errors = preflight(root, stages, inputs, [name], verify_inputs)
        if errors:
            summary.update(status='preflight_failed', errors=errors)
            save()
            print('\n'.join(errors), file=sys.stderr)
            return 2
        for script in stages[name]['scripts']:
            command = [sys.executable, '-I', '-B', '-u', str(root / script)]
            log = log_dir / f'{len(records) + 1:02d}-{Path(script).stem}.log'
            print(f'Running {name}: {script} -> {log}', flush=True)
            start = time.monotonic()
            try:
                with log.open('w') as stream:
                    result = subprocess.run(command, cwd=root, env=env,
                                            stdout=stream, stderr=subprocess.STDOUT)
                code = result.returncode
            except OSError as exc:
                log.write_text(f'Unable to launch subprocess: {exc}\n')
                code = 1
            except KeyboardInterrupt:
                summary.update(status='interrupted', interrupted_command=command)
                save()
                return 130
            records.append({'stage': name, 'command': command, 'log': log.name,
                            'exit': code, 'seconds': round(time.monotonic() - start, 3)})
            if code:
                summary['status'] = 'failed'
                save()
                return code if code > 0 else 1
            save()
        missing = [path for path in stages[name]['outputs']
                   if not (root / path).is_file() or (root / path).stat().st_size == 0]
        if missing:
            summary.update(status='outputs_missing', errors=missing)
            save()
            return 1
    summary['status'] = 'passed'
    save()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workflow', choices=['scooter', 'figures', 'commuting'])
    parser.add_argument('--stages', nargs='+', help='Explicit stage names; default: all in workflow')
    parser.add_argument('--list', action='store_true', help='List stages without checking inputs')
    parser.add_argument('--dry-run', action='store_true', help='Print commands and preflight; write nothing')
    parser.add_argument('--preflight', action='store_true', help='Check selected plan without execution')
    parser.add_argument('--verify-inputs', action='store_true', help='Also compare supplied input SHA-256 hashes')
    parser.add_argument('--log-dir', type=Path, help='New log directory; must not exist')
    args = parser.parse_args(argv)
    stages, inputs = load_config()
    try:
        selected = select_stages(stages, args.workflow, args.stages)
    except ValueError as exc:
        parser.error(str(exc))
    for name in selected:
        print(f'{name}: ' + ', '.join(stages[name]['scripts']))
        if args.dry_run:
            for script in stages[name]['scripts']:
                print('  ' + repr([sys.executable, '-I', '-B', '-u', str(ROOT / script)]))
    if args.list:
        return 0
    errors = preflight(ROOT, stages, inputs, selected, args.verify_inputs)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 2
    print('Preflight passed (scheduled intermediate outputs checked again at stage boundaries).')
    if args.preflight or args.dry_run:
        return 0
    log_dir = args.log_dir or ROOT / 'outputs/logs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log_dir = log_dir.resolve()
    if log_dir.exists():
        parser.error(f'Log directory already exists: {log_dir}')
    return execute(ROOT, stages, inputs, selected, log_dir, args.verify_inputs)


if __name__ == '__main__':
    raise SystemExit(main())
