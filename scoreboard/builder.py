"""Build scoreboard rows for threads and processes."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List

from data_loader import TASKS_DIR, load_student_info
from metrics import (
    DeadlineInfo,
    calc_perf_points_from_efficiency,
    calculate_deadline_penalty,
    calculate_performance_metrics,
    check_plagiarism_and_calculate_penalty,
    compute_variant_threads,
    compute_variants_processes,
    get_solution_points_and_style,
)

THREAD_TASK_TYPES = ["seq", "omp", "tbb", "stl", "all"]


@dataclass
class ThreadsRow:
    name: str
    variant: str
    cells: Dict[str, dict]
    total: float
    student: dict


@dataclass
class ProcessesRow:
    name: str
    variant: str
    groups: List[dict]
    r_values: List[int]
    total: float
    student: dict


# ---------------------------------------------------------------------------
# Deadlines helpers
# ---------------------------------------------------------------------------


def _abbr(d: date) -> str:
    return f"{d.day} {calendar.month_abbr[d.month]}"


def _evenly_spaced_dates(n: int, start: date, end: date) -> list[date]:
    if n <= 1:
        return [end]
    total = (end - start).days
    step = total / n
    return [start + timedelta(days=int(round(step * (i + 1)))) for i in range(n)]


def compute_threads_deadlines(shifts: dict) -> dict[str, DeadlineInfo]:
    today = datetime.now().date()
    year = today.year if today.month <= 5 else today.year + 1
    start = date(year, 2, 1)
    end = date(year, 5, 15)
    base_dates = _evenly_spaced_dates(len(THREAD_TASK_TYPES), start, end)
    result: dict[str, DeadlineInfo] = {}
    for task, base in zip(THREAD_TASK_TYPES, base_dates):
        shift = shifts.get(task, 0)
        label = None
        if isinstance(shift, int):
            due_date = base + timedelta(days=shift)
            due_dt = datetime.combine(
                due_date,
                datetime.max.time().replace(
                    hour=23, minute=59, second=0, microsecond=0
                ),
            )
            label = _abbr(due_date)
        else:
            due_dt = None
            label = str(shift)
        result[task] = DeadlineInfo(label=label or "", due=due_dt)
    return result


def compute_process_deadlines(shifts: dict, count: int = 3) -> list[DeadlineInfo]:
    today = datetime.now().date()
    year = today.year if today.month <= 12 else today.year + 1
    start = date(year, 10, 15)
    end = date(year, 12, 14)
    base_dates = _evenly_spaced_dates(count, start, end)
    deadlines: list[DeadlineInfo] = []
    for idx, base in enumerate(base_dates, start=1):
        key = f"task_{idx}"
        shift_val = shifts.get(key, shifts.get(f"mpi_task_{idx}", 0))
        if isinstance(shift_val, int):
            due_date = base + timedelta(days=shift_val)
            due_dt = datetime.combine(
                due_date,
                datetime.max.time().replace(
                    hour=23, minute=59, second=0, microsecond=0
                ),
            )
            label = _abbr(due_date)
        else:
            due_dt = None
            label = str(shift_val)
        deadlines.append(DeadlineInfo(label=label or "", due=due_dt))
    return deadlines


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------


def build_threads_rows(
    status_map: dict[str, dict[str, str]],
    perf_map: dict[str, dict],
    points_info: dict,
    copying_cfg: dict,
    deadline_info: dict[str, DeadlineInfo],
    eff_num_proc: int,
    repo_salt: str,
) -> list[ThreadsRow]:
    rows: list[ThreadsRow] = []
    vmax = int((points_info.get("threads", {}) or {}).get("variants_max", 1))

    for dir_name in sorted(status_map.keys()):
        student = load_student_info(TASKS_DIR / dir_name) or {}
        display_name = "<br/>".join(
            [
                p
                for p in [
                    student.get("last_name"),
                    student.get("first_name"),
                    student.get("middle_name"),
                ]
                if p
            ]
        )
        if not display_name:
            display_name = dir_name
        variant = compute_variant_threads(student, repo_salt, vmax)

        total = 0.0
        cells: dict[str, dict] = {}
        perf_entry = perf_map.get(dir_name, {})
        seq_time = perf_entry.get("seq")

        for task in THREAD_TASK_TYPES:
            status = status_map[dir_name].get(task)
            sol_points, sol_style = get_solution_points_and_style(
                task, status, points_info
            )
            is_plagiarised, plag_points = check_plagiarism_and_calculate_penalty(
                dir_name, task, sol_points, copying_cfg, points_info, semester="threads"
            )
            deadline_penalty = calculate_deadline_penalty(
                dir_name,
                task,
                status,
                deadline_info.get(task).due if task in deadline_info else None,
                TASKS_DIR,
            )

            if task == "seq":
                perf_points = 0.0
                acceleration = "—"
                efficiency = "—"
                perf_points_display = "—"
            else:
                par_time = perf_entry.get(task)
                acceleration, efficiency = calculate_performance_metrics(
                    par_time, eff_num_proc, task_type=task, seq_val=seq_time
                )
                perf_max = _find_performance_max(points_info, task)
                try:
                    eff_val = float(efficiency)
                except Exception:
                    eff_val = None
                perf_points = calc_perf_points_from_efficiency(eff_val, perf_max)
                perf_points_display = (
                    f"{perf_points:.2f}" if eff_val is not None else "—"
                )

            report_points = (
                _find_report_max(points_info, task)
                if (TASKS_DIR / dir_name / "report.md").exists()
                else 0
            )

            cells[task] = {
                "solution_points": sol_points,
                "solution_class": "cell-success"
                if status == "done"
                else ("cell-muted" if status == "disabled" else ""),
                "performance_points": perf_points_display,
                "acceleration": acceleration,
                "efficiency": efficiency,
                "deadline_penalty": int(deadline_penalty) if deadline_penalty else 0,
                "copy_penalty": plag_points,
                "copy_class": "cell-warning"
                if is_plagiarised or status == "disabled"
                else "",
                "report_points": report_points,
                "report_class": "cell-success" if report_points else "",
            }
            total += sol_points + perf_points + report_points + plag_points

        rows.append(
            ThreadsRow(
                name=display_name,
                variant=variant,
                cells=cells,
                total=total,
                student=student,
            )
        )

    return rows


def _find_process_points(points_info: dict, task_number: int) -> tuple[int, int, int]:
    proc_tasks = (points_info.get("processes", {}) or {}).get("tasks", [])
    key = f"mpi_task_{task_number}"
    for task in proc_tasks:
        if str(task.get("name")) == key:
            mpi_blk = task.get("mpi", {})
            seq_blk = task.get("seq", {})

            def _extract(obj, key):
                if isinstance(obj, dict):
                    return int(obj.get(key, 0))
                if isinstance(obj, list):
                    for it in obj:
                        if isinstance(it, dict) and key in it:
                            return int(it.get(key, 0))
                return 0

            s_mpi = _extract(mpi_blk, "S")
            a_mpi = _extract(mpi_blk, "A")
            s_seq = _extract(seq_blk, "S")
            return s_mpi, s_seq, a_mpi
    return 0, 0, 0


def _find_process_report(points_info: dict, task_number: int) -> int:
    proc_tasks = (points_info.get("processes", {}) or {}).get("tasks", [])
    key = f"mpi_task_{task_number}"
    for task in proc_tasks:
        if str(task.get("name")) == key:
            try:
                return int(task.get("R", 0))
            except Exception:
                return 0
    return 0


def _find_process_vmax(points_info: dict, task_number: int) -> int:
    proc_tasks = (points_info.get("processes", {}) or {}).get("tasks", [])
    key = f"mpi_task_{task_number}"
    for task in proc_tasks:
        if str(task.get("name")) == key:
            try:
                return int(task.get("variants_max", 1))
            except Exception:
                return 1
    return 1


def build_process_rows(
    status_map: dict[str, dict[str, str]],
    perf_map: dict[str, dict],
    points_info: dict,
    copying_cfg: dict,
    deadlines: list[DeadlineInfo],
    eff_num_proc: int,
    repo_salt: str,
) -> list[ProcessesRow]:
    # Group directories by student identity
    def identity(student: dict) -> str:
        return "|".join(
            [
                student.get("last_name", ""),
                student.get("first_name", ""),
                student.get("middle_name", ""),
                student.get("group_number", ""),
            ]
        )

    dirs_by_identity: dict[str, dict] = {}
    for dir_name, tasks in status_map.items():
        if "mpi" not in tasks:
            continue
        student = load_student_info(TASKS_DIR / dir_name) or {}
        key = identity(student)
        entry = dirs_by_identity.setdefault(key, {"student": student, "task_dirs": {}})
        try:
            task_number = int(student.get("task_number", 1))
        except Exception:
            task_number = 1
        entry["task_dirs"][task_number] = dir_name

    rows: list[ProcessesRow] = []
    vmaxes = [_find_process_vmax(points_info, n) for n in [1, 2, 3]]

    for key in sorted(dirs_by_identity.keys()):
        student = dirs_by_identity[key]["student"]
        task_dirs = dirs_by_identity[key]["task_dirs"]
        display_name = (
            "<br/>".join(
                [
                    p
                    for p in [
                        student.get("last_name"),
                        student.get("first_name"),
                        student.get("middle_name"),
                    ]
                    if p
                ]
            )
            or "processes"
        )
        variant = compute_variants_processes(student, repo_salt, vmaxes)

        groups: list[dict] = []
        r_values: list[int] = []
        total = 0.0

        for idx in [1, 2, 3]:
            dir_name = task_dirs.get(idx)
            deadline = (
                deadlines[idx - 1]
                if idx - 1 < len(deadlines)
                else DeadlineInfo(label="", due=None)
            )
            s_mpi, s_seq, a_mpi = _find_process_points(points_info, idx)
            r_max = _find_process_report(points_info, idx)

            if dir_name:
                status_seq = status_map[dir_name].get("seq")
                status_mpi = status_map[dir_name].get("mpi")
                perf_entry = perf_map.get(dir_name, {})

                seq_time = perf_entry.get("seq")
                mpi_time = perf_entry.get("mpi")

                seq_sol, seq_style = get_solution_points_and_style(
                    "seq", status_seq, points_info
                )
                mpi_sol, mpi_style = get_solution_points_and_style(
                    "mpi", status_mpi, points_info
                )

                seq_deadline_penalty = calculate_deadline_penalty(
                    dir_name, "seq", status_seq, deadline.due, TASKS_DIR
                )
                mpi_deadline_penalty = calculate_deadline_penalty(
                    dir_name, "mpi", status_mpi, deadline.due, TASKS_DIR
                )

                acc, eff = calculate_performance_metrics(
                    mpi_time, eff_num_proc, task_type="mpi", seq_val=seq_time
                )
                try:
                    eff_val = float(eff)
                except Exception:
                    eff_val = None
                perf_points = (
                    calc_perf_points_from_efficiency(eff_val, a_mpi)
                    if status_seq and status_mpi
                    else 0.0
                )
                perf_points_display = (
                    f"{perf_points:.2f}" if eff_val is not None else "—"
                )

                plag_mpi, plag_pts_mpi = check_plagiarism_and_calculate_penalty(
                    dir_name,
                    "mpi",
                    mpi_sol,
                    copying_cfg,
                    points_info,
                    semester="processes",
                )
                plag_seq, plag_pts_seq = check_plagiarism_and_calculate_penalty(
                    dir_name,
                    "seq",
                    seq_sol,
                    copying_cfg,
                    points_info,
                    semester="processes",
                )

                groups.extend(
                    [
                        {
                            "solution_points": seq_sol,
                            "solution_class": "cell-success"
                            if status_seq == "done"
                            else ("cell-muted" if status_seq == "disabled" else ""),
                            "deadline_penalty": int(seq_deadline_penalty)
                            if seq_deadline_penalty
                            else 0,
                            "copy_penalty": plag_pts_seq,
                            "copy_class": "cell-warning"
                            if plag_seq or status_seq == "disabled"
                            else "",
                        },
                        {
                            "solution_points": mpi_sol,
                            "solution_class": "cell-success"
                            if status_mpi == "done"
                            else ("cell-muted" if status_mpi == "disabled" else ""),
                            "performance_points": perf_points_display,
                            "acceleration": acc,
                            "efficiency": eff,
                            "deadline_penalty": int(mpi_deadline_penalty)
                            if mpi_deadline_penalty
                            else 0,
                            "copy_penalty": plag_pts_mpi,
                            "copy_class": "cell-warning"
                            if plag_mpi or status_mpi == "disabled"
                            else "",
                        },
                    ]
                )

                report_points = (
                    r_max if (TASKS_DIR / dir_name / "report.md").exists() else 0
                )
                r_values.append(report_points)

                total += (
                    seq_sol
                    + mpi_sol
                    + perf_points
                    + report_points
                    + plag_pts_mpi
                    + plag_pts_seq
                )
            else:
                groups.extend(
                    [
                        {
                            "solution_points": 0,
                            "solution_class": "cell-empty",
                            "deadline_penalty": 0,
                            "copy_penalty": 0,
                            "copy_class": "",
                        },
                        {
                            "solution_points": 0,
                            "solution_class": "cell-empty",
                            "performance_points": "—",
                            "acceleration": "—",
                            "efficiency": "—",
                            "deadline_penalty": 0,
                            "copy_penalty": 0,
                            "copy_class": "",
                        },
                    ]
                )
                r_values.append(0)

        rows.append(
            ProcessesRow(
                name=display_name,
                variant=variant,
                groups=groups,
                r_values=r_values,
                total=total,
                student=student,
            )
        )

    return rows


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def _find_report_max(points_info: dict, task_type: str) -> int:
    threads_tasks = (points_info.get("threads", {}) or {}).get("tasks", [])
    for t in threads_tasks:
        if str(t.get("name")) == task_type:
            try:
                return int(t.get("R", 0))
            except Exception:
                return 0
    return 0


def _find_performance_max(points_info: dict, task_type: str) -> int:
    threads_tasks = (points_info.get("threads", {}) or {}).get("tasks", [])
    for t in threads_tasks:
        if str(t.get("name")) == task_type:
            try:
                return int(t.get("A", 0))
            except Exception:
                return 0
    return 0


__all__ = [
    "THREAD_TASK_TYPES",
    "ThreadsRow",
    "ProcessesRow",
    "build_threads_rows",
    "build_process_rows",
    "compute_threads_deadlines",
    "compute_process_deadlines",
]
