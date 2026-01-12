"""CLI entrypoint to build static scoreboard HTML pages.

All calculations are done on the Python side; the resulting pages are
fully static (JS only for variant display/calculator).
"""

from __future__ import annotations

import argparse
import logging
import shutil
from datetime import datetime
from pathlib import Path

from builder import (
    THREAD_TASK_TYPES,
    build_process_rows,
    build_threads_rows,
    compute_process_deadlines,
    compute_threads_deadlines,
)
from data_loader import (
    SCRIPT_DIR,
    TASKS_DIR,
    discover_tasks,
    load_benchmark_json,
    load_copying_config,
    load_deadline_shifts,
    load_points_info,
)
from html_renderer import (
    render_index_page,
    render_processes_page,
    render_threads_page,
    render_variants_page,
)
from metrics import compute_variant_threads, compute_variants_processes
from texts import TEXT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = SCRIPT_DIR.parent.resolve()
REPO_SALT = f"learning_process/{REPO_ROOT.name}"


# ---------------------------------------------------------------------------
# Performance data resolution
# ---------------------------------------------------------------------------


def _locate_perf_json(kind: str) -> Path | None:
    candidates = [
        REPO_ROOT / "build" / "bin" / f"perf_results_{kind}.json",
        REPO_ROOT / "install" / "bin" / f"perf_results_{kind}.json",
        REPO_ROOT / f"perf_results_{kind}.json",
    ]
    return next((p for p in candidates if p.exists()), None)


def _load_perf_data(status_map: dict[str, dict[str, str]]) -> tuple[dict, dict]:
    task_hints = list(status_map.keys())
    threads_perf: dict[str, dict] = {}
    processes_perf: dict[str, dict] = {}

    threads_json = _locate_perf_json("threads")
    processes_json = _locate_perf_json("processes")

    if threads_json:
        threads_perf, _ = load_benchmark_json(threads_json, task_hints)
    if processes_json:
        processes_perf, _ = load_benchmark_json(processes_json, task_hints)

    return threads_perf, processes_perf


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


def _extract_groups(status_map: dict[str, dict[str, str]]) -> list[str]:
    groups = set()
    for dir_name in status_map.keys():
        info = TASKS_DIR / dir_name / "info.json"
        if info.exists():
            import json

            try:
                with open(info, "r", encoding="utf-8") as f:
                    data = json.load(f)
                g = data.get("student", {}).get("group_number")
                if g:
                    groups.add(str(g))
            except Exception:
                continue
    return sorted(groups)


def _collect_students(status_map: dict[str, dict[str, str]]) -> dict[str, dict]:
    students: dict[str, dict] = {}
    for dir_name in status_map.keys():
        info = TASKS_DIR / dir_name / "info.json"
        if not info.exists():
            continue
        try:
            import json

            with open(info, "r", encoding="utf-8") as f:
                data = json.load(f)
            student = data.get("student", {}) or {}
            key = "|".join(
                [
                    str(student.get("last_name", "")),
                    str(student.get("first_name", "")),
                    str(student.get("middle_name", "")),
                    str(student.get("group_number", "")),
                ]
            )
            students[key] = student
        except Exception:
            continue
    return students


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _load_css() -> str:
    css_path = SCRIPT_DIR / "static" / "main.css"
    if not css_path.exists():
        return ""
    return css_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate static scoreboard pages")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--variant",
        action="append",
        default=[],
        metavar="LAST;FIRST;MIDDLE;GROUP",
        help="Add a student for variants page (no JS). Example: --variant 'Ivanov;Ivan;Ivanovich;IVT-101'",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load configuration
    points_info = load_points_info()
    copying_cfg = load_copying_config()
    deadline_shifts = load_deadline_shifts()
    eff_num_proc = int(points_info.get("efficiency", {}).get("num_proc", 1))

    # Discover tasks on disk
    status_map = discover_tasks(TASKS_DIR, THREAD_TASK_TYPES + ["mpi"])

    # Split to threads / processes by presence of mpi implementation
    threads_dirs = {k: v for k, v in status_map.items() if "mpi" not in v}
    processes_dirs = {k: v for k, v in status_map.items() if "mpi" in v}

    # Variant maxima
    threads_vmax = int((points_info.get("threads", {}) or {}).get("variants_max", 1))

    def _proc_vmax(task_number: int) -> int:
        proc_tasks = (points_info.get("processes", {}) or {}).get("tasks", [])
        key = f"mpi_task_{task_number}"
        for task in proc_tasks:
            if str(task.get("name")) == key:
                try:
                    return int(task.get("variants_max", 1))
                except Exception:
                    return 1
        return 1

    proc_vmaxes = [_proc_vmax(n) for n in [1, 2, 3]]

    # Performance data
    perf_threads, perf_processes = _load_perf_data(status_map)

    # Deadlines
    threads_deadlines_info = compute_threads_deadlines(
        deadline_shifts.get("threads", {})
    )
    threads_deadlines_labels = {k: v.label for k, v in threads_deadlines_info.items()}
    processes_deadlines_info = compute_process_deadlines(
        deadline_shifts.get("processes", {})
    )
    processes_deadlines_labels = [d.label for d in processes_deadlines_info]

    # Build rows
    threads_rows = build_threads_rows(
        threads_dirs,
        perf_threads,
        points_info,
        copying_cfg,
        threads_deadlines_info,
        eff_num_proc,
        REPO_SALT,
    )
    processes_rows = build_process_rows(
        processes_dirs,
        perf_processes,
        points_info,
        copying_cfg,
        processes_deadlines_info,
        eff_num_proc,
        REPO_SALT,
    )

    css = _load_css()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    threads_html = render_threads_page(
        threads_rows,
        threads_deadlines_labels,
        generated_at,
        css,
        texts=TEXT,
        repo_salt=REPO_SALT,
        threads_vmax=threads_vmax,
    )
    processes_html = render_processes_page(
        processes_rows,
        processes_deadlines_labels,
        generated_at,
        css,
        texts=TEXT,
        repo_salt=REPO_SALT,
        proc_vmaxes=proc_vmaxes,
    )

    (output_dir / "threads.html").write_text(threads_html, encoding="utf-8")
    (output_dir / "processes.html").write_text(processes_html, encoding="utf-8")

    # Per-group pages
    threads_groups = []
    for g in _extract_groups(threads_dirs):
        filtered = {
            k: v
            for k, v in threads_dirs.items()
            if (TASKS_DIR / k / "info.json").exists() and _group_of(k) == g
        }
        rows = build_threads_rows(
            filtered,
            perf_threads,
            points_info,
            copying_cfg,
            threads_deadlines_info,
            eff_num_proc,
            REPO_SALT,
        )
        html = render_threads_page(
            rows,
            threads_deadlines_labels,
            generated_at,
            css,
            texts=TEXT,
            repo_salt=REPO_SALT,
            threads_vmax=threads_vmax,
        )
        fname = f"threads_{_slugify(g)}.html"
        (output_dir / fname).write_text(html, encoding="utf-8")
        threads_groups.append({"href": fname, "title": g})

    processes_groups = []
    for g in _extract_groups(processes_dirs):
        filtered = {
            k: v
            for k, v in processes_dirs.items()
            if (TASKS_DIR / k / "info.json").exists() and _group_of(k) == g
        }
        rows = build_process_rows(
            filtered,
            perf_processes,
            points_info,
            copying_cfg,
            processes_deadlines_info,
            eff_num_proc,
            REPO_SALT,
        )
        html = render_processes_page(
            rows,
            processes_deadlines_labels,
            generated_at,
            css,
            texts=TEXT,
            repo_salt=REPO_SALT,
            proc_vmaxes=proc_vmaxes,
        )
        fname = f"processes_{_slugify(g)}.html"
        (output_dir / fname).write_text(html, encoding="utf-8")
        processes_groups.append({"href": fname, "title": g})

    # Variants lookup page
    variant_rows = []
    for raw in args.variant:
        parts = [p.strip() for p in raw.split(";")]
        while len(parts) < 4:
            parts.append("")
        last, first, middle, group = parts[:4]
        stud = {
            "last_name": last,
            "first_name": first,
            "middle_name": middle,
            "group_number": group,
        }
        name_html = "<br/>".join([p for p in [last, first, middle] if p]) or "—"
        variant_rows.append(
            {
                "name": name_html,
                "group": group,
                "threads": compute_variant_threads(stud, REPO_SALT, threads_vmax),
                "processes": compute_variants_processes(stud, REPO_SALT, proc_vmaxes),
            }
        )

    variants_html = render_variants_page(
        variant_rows,
        generated_at,
        css,
        repo_salt=REPO_SALT,
        threads_vmax=threads_vmax,
        proc_vmaxes=proc_vmaxes,
        texts=TEXT,
    )
    (output_dir / "variants.html").write_text(variants_html, encoding="utf-8")

    # Static assets (JS/CSS)
    static_src = SCRIPT_DIR / "static"
    static_dst = output_dir / "static"
    if static_dst.exists():
        shutil.rmtree(static_dst)
    if static_src.exists():
        shutil.copytree(static_src, static_dst)

    index_html = render_index_page(
        threads_groups,
        processes_groups,
        has_variants_page=True,
        generated_at=generated_at,
        inline_css=css,
        texts=TEXT,
    )
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")

    logger.info("Scoreboard generated to %s", output_dir)


def _group_of(dir_name: str) -> str | None:
    info = TASKS_DIR / dir_name / "info.json"
    if not info.exists():
        return None
    try:
        import json

        with open(info, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("student", {}).get("group_number")
    except Exception:
        return None


def _slugify(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(text))


if __name__ == "__main__":
    main()
