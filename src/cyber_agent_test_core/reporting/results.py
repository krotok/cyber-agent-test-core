"""Collision-safe merging of Allure result directories from workers and CI jobs."""

import shutil
from hashlib import sha256
from pathlib import Path


def merge_allure_results(sources: tuple[Path, ...], destination: Path) -> int:
    """Copy result artifacts, preserving distinct files with colliding names."""
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source in sources:
        if not source.exists():
            continue
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                incoming = path.read_bytes()
                if target.read_bytes() == incoming:
                    continue
                suffix = sha256(incoming).hexdigest()[:12]
                target = target.with_name(f"{target.stem}-{suffix}{target.suffix}")
            shutil.copy2(path, target)
            copied += 1
    return copied
