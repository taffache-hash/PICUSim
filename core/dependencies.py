"""Dependency audit helpers for PDT modules (v0.27)."""
from __future__ import annotations
from dataclasses import fields
from typing import Iterable, Dict, List, Tuple
from .bus import BusState

BUS_KEYS = {f.name for f in fields(BusState)}


def collect_module_io(modules: Iterable) -> dict:
    records = {}
    for m in modules:
        records[m.name] = {
            "reads": list(getattr(m, "input_keys", [])),
            "writes": list(getattr(m, "output_keys", [])),
        }
    return records


def audit_module_dependencies(modules: Iterable) -> dict:
    records = collect_module_io(modules)
    writers: Dict[str, List[str]] = {}
    for mod, io in records.items():
        for key in io["writes"]:
            writers.setdefault(key, []).append(mod)
    missing_bus_keys: List[Tuple[str, str, str]] = []
    orphan_reads: List[Tuple[str, str]] = []
    for mod, io in records.items():
        for key in io["reads"]:
            if key not in BUS_KEYS:
                missing_bus_keys.append((mod, "read", key))
            # bus defaults are valid producers for baseline fields; record only for documentation.
            if key not in writers and key in BUS_KEYS:
                orphan_reads.append((mod, key))
        for key in io["writes"]:
            if key not in BUS_KEYS:
                missing_bus_keys.append((mod, "write", key))
    duplicate_writers = {k: v for k, v in writers.items() if len(v) > 1}
    return {
        "records": records,
        "missing_bus_keys": missing_bus_keys,
        "orphan_reads": orphan_reads,
        "duplicate_writers": duplicate_writers,
    }
