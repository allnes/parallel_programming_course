# Scoreboard

Static HTML generator for the course scoreboard. All calculations happen in Python; the output pages are
offline-ready and contain no JavaScript.

## Usage

```bash
pip install -r requirements.txt
python main.py -o build/html
```

Generated files: `index.html`, `threads.html`, `processes.html` and optional per-group pages.

## Configuration

- `data/points-info.yml` — max points, variants, performance scale
- `data/deadlines.yml` — deadline offsets/labels for display and penalty
- `data/copying.yml` — flagged submissions per task (with coefficient in `points-info.yml`)

## Testing

```bash
pip install -r tests/requirements.txt
pytest -v
```

## Notes

- Threads deadlines are auto-distributed across 1 Feb → 15 May; processes across 15 Oct → 14 Dec, with
  per-task shifts from `deadlines.yml`.
- CSS is bundled locally (no CDN, no JS); HTML pages remain self-contained for offline use.
