#!/usr/bin/env python3
"""Rebuild derived previews from the bundled frame masters; Python stdlib only."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--magick', default='magick', help='ImageMagick 7 executable')
    args = parser.parse_args()
    executable = shutil.which(args.magick)
    if not executable:
        parser.error('ImageMagick 7 is required; install it separately or pass --magick PATH')
    for spec in json.loads((ROOT / 'animations.json').read_text()):
        name = spec['name']
        source = ROOT / 'animations' / name
        output = ROOT / 'build' / name
        output.mkdir(parents=True, exist_ok=True)
        frames = [source / f'frame-{i}.png' for i in range(spec['count'])]
        previews = [source / f'preview-{i}.png' for i in range(spec['count'])]
        if not all(p.exists() for p in previews):
            previews = frames
        subprocess.run([executable, *map(str, frames), '+append', str(output / 'strip.png')], check=True)
        # Assemble rows explicitly so a partial final row does not change frame geometry.
        rows = []
        for start in range(0, len(frames), spec['cols']):
            row = output / f'row-{start // spec["cols"]}.png'
            subprocess.run([executable, *map(str, frames[start:start + spec['cols']]), '+append', str(row)], check=True)
            rows.append(row)
        subprocess.run([executable, *map(str, rows), '-append', str(output / 'keyframes.png')], check=True)
        command = [executable]
        for duration, preview in zip(spec['durations'], previews):
            command.extend(['-delay', str(duration // 10), str(preview)])
        subprocess.run([*command, '-loop', '0', str(output / f'{name}.gif')], check=True)
        print(f'{name}: {len(frames)} frames -> build/{name}/')


if __name__ == '__main__':
    main()
