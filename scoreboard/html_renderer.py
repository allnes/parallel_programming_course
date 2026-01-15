"""HTML rendering helpers using Jinja2 templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_threads_page(
    rows: List[Any],
    deadlines: Dict[str, str],
    generated_at: str,
    inline_css: str,
    texts: dict,
    repo_salt: str,
    threads_vmax: int,
    thread_tasks: List[Any],
) -> str:
    env = _environment()
    template = env.get_template("threads_table.html.j2")
    return template.render(
        rows=rows,
        deadlines=deadlines,
        generated_at=generated_at,
        inline_css=inline_css,
        t=texts,
        repo_salt=repo_salt,
        threads_vmax=threads_vmax,
        thread_tasks=thread_tasks,
    )


def render_processes_page(
    rows: List[Any],
    deadlines: List[str],
    generated_at: str,
    inline_css: str,
    texts: dict,
    repo_salt: str,
    proc_vmaxes: list[int],
    proc_tasks: List[Any],
) -> str:
    env = _environment()
    template = env.get_template("processes_table.html.j2")
    return template.render(
        rows=rows,
        deadlines=deadlines,
        generated_at=generated_at,
        inline_css=inline_css,
        t=texts,
        repo_salt=repo_salt,
        proc_vmaxes=proc_vmaxes,
        proc_tasks=proc_tasks,
    )


def render_index_page(
    threads_groups: List[dict],
    processes_groups: List[dict],
    has_variants_page: bool,
    generated_at: str,
    inline_css: str,
    texts: dict,
) -> str:
    env = _environment()
    template = env.get_template("index_menu.html.j2")
    return template.render(
        threads_groups=threads_groups,
        processes_groups=processes_groups,
        has_variants_page=has_variants_page,
        generated_at=generated_at,
        inline_css=inline_css,
        t=texts,
    )


def render_variants_page(
    rows: List[dict],
    generated_at: str,
    inline_css: str,
    repo_salt: str,
    threads_vmax: int,
    proc_vmaxes: list[int],
    texts: dict,
) -> str:
    env = _environment()
    template = env.get_template("variants.html.j2")
    return template.render(
        rows=rows,
        generated_at=generated_at,
        inline_css=inline_css,
        repo_salt=repo_salt,
        threads_vmax=threads_vmax,
        proc_vmaxes=proc_vmaxes,
        t=texts,
    )


__all__ = [
    "render_threads_page",
    "render_processes_page",
    "render_index_page",
    "render_variants_page",
]
