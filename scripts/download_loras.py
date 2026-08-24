from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Set, Tuple
from urllib.request import Request, urlopen


_ALIAS = re.compile(r"^[A-Za-z0-9._-]+$")
_SHA256 = re.compile(r"^[A-Fa-f0-9]{64}$")
_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class LoraManifestEntry:
    alias: str
    url: str
    sha256: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "LoraManifestEntry":
        alias = _required_string(data, "alias")
        url = _required_string(data, "url")
        sha256 = _required_string(data, "sha256").lower()

        if _ALIAS.fullmatch(alias) is None:
            raise ValueError(f"Invalid LoRA alias '{alias}'")
        if not url.startswith("https://"):
            raise ValueError(f"LoRA '{alias}' must use an HTTPS download URL")
        if _SHA256.fullmatch(sha256) is None:
            raise ValueError(f"LoRA '{alias}' has an invalid SHA-256")
        return cls(alias=alias, url=url, sha256=sha256)


def _required_string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"LoRA manifest field '{key}' must be a non-empty string")
    return value.strip()


def load_manifest(path: Path) -> Tuple[LoraManifestEntry, ...]:
    with path.open("r", encoding="utf-8") as handle:
        payload: object = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError("LoRA manifest must be a JSON array")

    entries: List[LoraManifestEntry] = []
    aliases: Set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each LoRA manifest entry must be an object")
        entry = LoraManifestEntry.from_mapping(item)
        key = entry.alias.casefold()
        if key in aliases:
            raise ValueError(f"Duplicate LoRA alias '{entry.alias}'")
        aliases.add(key)
        entries.append(entry)
    return tuple(entries)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_lora(entry: LoraManifestEntry, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{entry.alias}.safetensors"
    if target.is_file() and file_sha256(target) == entry.sha256:
        return target

    temporary = target.with_suffix(".safetensors.part")
    completed = False
    try:
        request = Request(
            entry.url, headers={"User-Agent": "e-dream-deforum-builder/1.0"}
        )
        with urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
            while chunk := response.read(_CHUNK_SIZE):
                handle.write(chunk)

        actual_sha256 = file_sha256(temporary)
        if actual_sha256 != entry.sha256:
            raise ValueError(
                f"SHA-256 mismatch for '{entry.alias}': expected {entry.sha256}, got {actual_sha256}"
            )
        os.replace(temporary, target)
        completed = True
        return target
    finally:
        if not completed and temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    for entry in load_manifest(args.manifest):
        path = download_lora(entry, args.output)
        print(f"Installed LoRA '{entry.alias}' at {path}")


if __name__ == "__main__":
    main()
