# Scoreboard

Static HTML generator for the course scoreboard. All calculations happen in Python; a small bundled JS
snippet is used only for client-side variant calculation.

Key modules (object-oriented):

- `scoreboard.py` — aggregates tasks/students, builds rows, exposes deadlines/variants.
- `tasks.py` — domain model for `Task` with concrete `ThreadTask`/`ProcessTask` and scoring rules.
- `student.py` — student entity holding submissions and caching computed scores.

## Usage

```bash
pip install -r requirements.txt
python main.py -o build/html
```

Generated files: `index.html`, `threads.html`, `processes.html` and optional per-group pages.

## Configuration

- `data/points-info.json` — max points, variants, performance scale
- `data/deadlines.json` — deadline offsets/labels for display and penalty
- `data/copying.json` — flagged submissions per task (with coefficient in `points-info.json`)

## Testing

```bash
pip install -r tests/requirements.txt
pytest -v
```

## Notes

- Threads deadlines are auto-distributed across 1 Feb → 15 May; processes across 15 Oct → 14 Dec, with
  per-task shifts from `deadlines.json`.
- CSS is bundled locally (no CDN); HTML pages remain self-contained, with JS limited to the variant calculator.
