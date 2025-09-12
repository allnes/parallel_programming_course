#!/usr/bin/env python3
import pathlib, datetime

PROFILES = pathlib.Path("docs/scoreboard/profiles")
OUT_MD   = pathlib.Path("docs/scoreboard/README.md")

def main():
    PROFILES.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(p for p in PROFILES.glob("*.html"))
    lines = [
      "# Scoreboard\n",
      "_Профили выполнений (microprofile). Таблица производительности отключена._\n\n",
      f"Generated: {datetime.datetime.utcnow().isoformat()}Z\n\n",
    ]
    if not items:
        lines.append("> Profiles not found.\n")
    else:
        lines.append("## Profiles\n\n")
        for p in items:
            lines.append(f"- [{p.name}]({p.name})\n")
    OUT_MD.write_text("".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()

