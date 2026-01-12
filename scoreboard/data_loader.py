"""Data loading helpers for the scoreboard generator.

This module is responsible for reading JSON configs, discovering task
folders on disk, and loading auxiliary data such as benchmark results
and student metadata.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
TASKS_DIR = SCRIPT_DIR.parent / "tasks"
DATA_DIR = SCRIPT_DIR / "data"


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data or {}


def load_points_info() -> dict:
    return _load_json(DATA_DIR / "points-info.json")


def load_copying_config() -> dict:
    return _load_json(DATA_DIR / "copying.json")


def load_deadline_shifts() -> dict:
    path = DATA_DIR / "deadlines.json"
    if not path.exists():
        return {"threads": {}, "processes": {}}
    return _load_json(path)


# ---------------------------------------------------------------------------
# Task discovery and student metadata
# ---------------------------------------------------------------------------


def discover_tasks(
    tasks_dir: Path, task_types: Iterable[str]
) -> dict[str, dict[str, str]]:
    """Return mapping task_dir -> {task_type: status}.

    Status is "done" when the implementation subfolder exists, "disabled"
    when the directory name ends with ``_disabled``.
    """
    directories: dict[str, dict[str, str]] = defaultdict(dict)
    if not tasks_dir.exists():
        return {}

    for task_dir in tasks_dir.iterdir():
        if not task_dir.is_dir() or task_dir.name == "common":
            continue
        raw_name = task_dir.name
        clean_name = raw_name.removesuffix("_disabled")
        status_value = "disabled" if raw_name.endswith("_disabled") else "done"
        for task_type in task_types:
            impl_dir = task_dir / task_type
            if impl_dir.exists() and impl_dir.is_dir():
                directories[clean_name][task_type] = status_value
    return directories


def load_student_info(task_dir: Path) -> dict | None:
    info_path = task_dir / "info.json"
    if not info_path.exists():
        return None
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("student", {})
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to parse %s: %s", info_path, exc)
        return None


# ---------------------------------------------------------------------------
# Performance results (Google Benchmark JSON)
# ---------------------------------------------------------------------------


def _time_unit_factor(unit: str) -> float:
    if unit == "ns":
        return 1e-9
    if unit == "us":
        return 1e-6
    if unit == "ms":
        return 1e-3
    return 1.0


def load_benchmark_json(
    perf_json_path: Path, task_hints: list[str] | None = None
) -> tuple[dict[str, dict], dict[str, str]]:
    """Parse Google Benchmark JSON into perf map: task -> {impl -> time_sec}.

    Also collects task types reported in benchmark names.
    The benchmark name pattern expected: ``task_run_<type>:<task_dir>:<impl>...``
    """
    if not perf_json_path.exists():
        return {}, {}

    try:
        with open(perf_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.warning("Failed to parse benchmark JSON %s: %s", perf_json_path, exc)
        return {}, {}

    benchmarks = data.get("benchmarks", []) or []
    perf: dict[str, dict] = {}
    types: dict[str, str] = {}

    task_hints = task_hints or []
    impl_tokens = ("seq", "omp", "tbb", "stl", "all", "mpi")

    for bench in benchmarks:
        name = bench.get("name", "")
        if not isinstance(name, str):
            continue
        name = name.split("/", 1)[0]  # drop JSON-added suffixes
        if not name.startswith("task_run_"):
            continue
        payload = name.removeprefix("task_run_")
        segments = payload.split(":")
        if len(segments) < 3:
            continue
        tasks_type, task_dir, impl_status = segments[0], segments[1], segments[2]
        impl = None
        for tok in impl_tokens:
            if impl_status.startswith(tok):
                impl = tok
                break
        if impl is None:
            continue
        if task_hints and task_dir not in task_hints:
            continue

        real_time = bench.get("real_time")
        unit = bench.get("time_unit", "ns")
        if real_time is None:
            continue
        try:
            time_sec = float(real_time) * _time_unit_factor(str(unit))
        except Exception:
            continue

        perf.setdefault(task_dir, {})[impl] = min(
            time_sec, perf.get(task_dir, {}).get(impl, time_sec)
        )
        types.setdefault(task_dir, tasks_type)

    return perf, types


__all__ = [
    "SCRIPT_DIR",
    "TASKS_DIR",
    "DATA_DIR",
    "discover_tasks",
    "load_points_info",
    "load_copying_config",
    "load_deadline_shifts",
    "load_student_info",
    "load_benchmark_json",
]
