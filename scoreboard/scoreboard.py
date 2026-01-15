"""High-level scoreboard assembly: tasks + students + rendering helpers."""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional

from assign_variant import assign_variant
from data_loader import (
    SCRIPT_DIR,
    TASKS_DIR,
    discover_tasks,
    load_benchmark_json,
    load_copying_config,
    load_deadline_shifts,
    load_points_info,
    load_student_info,
)
from student import Student

from tasks import (
    DeadlineInfo,
    ProcessScore,
    ProcessSubmission,
    ProcessTask,
    TaskScore,
    ThreadSubmission,
    ThreadTask,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------#
# Helpers                                                                    #
# ---------------------------------------------------------------------------#


def _normalize_group(group: str | None) -> str:
    """Normalize group strings to avoid duplicates like ivt-101 vs IVT-101."""
    if group is None:
        return ""
    return str(group).strip().upper()


# ---------------------------------------------------------------------------#
# Row DTOs (for templating)                                                  #
# ---------------------------------------------------------------------------#


@dataclass
class ThreadsRow:
    name: str
    variant: str
    cells: dict[str, TaskScore]
    total: float
    student: Student


@dataclass
class ProcessesRow:
    name: str
    variant: str
    groups: List[TaskScore]
    r_values: List[float]
    total: float
    student: Student


# ---------------------------------------------------------------------------#
# Scoreboard                                                                 #
# ---------------------------------------------------------------------------#


class Scoreboard:
    """Encapsulates tasks, students, and scoring logic."""

    def __init__(
        self,
        repo_salt: str,
        points_info: dict,
        copying_cfg: dict,
        deadline_shifts: dict,
        tasks_dir: Path = TASKS_DIR,
        efficiency_scale: list[tuple[float, float]] | None = None,
    ) -> None:
        self.repo_salt = repo_salt
        self.points_info = points_info
        self.copying_cfg = copying_cfg
        self.deadline_shifts = deadline_shifts
        self.tasks_dir = tasks_dir

        self.copy_coeff = float(
            (points_info.get("copying", {}) or {}).get("coefficient", 0.0)
        )
        self.eff_num_proc = int(
            (points_info.get("efficiency", {}) or {}).get("num_proc", 1)
        )
        self.efficiency_scale = efficiency_scale or self._parse_efficiency_scale(
            points_info.get("efficiency_scale")
        )

        self.thread_tasks: list[ThreadTask] = self._build_thread_tasks()
        self.process_tasks: list[ProcessTask] = self._build_process_tasks()

        self.thread_students: list[Student] = []
        self.process_students: list[Student] = []

    # ----- construction helpers -----------------------------------------#

    @classmethod
    def from_files(cls, repo_salt: str) -> "Scoreboard":
        points_info = load_points_info()
        copying_cfg = load_copying_config()
        deadline_shifts = load_deadline_shifts()
        board = cls(
            repo_salt=repo_salt,
            points_info=points_info,
            copying_cfg=copying_cfg,
            deadline_shifts=deadline_shifts,
            efficiency_scale=None,
        )

        thread_task_names = [
            str(t.get("name"))
            for t in (points_info.get("threads", {}) or {}).get("tasks", [])
        ]
        status_map = discover_tasks(board.tasks_dir, thread_task_names + ["mpi"])
        threads_dirs = {k: v for k, v in status_map.items() if "mpi" not in v}
        processes_dirs = {k: v for k, v in status_map.items() if "mpi" in v}

        perf_threads, perf_processes = board._load_perf_data(status_map.keys())

        board._build_thread_students(threads_dirs, perf_threads)
        board._build_process_students(processes_dirs, perf_processes)

        # Consistency guard: number of unique identities vs produced rows.
        thread_identities = board._collect_identities(threads_dirs)
        proc_identities = board._collect_identities(processes_dirs)
        if len(thread_identities) != len(board.thread_students):
            raise RuntimeError(
                "Threads track mismatch: discovered "
                f"{len(thread_identities)} unique students across task folders, "
                f"produced {len(board.thread_students)} rows. "
                "Ensure each task has valid info.json (last/first/middle/group)."
            )
        if len(proc_identities) != len(board.process_students):
            raise RuntimeError(
                "Processes track mismatch: discovered "
                f"{len(proc_identities)} unique students across task folders, "
                f"produced {len(board.process_students)} rows. "
                "Likely missing or duplicate student info."
            )
        return board

    def _build_thread_tasks(self) -> list[ThreadTask]:
        tasks_cfg = (self.points_info.get("threads", {}) or {}).get("tasks", [])
        deadlines = self._compute_threads_deadlines(
            self.deadline_shifts.get("threads", {}),
            self.deadline_shifts.get("threads_base", {}),
            len(tasks_cfg),
        )
        tasks: list[ThreadTask] = []
        for cfg in tasks_cfg:
            name = str(cfg.get("name"))
            display_name = cfg.get("title") or name
            task = ThreadTask(
                name=name,
                display_name=display_name,
                s_points=int(cfg.get("S", 0)),
                a_points=int(cfg.get("A", 0)),
                r_points=int(cfg.get("R", 0)),
                deadline=deadlines.get(name),
                copy_coeff=self.copy_coeff,
                eff_num_proc=self.eff_num_proc,
                efficiency_scale=self.efficiency_scale,
            )
            tasks.append(task)
        return tasks

    def _build_process_tasks(self) -> list[ProcessTask]:
        tasks_cfg = (self.points_info.get("processes", {}) or {}).get("tasks", [])
        deadlines = self._compute_process_deadlines(
            self.deadline_shifts.get("processes", {}),
            len(tasks_cfg),
            self.deadline_shifts.get("processes_base", {}),
        )
        tasks: list[ProcessTask] = []
        for idx, (cfg, deadline) in enumerate(zip(tasks_cfg, deadlines), start=1):
            name = str(cfg.get("name"))
            display_name = cfg.get("title") or f"Task {idx}"
            mpi_blk = cfg.get("mpi", {})
            seq_blk = cfg.get("seq", {})

            def _extract(block: dict | list, key: str) -> int:
                if isinstance(block, dict):
                    return int(block.get(key, 0))
                if isinstance(block, list):
                    for it in block:
                        if isinstance(it, dict) and key in it:
                            return int(it.get(key, 0))
                return 0

            mpi_points = {"S": _extract(mpi_blk, "S"), "A": _extract(mpi_blk, "A")}
            seq_points = {"S": _extract(seq_blk, "S"), "A": _extract(seq_blk, "A")}

            task = ProcessTask(
                name=name,
                display_name=display_name,
                mpi_points=mpi_points,
                seq_points=seq_points,
                r_points=int(cfg.get("R", 0)),
                variants_max=int(cfg.get("variants_max", 1)),
                deadline=deadline,
                copy_coeff=self.copy_coeff,
                eff_num_proc=self.eff_num_proc,
                efficiency_scale=self.efficiency_scale,
            )
            tasks.append(task)
        return tasks

    # ------------------------------------------------------------------#
    # Student discovery / submissions                                   #
    # ------------------------------------------------------------------#

    def _resolve_dir(self, dir_name: str) -> Path:
        base = self.tasks_dir / dir_name
        if base.exists():
            return base
        disabled = self.tasks_dir / f"{dir_name}_disabled"
        if disabled.exists():
            return disabled
        return base

    def _load_perf_data(self, task_hints: Iterable[str]) -> tuple[dict, dict]:
        def locate(kind: str) -> Optional[Path]:
            candidates = [
                SCRIPT_DIR.parent / "build" / "bin" / f"perf_results_{kind}.json",
                SCRIPT_DIR.parent / "install" / "bin" / f"perf_results_{kind}.json",
                SCRIPT_DIR.parent / f"perf_results_{kind}.json",
            ]
            return next((p for p in candidates if p.exists()), None)

        threads_perf: dict[str, dict] = {}
        processes_perf: dict[str, dict] = {}

        threads_json = locate("threads")
        processes_json = locate("processes")

        if threads_json:
            threads_perf, _ = load_benchmark_json(threads_json, list(task_hints))
        if processes_json:
            processes_perf, _ = load_benchmark_json(processes_json, list(task_hints))

        return threads_perf, processes_perf

    def _is_copied(self, semester: str, task_key: str, dir_name: str) -> bool:
        semester_cfg = (
            self.copying_cfg.get(semester, {})
            if isinstance(self.copying_cfg, dict)
            else {}
        )
        mapping = semester_cfg.get("copying") or semester_cfg.get("plagiarism") or {}
        flagged = set(mapping.get(task_key, []) or [])
        return dir_name in flagged or f"{dir_name}_disabled" in flagged

    def _build_thread_students(
        self, status_map: dict[str, dict[str, str]], perf_map: dict[str, dict]
    ) -> None:
        for dir_name in sorted(status_map.keys()):
            work_dir = self._resolve_dir(dir_name)
            student_info = load_student_info(work_dir) or {}
            student = Student(
                last_name=student_info.get("last_name", ""),
                first_name=student_info.get("first_name", ""),
                middle_name=student_info.get("middle_name", ""),
                group_number=_normalize_group(student_info.get("group_number", "")),
                student_id=student_info.get("student_id"),
            )

            perf_entry = perf_map.get(dir_name, {})
            seq_time = perf_entry.get("seq")
            report_present = (work_dir / "report.md").exists()

            for task in self.thread_tasks:
                status = status_map[dir_name].get(task.name)
                submission = ThreadSubmission(
                    task_name=task.name,
                    status=status,
                    work_dir=work_dir,
                    perf_time=perf_entry.get(task.name),
                    seq_time=seq_time,
                    report_present=report_present,
                    copied=self._is_copied("threads", task.name, dir_name),
                )
                student.add_thread_submission(submission)
            self.thread_students.append(student)

    def _build_process_students(
        self, status_map: dict[str, dict[str, str]], perf_map: dict[str, dict]
    ) -> None:
        students_by_identity: dict[str, Student] = {}
        num_tasks = len(self.process_tasks)
        for dir_name, statuses in status_map.items():
            work_dir = self._resolve_dir(dir_name)
            student_info = load_student_info(work_dir) or {}
            identity = self._identity_key(student_info)
            if not identity:
                logger.warning(
                    "Skipping task folder with empty student info: %s", work_dir
                )
                continue
            student = students_by_identity.get(self._identity_key(student_info))
            if student is None:
                student = Student(
                    last_name=student_info.get("last_name", ""),
                    first_name=student_info.get("first_name", ""),
                    middle_name=student_info.get("middle_name", ""),
                    group_number=_normalize_group(student_info.get("group_number", "")),
                    student_id=student_info.get("student_id"),
                )
                students_by_identity[student.identity_key()] = student

            task_number = self._parse_task_number(student_info, work_dir, identity)
            self._validate_task_number(task_number, num_tasks, work_dir, identity)
            task_name = f"mpi_task_{task_number}"
            perf_entry = perf_map.get(dir_name, {})
            self._ensure_unique_submission(student, task_name, work_dir, identity)
            submission = self._make_process_submission(
                task_number, task_name, statuses, perf_entry, work_dir, dir_name
            )
            student.add_process_submission(task_name, submission)

        self.process_students = [
            students_by_identity[k] for k in sorted(students_by_identity.keys())
        ]

    def _collect_identities(self, status_map: dict[str, dict[str, str]]) -> set[str]:
        identities: set[str] = set()
        for dir_name in status_map.keys():
            work_dir = self._resolve_dir(dir_name)
            student_info = load_student_info(work_dir) or {}
            identity = self._identity_key(student_info)
            if identity:
                identities.add(identity)
        return identities

    # ------------------------------------------------------------------#
    # Helpers for process student construction                          #
    # ------------------------------------------------------------------#

    def _parse_task_number(
        self, student_info: dict, work_dir: Path, identity: str
    ) -> int:
        try:
            return int(student_info.get("task_number", 1))
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Invalid task_number in {work_dir}/info.json for {identity.replace('|', ' ')}"
            ) from exc

    def _validate_task_number(
        self, task_number: int, num_tasks: int, work_dir: Path, identity: str
    ) -> None:
        if num_tasks <= 0:
            raise RuntimeError("No process tasks configured; cannot assign task_number")
        if task_number < 1 or task_number > num_tasks:
            raise RuntimeError(
                "task_number out of range in "
                f"{work_dir}/info.json for {identity.replace('|', ' ')}: "
                f"{task_number} (allowed 1..{num_tasks})"
            )

    def _ensure_unique_submission(
        self, student: Student, task_name: str, work_dir: Path, identity: str
    ) -> None:
        if task_name in student.process_submissions:
            raise RuntimeError(
                f"Duplicate process task {task_name} for student {identity.replace('|', ' ')} "
                f"in {work_dir} and {student.process_submissions[task_name].work_dir}"
            )

    def _make_process_submission(
        self,
        task_number: int,
        task_name: str,
        statuses: dict[str, str],
        perf_entry: dict,
        work_dir: Path,
        dir_name: str,
    ) -> ProcessSubmission:
        return ProcessSubmission(
            task_number=task_number,
            seq_status=statuses.get("seq"),
            mpi_status=statuses.get("mpi"),
            work_dir=work_dir,
            seq_time=perf_entry.get("seq"),
            mpi_time=perf_entry.get("mpi"),
            report_present=(work_dir / "report.md").exists(),
            seq_copied=self._is_copied("processes", "seq", dir_name),
            mpi_copied=self._is_copied("processes", "mpi", dir_name),
        )

    @staticmethod
    def _identity_key(student: dict) -> str:
        return "|".join(
            [
                str(student.get("last_name", "")),
                str(student.get("first_name", "")),
                str(student.get("middle_name", "")),
                _normalize_group(student.get("group_number", "")),
            ]
        )

    # ------------------------------------------------------------------#
    # Deadlines                                                         #
    # ------------------------------------------------------------------#

    def _abbr(self, d: date) -> str:
        return f"{d.day} {calendar.month_abbr[d.month]}"

    def _evenly_spaced_dates(self, n: int, start: date, end: date) -> list[date]:
        if n <= 1:
            return [end]
        total = (end - start).days
        step = total / n
        return [start + timedelta(days=int(round(step * (i + 1)))) for i in range(n)]

    def _compute_threads_deadlines(
        self, shifts: dict, base: dict, task_count: int
    ) -> dict[str, DeadlineInfo]:
        today = datetime.now().date()
        year = today.year if today.month <= 5 else today.year + 1
        start_month = int(base.get("start_month", 2))
        start_day = int(base.get("start_day", 1))
        end_month = int(base.get("end_month", 5))
        end_day = int(base.get("end_day", 15))
        start = date(year, start_month, start_day)
        end = date(year, end_month, end_day)
        base_dates = self._evenly_spaced_dates(task_count, start, end)
        result: dict[str, DeadlineInfo] = {}
        for task_name, base in zip(
            [
                t.get("name")
                for t in (self.points_info.get("threads", {}) or {}).get("tasks", [])
            ],
            base_dates,
        ):
            shift = shifts.get(task_name, 0)
            if isinstance(shift, int):
                due_date = base + timedelta(days=shift)
                due_dt = datetime.combine(
                    due_date,
                    datetime.max.time().replace(
                        hour=23, minute=59, second=0, microsecond=0
                    ),
                )
                label = self._abbr(due_date)
            else:
                due_dt = None
                label = str(shift)
            result[task_name] = DeadlineInfo(label=label or "", due=due_dt)
        return result

    def _compute_process_deadlines(
        self, shifts: dict, count: int, base: dict
    ) -> list[DeadlineInfo]:
        today = datetime.now().date()
        year = today.year if today.month <= 12 else today.year + 1
        start_month = int(base.get("start_month", 10))
        start_day = int(base.get("start_day", 15))
        end_month = int(base.get("end_month", 12))
        end_day = int(base.get("end_day", 14))
        start = date(year, start_month, start_day)
        end = date(year, end_month, end_day)
        base_dates = self._evenly_spaced_dates(count, start, end)
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
                label = self._abbr(due_date)
            else:
                due_dt = None
                label = str(shift_val)
            deadlines.append(DeadlineInfo(label=label or "", due=due_dt))
        return deadlines

    # ------------------------------------------------------------------#
    # Variants                                                          #
    # ------------------------------------------------------------------#

    def thread_variant(self, student: Student) -> str:
        vmax = int((self.points_info.get("threads", {}) or {}).get("variants_max", 1))
        if not student:
            return "?"
        try:
            vidx = assign_variant(
                surname=student.last_name,
                name=student.first_name,
                patronymic=student.middle_name,
                group=student.group_number,
                repo=self.repo_salt,
                num_variants=vmax,
            )
            return str(vidx + 1)
        except Exception:
            return "?"

    def process_variants(self, student: Student) -> str:
        rendered: list[str] = []
        for idx, task in enumerate(self.process_tasks, start=1):
            try:
                vidx = assign_variant(
                    surname=student.last_name,
                    name=student.first_name,
                    patronymic=student.middle_name,
                    group=student.group_number,
                    repo=f"{self.repo_salt}/processes/task-{idx}",
                    num_variants=task.variants_max,
                )
                rendered.append(str(vidx + 1))
            except Exception:
                rendered.append("?")
        return "<br/>".join(rendered)

    # ------------------------------------------------------------------#
    # Rows for rendering                                                #
    # ------------------------------------------------------------------#

    def build_threads_rows(
        self, students: Optional[list[Student]] = None
    ) -> list[ThreadsRow]:
        target_students = students if students is not None else self.thread_students
        rows: list[ThreadsRow] = []
        for student in target_students:
            cells: dict[str, TaskScore] = {}
            for task in self.thread_tasks:
                cells[task.name] = student.score_thread(task)
            rows.append(
                ThreadsRow(
                    name=student.display_name,
                    variant=self.thread_variant(student),
                    cells=cells,
                    total=student.threads_total(self.thread_tasks),
                    student=student,
                )
            )
        return rows

    def build_process_rows(
        self, students: Optional[list[Student]] = None
    ) -> list[ProcessesRow]:
        target_students = students if students is not None else self.process_students
        rows: list[ProcessesRow] = []
        for student in target_students:
            groups: list[TaskScore] = []
            r_values: list[float] = []
            total = 0.0
            for task in self.process_tasks:
                score: ProcessScore = student.score_process(task)
                groups.extend([score.seq, score.mpi])
                r_values.append(score.report_points)
                total += score.total
            rows.append(
                ProcessesRow(
                    name=student.display_name,
                    variant=self.process_variants(student),
                    groups=groups,
                    r_values=r_values,
                    total=round(total, 2),
                    student=student,
                )
            )
        return rows

    # ------------------------------------------------------------------#
    # Groups filtering                                                  #
    # ------------------------------------------------------------------#

    @staticmethod
    def _group_from_student(student: Student) -> str | None:
        return student.group_number or None

    def groups_threads(self) -> list[str]:
        groups = {
            g for g in (self._group_from_student(s) for s in self.thread_students) if g
        }
        return sorted(groups)

    def groups_processes(self) -> list[str]:
        groups = {
            g for g in (self._group_from_student(s) for s in self.process_students) if g
        }
        return sorted(groups)

    def threads_rows_for_group(self, group: str) -> list[ThreadsRow]:
        filtered = [s for s in self.thread_students if s.group_number == group]
        return self.build_threads_rows(filtered)

    def processes_rows_for_group(self, group: str) -> list[ProcessesRow]:
        filtered = [s for s in self.process_students if s.group_number == group]
        return self.build_process_rows(filtered)

    # ------------------------------------------------------------------#
    # Labels / metadata                                                 #
    # ------------------------------------------------------------------#

    @property
    def threads_deadline_labels(self) -> dict[str, str]:
        return {
            task.name: (task.deadline.label if task.deadline else "")
            for task in self.thread_tasks
        }

    @property
    def processes_deadline_labels(self) -> list[str]:
        return [
            task.deadline.label if task.deadline else "" for task in self.process_tasks
        ]

    # ------------------------------------------------------------------#
    # Efficiency scale                                                  #
    # ------------------------------------------------------------------#

    @staticmethod
    def _parse_efficiency_scale(raw) -> list[tuple[float, float]]:
        if not raw:
            return []
        parsed: list[tuple[float, float]] = []
        for entry in raw:
            try:
                threshold = float(entry.get("threshold"))
                percent = float(entry.get("percent"))
                parsed.append((threshold, percent))
            except Exception:
                continue
        return parsed


__all__ = [
    "Scoreboard",
    "ThreadsRow",
    "ProcessesRow",
]
