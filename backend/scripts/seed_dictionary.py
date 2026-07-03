"""Seed kamus isyarat dari data mock frontend (constants/MockData.ts).

Idempoten: entri dengan id yang sama tidak diduplikasi.

Jalankan dari folder backend/:
    python scripts/seed_dictionary.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mobile.db import SessionLocal, init_db  # noqa: E402
from app.mobile.models import DictionaryEntry  # noqa: E402

MOCKDATA_PATH = (
    Path(__file__).resolve().parents[2] / "amertasign" / "constants" / "MockData.ts"
)

NODE_SNIPPET = """
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8')
  .replace(/import[^;]+;/g, '')
  .replace(/export const (\w+)[^=]*=/g, 'globalThis.$1 =');
eval(src);
process.stdout.write(JSON.stringify(globalThis.dictionaryEntries));
"""


def parse_mock_entries(path: Path) -> list[dict]:
    """Evaluasi array dictionaryEntries dari file TypeScript via Node.js."""
    result = subprocess.run(
        ["node", "-e", NODE_SNIPPET, str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def main() -> None:
    init_db()
    entries = parse_mock_entries(MOCKDATA_PATH)

    created = 0
    with SessionLocal() as db:
        for item in entries:
            if db.get(DictionaryEntry, item["id"]):
                continue
            db.add(
                DictionaryEntry(
                    id=item["id"],
                    word=item["word"],
                    category=item["category"],
                    type=item["type"],
                    description=item.get("description", ""),
                    image_url=item.get("imageUrl", ""),
                    video_url=item.get("videoUrl", ""),
                )
            )
            created += 1
        db.commit()

    print(f"Selesai: {created} entri baru, total sumber {len(entries)} entri.")


if __name__ == "__main__":
    main()
