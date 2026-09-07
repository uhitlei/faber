#!/usr/bin/env python3
"""Avaliar ou selar pacote de requisitos (não aprova G1)."""
import argparse
import json
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from requirements import Invalid, delivery_hash, evaluate, seal


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("report", "seal", "delivery"))
    p.add_argument("folder", type=Path, help="Pasta da demanda ou faber/bootstrap")
    p.add_argument("--write", action="store_true", help="Gravar readiness.json no modo report")
    args = p.parse_args()
    if args.write and args.action != "report":
        p.error("--write somente com report")
    try:
        if args.action == "report":
            report = evaluate(args.folder)
            content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            if args.write:
                (args.folder / "requirements" / "readiness.json").write_text(content, encoding="utf-8")
            print(content, end="")
            return 0 if report["ready"] else 1
        if args.action == "seal":
            print(json.dumps(seal(args.folder), ensure_ascii=False, indent=2))
        else:
            print(delivery_hash(args.folder))
        return 0
    except (Invalid, OSError, ValueError, yaml.YAMLError) as exc:
        print(f"BLOQUEIO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
