import argparse
import gzip
import json
from pathlib import Path

from consignai.data.generator import write_dataset
from consignai.data.store import Store
from consignai.services.analysis import run_analysis
from consignai.services.ingestion import ingest


def main():
    parser = argparse.ArgumentParser(prog="consignai")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--output", type=Path, default=Path("data/generated/demo.jsonl.gz"))
    for key, default in (("seed", 42), ("contractors", 100), ("skus", 500), ("days", 365), ("slots", 8)):
        generate.add_argument(f"--{key}", type=int, default=default)
    imp = sub.add_parser("import")
    imp.add_argument("file", type=Path)
    imp.add_argument("--db", default="var/consignai.db")
    analyze = sub.add_parser("analyze")
    analyze.add_argument("--db", default="var/consignai.db")
    analyze.add_argument("--as-of")
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "generate":
        output = args.pop("output")
        print(json.dumps({"path": str(output), "rows": write_dataset(output, **args)}))
    elif command == "import":
        path = args["file"]
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as file:
            result = ingest(Store(args["db"]), (json.loads(line) for line in file if line.strip()), path.name)
        print(json.dumps(result))
        if result["status"] == "rejected":
            raise SystemExit(1)
    else:
        print(json.dumps(run_analysis(Store(args["db"]), args["as_of"])["summary"], indent=2))


if __name__ == "__main__":
    main()
