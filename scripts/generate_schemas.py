import json
from pathlib import Path

from consignai.domain.schemas import record_adapter

Path("data/schemas/record.schema.json").write_text(json.dumps(record_adapter.json_schema(), indent=2) + "\n")
