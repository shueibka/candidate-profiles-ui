#!/usr/bin/env python3
# backend/export_profiles.py

import argparse
import json
from pathlib import Path

from db_connection import get_session
from models import CandidateProfilesJoined

FIELDS_TO_EXPORT = [
    "about",
    "experiences",
    "degrees",
    "certifications",
    "languages",
    "courses",
    "skills",
]

def main():
    parser = argparse.ArgumentParser(
        description="Export select candidate profile fields as JSON"
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path("candidate_profiles_export.json"),
        help="Output JSON file path"
    )
    args = parser.parse_args()

    session = get_session()
    try:
        profiles = session.query(CandidateProfilesJoined).all()
        if not profiles:
            print("⚠️ No candidate profiles found.")
            return

        result = []
        for p in profiles:
            entry = {"record_id": p.record_id}
            for field in FIELDS_TO_EXPORT:
                # if the attribute exists and is not None/empty, else empty string
                entry[field] = getattr(p, field) or ""
            result.append(entry)

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"✅ Exported {len(result)} profiles to {args.out}")

    except Exception as e:
        print(f"❌ Error during export: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
