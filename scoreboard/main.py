"""CLI entrypoint to build static scoreboard HTML pages."""

from __future__ import annotations

import argparse
import logging
import shutil
from datetime import datetime
from pathlib import Path

from builder import load_scoreboard
from data_loader import SCRIPT_DIR
from html_renderer import (
    render_index_page,
    render_processes_page,
    render_threads_page,
    render_variants_page,
)
from student import Student
from texts import TEXT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = SCRIPT_DIR.parent.resolve()
REPO_SALT = f"learning_process/{REPO_ROOT.name}"


def _load_css() -> str:
    css_path = SCRIPT_DIR / "static" / "main.css"
    if not css_path.exists():
        return ""
    return css_path.read_text(encoding="utf-8")


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

    board = load_scoreboard(repo_salt=REPO_SALT)

    css = _load_css()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    threads_rows = board.build_threads_rows()
    processes_rows = board.build_process_rows()

    threads_html = render_threads_page(
        threads_rows,
        board.threads_deadline_labels,
        generated_at,
        css,
        texts=TEXT,
        repo_salt=REPO_SALT,
        threads_vmax=int(
            (board.points_info.get("threads", {}) or {}).get("variants_max", 1)
        ),
        thread_tasks=board.thread_tasks,
    )
    proc_vmaxes = [task.variants_max for task in board.process_tasks]
    processes_html = render_processes_page(
        processes_rows,
        board.processes_deadline_labels,
        generated_at,
        css,
        texts=TEXT,
        repo_salt=REPO_SALT,
        proc_vmaxes=proc_vmaxes,
        proc_tasks=board.process_tasks,
    )

    (output_dir / "threads.html").write_text(threads_html, encoding="utf-8")
    (output_dir / "processes.html").write_text(processes_html, encoding="utf-8")

    # Per-group pages
    threads_groups = []
    for group in board.groups_threads():
        rows = board.threads_rows_for_group(group)
        html = render_threads_page(
            rows,
            board.threads_deadline_labels,
            generated_at,
            css,
            texts=TEXT,
            repo_salt=REPO_SALT,
            threads_vmax=int(
                (board.points_info.get("threads", {}) or {}).get("variants_max", 1)
            ),
            thread_tasks=board.thread_tasks,
        )
        fname = f"threads_{_slugify(group)}.html"
        (output_dir / fname).write_text(html, encoding="utf-8")
        threads_groups.append({"href": fname, "title": group})

    processes_groups = []
    for group in board.groups_processes():
        rows = board.processes_rows_for_group(group)
        html = render_processes_page(
            rows,
            board.processes_deadline_labels,
            generated_at,
            css,
            texts=TEXT,
            repo_salt=REPO_SALT,
            proc_vmaxes=proc_vmaxes,
            proc_tasks=board.process_tasks,
        )
        fname = f"processes_{_slugify(group)}.html"
        (output_dir / fname).write_text(html, encoding="utf-8")
        processes_groups.append({"href": fname, "title": group})

    # Variants lookup page (server-side, without JS)
    variant_rows = []
    for raw in args.variant:
        parts = [p.strip() for p in raw.split(";")]
        while len(parts) < 4:
            parts.append("")
        last, first, middle, group = parts[:4]
        group = group.upper()
        student = Student(
            last_name=last, first_name=first, middle_name=middle, group_number=group
        )
        name_html = student.display_name
        variant_rows.append(
            {
                "name": name_html,
                "group": group,
                "threads": board.thread_variant(student),
                "processes": board.process_variants(student),
            }
        )

    variants_html = render_variants_page(
        variant_rows,
        generated_at,
        css,
        repo_salt=REPO_SALT,
        threads_vmax=int(
            (board.points_info.get("threads", {}) or {}).get("variants_max", 1)
        ),
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


def _slugify(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(text))


if __name__ == "__main__":
    main()
