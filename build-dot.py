#!/usr/bin/env python3
"""Build the data-only Vanilla sprite atlas for Codex Dot v1."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
CELL = (192, 208)
ROWS = [
    ("idle", list(range(6))),
    ("running-right", list(range(8))),
    ("running-left", list(range(8))),
    ("waving", list(range(4))),
    ("jumping", [1, 2, 4, 5, 6]),
    ("failed", list(range(8))),
    ("waiting", list(range(6))),
    ("running", list(range(6))),
    ("review", list(range(6))),
]
EYES_X = [299, 302, 302, 312, 301, 300, 307, 313]
EYES_Y = [220, 220, 220, 220, 218, 218, 218, 218]
BOB = [0, 3, 0, -4]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--magick", default="magick", help="ImageMagick 7 executable")
    args = parser.parse_args()
    magick = shutil.which(args.magick)
    if not magick:
        parser.error("ImageMagick 7 is required; pass --magick PATH if needed")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    sources = set()
    rows = []
    with tempfile.TemporaryDirectory(prefix="vanilla-dot-") as directory:
        temp = Path(directory)

        def render(*arguments):
            subprocess.run([magick, *map(str, arguments)], check=True)

        # Recreate the approved run alignment without its preview background.
        # Preserve original alpha; keying white would damage the character.
        original = ROOT / "sources/running-right.png"
        sources.add(original)
        for index in range(8):
            x = 204 - EYES_X[index] * 0.58
            y = 135 + BOB[index % 4] - EYES_Y[index] * 0.58
            right = temp / f"right-{index}.png"
            render(original, "-crop", f"384x512+{index % 4 * 384}+{index // 4 * 512}",
                   "+repage", "-alpha", "on", "-virtual-pixel", "transparent",
                   "-define", "distort:viewport=288x320+0+0", "-distort",
                   "AffineProjection", f"0.58,0,0,0.58,{x},{y}", "+repage",
                   "-resize", "192x208", "-gravity", "center", "-background", "none",
                   "-extent", "192x208", "-strip", f"PNG32:{right}")
            render(right, "-flop", "-strip", "PNG32:" + str(temp / ("left-%d.png" % index)))

        blank = temp / "blank.png"
        render("-size", "192x208", "xc:none", "-strip", f"PNG32:{blank}")
        row_images = []
        for row_index, (name, indices) in enumerate(ROWS):
            frames = []
            for index in indices:
                if name == "running-right":
                    frame = temp / f"right-{index}.png"
                elif name == "running-left":
                    frame = temp / f"left-{index}.png"
                else:
                    frame = ROOT / "animations" / name / f"frame-{index}.png"
                    sources.add(frame)
                frames.append(frame)
            row = temp / f"row-{row_index}.png"
            render(*frames, *([blank] * (8 - len(frames))), "+append", "-strip", f"PNG32:{row}")
            row_images.append(row)
            rows.append({"row": row_index, "state": name, "count": len(indices),
                         "source_indices_zero_based": indices})
        atlas = output / "vanilla-dot-v1.png"
        render(*row_images, "-append", "-strip", f"PNG32:{atlas}")
    manifest = {
        "spriteVersionNumber": 1,
        "atlas": {"path": atlas.name, "width": 1536, "height": 1872,
                  "columns": 8, "cell": list(CELL), "sha256": sha256(atlas),
                  "bytes": atlas.stat().st_size},
        "rows": rows,
        "sources": [{"path": str(p.relative_to(ROOT)), "sha256": sha256(p)}
                    for p in sorted(sources)],
        "run_transform": {"crop": [384, 512], "preview_canvas": [288, 320],
                          "scale": 0.58, "eye_anchor": [204, 135],
                          "eyes_x": EYES_X, "eyes_y": EYES_Y, "bob": BOB,
                          "fit_canvas": list(CELL), "left": "mirror of right"},
        "timing": "Controlled by the installed Codex runtime, not this PNG.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"dist/{atlas.name}: 1536x1872 RGBA, {atlas.stat().st_size} bytes")


if __name__ == "__main__":
    main()
