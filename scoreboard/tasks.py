"""Domain model for scoreboard tasks and scoring logic."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------#
# Shared dataclasses                                                         #
# ---------------------------------------------------------------------------#


@dataclass
class DeadlineInfo:
    label: str = ""
    due: Optional[datetime] = None


@dataclass
class TaskScore:
    """Uniform representation of a task cell in the table."""

    solution_points: float = 0.0
    solution_class: str = ""
    performance_points: float = 0.0
    performance_display: str = "—"
    acceleration: str = "—"
    efficiency: str = "—"
    deadline_penalty: float = 0.0
    copy_penalty: float = 0.0
    copy_class: str = ""
    report_points: float = 0.0
    report_class: str = ""

    @property
    def total(self) -> float:
        return round(
            self.solution_points
            + self.performance_points
            + self.report_points
            + self.copy_penalty,
            2,
        )


# ---------------------------------------------------------------------------#
# Abstract task                                                              #
# ---------------------------------------------------------------------------#


class Task(ABC):
    """Base class for any course task."""

    def __init__(
        self,
        name: str,
        max_points: int,
        deadline: DeadlineInfo | None = None,
        copy_coeff: float = 0.0,
        eff_num_proc: int = 1,
        efficiency_scale: list[tuple[float, float]] | None = None,
    ):
        self.name = name
        self.max_points = max_points
        self.deadline = deadline or DeadlineInfo()
        self.copy_coeff = copy_coeff
        self.eff_num_proc = eff_num_proc
        self.efficiency_scale = efficiency_scale or []

    @abstractmethod
    def calculate_score(
        self, student, submission
    ) -> TaskScore:  # pragma: no cover - abstract
        raise NotImplementedError

    # ----- helpers shared by subclasses ----------------------------------#

    @staticmethod
    def _git_commit_time(path: Path) -> Optional[datetime]:
        git_cmd = ["git", "log", "-1", "--format=%ct", str(path)]
        try:
            result = subprocess.run(
                git_cmd, capture_output=True, text=True, check=False
            )
            ts = result.stdout.strip()
            if ts.isdigit():
                return datetime.fromtimestamp(int(ts))
        except Exception:
            return None
        return None

    def _deadline_penalty(self, path: Path | None, status: str | None) -> float:
        if status != "done" or self.deadline.due is None or path is None:
            return 0.0
        commit_dt = self._git_commit_time(path)
        if commit_dt is None:
            return 0.0
        days_late = (commit_dt - self.deadline.due).days
        return float(-days_late) if days_late > 0 else 0.0

    def _performance_metrics(
        self, perf_val: Optional[float], seq_val: Optional[float]
    ) -> tuple[Optional[float], str, str]:
        """Return (efficiency_value, acceleration_str, efficiency_str)."""
        invalid = {None, "", "?", "N/A"}
        if (
            perf_val in invalid
            or seq_val in invalid
            or perf_val is None
            or seq_val is None
        ):
            return None, "—", "—"
        try:
            seq_t = float(seq_val)
            par_t = float(perf_val)
            if seq_t <= 0 or par_t <= 0:
                return None, "—", "—"
            speedup = seq_t / par_t
            acceleration = f"{speedup:.2f}"
            eff_value = speedup / max(self.eff_num_proc, 1)
            efficiency = f"{eff_value:.2f}"
            return eff_value, acceleration, efficiency
        except Exception:
            return None, "—", "—"

    def _efficiency_to_points(
        self, efficiency_value: Optional[float], max_points: int
    ) -> float:
        if efficiency_value is None or max_points <= 0:
            return 0.0
        for threshold, pct in self.efficiency_scale:
            if efficiency_value >= threshold:
                return round(max_points * pct, 2)
        return 0.0


# ---------------------------------------------------------------------------#
# Thread tasks                                                               #
# ---------------------------------------------------------------------------#


@dataclass
class ThreadSubmission:
    task_name: str
    status: Optional[str]
    work_dir: Path
    perf_time: Optional[float]
    seq_time: Optional[float]
    report_present: bool
    copied: bool

    @property
    def impl_path(self) -> Path:
        return self.work_dir / self.task_name


class ThreadTask(Task):
    """Thread-oriented task (seq/omp/tbb/stl/all)."""

    def __init__(
        self,
        name: str,
        display_name: str | None,
        s_points: int,
        a_points: int,
        r_points: int,
        deadline: DeadlineInfo | None,
        copy_coeff: float,
        eff_num_proc: int,
        efficiency_scale: list[tuple[float, float]],
    ):
        super().__init__(
            name=name,
            max_points=s_points + a_points + r_points,
            deadline=deadline,
            copy_coeff=copy_coeff,
            eff_num_proc=eff_num_proc,
            efficiency_scale=efficiency_scale,
        )
        self.s_points = s_points
        self.a_points = a_points
        self.r_points = r_points
        self.display_name = display_name or name

    def calculate_score(
        self, student, submission: ThreadSubmission | None
    ) -> TaskScore:
        if submission is None:
            return TaskScore()

        status = submission.status
        solution_points = self.s_points if status in {"done", "disabled"} else 0.0
        solution_class = (
            "cell-success"
            if status == "done"
            else ("cell-muted" if status == "disabled" else "")
        )

        deadline_penalty = self._deadline_penalty(submission.impl_path, status)

        copy_penalty = -self.copy_coeff * solution_points if submission.copied else 0.0
        copy_class = "cell-warning" if submission.copied or status == "disabled" else ""

        report_points = self.r_points if submission.report_present else 0.0
        report_class = "cell-success" if report_points else ""

        perf_points = 0.0
        perf_display = "—"
        acceleration = "—"
        efficiency = "—"

        if self.name != "seq":
            eff_value, acceleration, efficiency = self._performance_metrics(
                submission.perf_time, submission.seq_time
            )
            perf_points = self._efficiency_to_points(eff_value, self.a_points)
            perf_display = f"{perf_points:.2f}" if eff_value is not None else "—"

        return TaskScore(
            solution_points=solution_points,
            solution_class=solution_class,
            performance_points=perf_points,
            performance_display=perf_display,
            acceleration=acceleration,
            efficiency=efficiency,
            deadline_penalty=deadline_penalty,
            copy_penalty=copy_penalty,
            copy_class=copy_class,
            report_points=report_points,
            report_class=report_class,
        )


# ---------------------------------------------------------------------------#
# Process tasks                                                              #
# ---------------------------------------------------------------------------#


@dataclass
class ProcessSubmission:
    task_number: int
    seq_status: Optional[str]
    mpi_status: Optional[str]
    work_dir: Optional[Path]
    seq_time: Optional[float]
    mpi_time: Optional[float]
    report_present: bool
    seq_copied: bool
    mpi_copied: bool

    def impl_path(self, impl_name: str) -> Path | None:
        if self.work_dir is None:
            return None
        return self.work_dir / impl_name


@dataclass
class ProcessScore:
    seq: TaskScore
    mpi: TaskScore
    report_points: float

    @property
    def total(self) -> float:
        return round(
            self.seq.total + self.mpi.total + self.report_points,
            2,
        )


class ProcessTask(Task):
    """MPI/seq paired task."""

    def __init__(
        self,
        name: str,
        display_name: str | None,
        mpi_points: dict,
        seq_points: dict,
        r_points: int,
        variants_max: int,
        deadline: DeadlineInfo | None,
        copy_coeff: float,
        eff_num_proc: int,
        efficiency_scale: list[tuple[float, float]],
    ):
        super().__init__(
            name=name,
            max_points=int(r_points)
            + int(mpi_points.get("S", 0))
            + int(seq_points.get("S", 0))
            + int(mpi_points.get("A", 0)),
            deadline=deadline,
            copy_coeff=copy_coeff,
            eff_num_proc=eff_num_proc,
            efficiency_scale=efficiency_scale,
        )
        self.mpi_points = {k: int(v) for k, v in mpi_points.items()}
        self.seq_points = {k: int(v) for k, v in seq_points.items()}
        self.r_points = int(r_points)
        self.variants_max = int(variants_max)
        self.display_name = display_name or name

    def calculate_score(
        self, student, submission: ProcessSubmission | None
    ) -> ProcessScore:
        if submission is None:
            empty = TaskScore()
            return ProcessScore(seq=empty, mpi=empty, report_points=0.0)

        seq_solution = (
            self.seq_points.get("S", 0)
            if submission.seq_status in {"done", "disabled"}
            else 0.0
        )
        seq_solution_class = (
            "cell-success"
            if submission.seq_status == "done"
            else ("cell-muted" if submission.seq_status == "disabled" else "")
        )
        seq_deadline = self._deadline_penalty(
            submission.impl_path("seq"), submission.seq_status
        )
        seq_copy_penalty = (
            -self.copy_coeff * seq_solution if submission.seq_copied else 0.0
        )
        seq_copy_class = (
            "cell-warning"
            if submission.seq_copied or submission.seq_status == "disabled"
            else ""
        )
        seq_score = TaskScore(
            solution_points=seq_solution,
            solution_class=seq_solution_class,
            deadline_penalty=seq_deadline,
            copy_penalty=seq_copy_penalty,
            copy_class=seq_copy_class,
        )

        mpi_solution = (
            self.mpi_points.get("S", 0)
            if submission.mpi_status in {"done", "disabled"}
            else 0.0
        )
        mpi_solution_class = (
            "cell-success"
            if submission.mpi_status == "done"
            else ("cell-muted" if submission.mpi_status == "disabled" else "")
        )
        mpi_deadline = self._deadline_penalty(
            submission.impl_path("mpi"), submission.mpi_status
        )
        mpi_copy_penalty = (
            -self.copy_coeff * mpi_solution if submission.mpi_copied else 0.0
        )
        mpi_copy_class = (
            "cell-warning"
            if submission.mpi_copied or submission.mpi_status == "disabled"
            else ""
        )

        eff_value, acceleration, efficiency = self._performance_metrics(
            submission.mpi_time, submission.seq_time
        )
        perf_points = self._efficiency_to_points(eff_value, self.mpi_points.get("A", 0))
        perf_display = f"{perf_points:.2f}" if eff_value is not None else "—"

        mpi_score = TaskScore(
            solution_points=mpi_solution,
            solution_class=mpi_solution_class,
            performance_points=perf_points,
            performance_display=perf_display,
            acceleration=acceleration,
            efficiency=efficiency,
            deadline_penalty=mpi_deadline,
            copy_penalty=mpi_copy_penalty,
            copy_class=mpi_copy_class,
        )

        report_points = self.r_points if submission.report_present else 0.0

        return ProcessScore(seq=seq_score, mpi=mpi_score, report_points=report_points)


__all__ = [
    "DeadlineInfo",
    "TaskScore",
    "Task",
    "ThreadTask",
    "ThreadSubmission",
    "ProcessTask",
    "ProcessSubmission",
    "ProcessScore",
]
