"""Student entity holding submissions and score accessors."""

from __future__ import annotations

from dataclasses import dataclass, field

from tasks import (
    ProcessScore,
    ProcessSubmission,
    ProcessTask,
    TaskScore,
    ThreadSubmission,
    ThreadTask,
)


@dataclass
class Student:
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    group_number: str = ""
    student_id: str | None = None

    task_scores: dict[str, TaskScore] = field(default_factory=dict)
    process_scores: dict[str, ProcessScore] = field(default_factory=dict)
    thread_submissions: dict[str, ThreadSubmission] = field(default_factory=dict)
    process_submissions: dict[str, ProcessSubmission] = field(default_factory=dict)

    def identity_key(self) -> str:
        return "|".join(
            [
                self.last_name or "",
                self.first_name or "",
                self.middle_name or "",
                self.group_number or "",
            ]
        )

    @property
    def display_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return "<br/>".join([p for p in parts if p]) or "—"

    def as_dict(self) -> dict:
        return {
            "last_name": self.last_name,
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "group_number": self.group_number,
            "student_id": self.student_id,
        }

    # ----- submissions ---------------------------------------------------#

    def add_thread_submission(self, submission: ThreadSubmission) -> None:
        self.thread_submissions[submission.task_name] = submission

    def add_process_submission(
        self, task_name: str, submission: ProcessSubmission
    ) -> None:
        self.process_submissions[task_name] = submission

    # ----- scoring -------------------------------------------------------#

    def score_thread(self, task: ThreadTask) -> TaskScore:
        if task.name not in self.task_scores:
            submission = self.thread_submissions.get(task.name)
            self.task_scores[task.name] = task.calculate_score(self, submission)
        return self.task_scores[task.name]

    def score_process(self, task: ProcessTask) -> ProcessScore:
        if task.name not in self.process_scores:
            submission = self.process_submissions.get(task.name)
            self.process_scores[task.name] = task.calculate_score(self, submission)
        return self.process_scores[task.name]

    def threads_total(self, tasks: list[ThreadTask]) -> float:
        return round(sum(self.score_thread(t).total for t in tasks), 2)

    def processes_total(self, tasks: list[ProcessTask]) -> float:
        return round(sum(self.score_process(t).total for t in tasks), 2)


__all__ = ["Student"]
