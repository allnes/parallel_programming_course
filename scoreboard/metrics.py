"""Scoreboard calculations: points, penalties, performance metrics."""

from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from assign_variant import assign_variant


@dataclass
class DeadlineInfo:
    label: str
    due: Optional[datetime]


# ---------------------------------------------------------------------------
# Points & penalties
# ---------------------------------------------------------------------------


def get_solution_points_and_style(
    task_type: str, status: Optional[str], points_info: dict
) -> tuple[int, str]:
    """Return (points, css_inline_style) for a task implementation.

    - "done"  → full points, green background
    - "disabled" → full points, pink background
    - anything else → 0 points, no style
    """
    threads_tasks = (points_info.get("threads", {}) or {}).get("tasks", [])
    max_points = None
    for task in threads_tasks:
        if str(task.get("name")) == task_type:
            try:
                max_points = int(task.get("S", 0))
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError("Invalid points config") from exc
            break
    if max_points is None:
        if task_type == "mpi":
            return 0, ""
        raise KeyError(f"Unknown task type: {task_type}")

    if status == "done":
        return max_points, "background-color: #d8f5d0;"
    if status == "disabled":
        return max_points, "background-color: #ffd8e1;"
    return 0, ""


def check_plagiarism_and_calculate_penalty(
    task_dir: str,
    task_type: str,
    sol_points: float,
    copying_cfg: dict,
    points_info: dict,
    semester: str,
) -> tuple[bool, float]:
    """Return (is_plagiarised, penalty_points)."""
    clean_name = task_dir.removesuffix("_disabled")
    semester_cfg = (
        copying_cfg.get(semester, {}) if isinstance(copying_cfg, dict) else {}
    )
    mapping = semester_cfg.get("copying") or semester_cfg.get("plagiarism") or {}
    flagged = set(mapping.get(task_type, []) or [])
    is_cheated = task_dir in flagged or clean_name in flagged

    try:
        coeff = float((points_info.get("copying", {}) or {}).get("coefficient", 0.0))
    except Exception:
        coeff = 0.0

    penalty = -coeff * sol_points if is_cheated and sol_points else 0.0
    return is_cheated, penalty


def calculate_deadline_penalty(
    task_dir: str,
    task_type: str,
    status: Optional[str],
    deadline: Optional[datetime],
    tasks_root: Path,
) -> float:
    if status != "done" or deadline is None:
        return 0.0
    target_dir = tasks_root / task_dir
    if task_dir.endswith("_disabled") and not target_dir.exists():
        target_dir = tasks_root / task_dir.removesuffix("_disabled")
    impl_dir = target_dir / task_type
    git_cmd = ["git", "log", "-1", "--format=%ct", str(impl_dir)]
    try:
        result = subprocess.run(git_cmd, capture_output=True, text=True, check=False)
        ts = result.stdout.strip()
        if ts.isdigit():
            commit_dt = datetime.fromtimestamp(int(ts))
            days_late = (commit_dt - deadline).days
            return float(-days_late) if days_late > 0 else 0.0
    except Exception:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------


def calculate_performance_metrics(
    perf_val: Optional[str | float],
    eff_num_proc: int,
    task_type: str = "par",
    seq_val: Optional[str | float] = None,
) -> tuple[str, str]:
    """Compute acceleration and efficiency.

    perf_val is either a ratio (T_par / T_seq) or absolute time when seq_val is provided.
    Returns (acceleration, efficiency) as strings (efficiency is a fraction, not %); missing/invalid → "—".
    """
    invalid = (None, "", "?", "N/A")
    if perf_val in invalid or eff_num_proc <= 0:
        return "—", "—"
    try:
        if seq_val not in invalid and seq_val is not None:
            seq_t = float(seq_val)
            par_t = float(perf_val)
            if seq_t <= 0 or par_t <= 0:
                return "—", "—"
            speedup = seq_t / par_t
        else:
            ratio = float(perf_val)
            if ratio <= 0 or math.isinf(ratio) or math.isnan(ratio):
                return "—", "—"
            speedup = 1.0 / ratio
        if task_type == "seq":
            return "1.00", "—"
        acceleration = f"{speedup:.2f}"
        efficiency_val = speedup / eff_num_proc
        efficiency = f"{efficiency_val:.2f}"
        return acceleration, efficiency
    except Exception:
        return "—", "—"


EFFICIENCY_SCALE = [
    (0.50, 1.0),
    (0.45, 0.9),
    (0.42, 0.8),
    (0.40, 0.7),
    (0.37, 0.6),
    (0.35, 0.5),
    (0.32, 0.4),
    (0.30, 0.3),
    (0.27, 0.2),
    (0.25, 0.1),
]


def calc_perf_points_from_efficiency(
    efficiency_value: Optional[float], max_points: int
) -> float:
    if efficiency_value is None:
        return 0.0
    percent = 0.0
    for threshold, pct in EFFICIENCY_SCALE:
        if efficiency_value >= threshold:
            percent = pct
            break
    points = max_points * percent if max_points > 0 else 0.0
    return round(points, 2)


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------


def compute_variant_threads(student: dict, repo_salt: str, vmax: int) -> str:
    if not student:
        return "?"
    try:
        vidx = assign_variant(
            surname=student.get("last_name", ""),
            name=student.get("first_name", ""),
            patronymic=student.get("middle_name", ""),
            group=student.get("group_number", ""),
            repo=repo_salt,
            num_variants=vmax,
        )
        return str(vidx + 1)
    except Exception:
        return "?"


def compute_variants_processes(student: dict, repo_salt: str, vmaxes: list[int]) -> str:
    if not student:
        return "?"
    rendered: list[str] = []
    for idx, vmax in enumerate(vmaxes, start=1):
        try:
            vidx = assign_variant(
                surname=student.get("last_name", ""),
                name=student.get("first_name", ""),
                patronymic=student.get("middle_name", ""),
                group=student.get("group_number", ""),
                repo=f"{repo_salt}/processes/task-{idx}",
                num_variants=vmax,
            )
            rendered.append(str(vidx + 1))
        except Exception:
            rendered.append("?")
    return "<br/>".join(rendered)


__all__ = [
    "DeadlineInfo",
    "get_solution_points_and_style",
    "check_plagiarism_and_calculate_penalty",
    "calculate_deadline_penalty",
    "calculate_performance_metrics",
    "calc_perf_points_from_efficiency",
    "compute_variant_threads",
    "compute_variants_processes",
]
