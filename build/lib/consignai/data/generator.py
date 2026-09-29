"""Sparse realistic network; full default is 100 contractors, 500 SKUs, 365 days.

Seed labels are external to the records and never available to the detector.
Opening snapshots are the accounting anchors; movements start on the next day.
"""

import gzip
import json
import random
from datetime import date, timedelta
from pathlib import Path

MARKETS = ["Chicago", "Dallas", "Atlanta", "Phoenix", "Denver"]
CATEGORIES = ["Fiber & cable", "Network hardware", "Power systems", "Site materials", "Safety & tools"]
MATERIALS = [
    "Fiber drop cable",
    "Optical splitter",
    "Power distribution unit",
    "Mounting bracket",
    "Grounding kit",
]
CONTRACTORS = [
    "Northline",
    "Apex",
    "Meridian",
    "Summit",
    "Vector",
    "Atlas",
    "Frontier",
    "Sterling",
    "Pioneer",
    "Keystone",
]


def generate(seed=42, contractors=100, skus=500, days=365, slots=8):
    if contractors < 1 or skus < 1 or days < 35 or slots < 1:
        raise ValueError("contractors/skus/slots must be positive and days must be >=35")
    rng = random.Random(seed)
    source = f"synthetic-v1-s{seed}-c{contractors}-k{skus}-d{days}-p{slots}"
    start = date(2025, 1, 1)
    end = start + timedelta(days=days - 1)
    meta = {
        "source_id": source,
        "ingested_at": f"{end}T23:59:59+00:00",
        "validation_status": "valid",
        "lineage": {"generator": "v1", "seed": str(seed)},
    }

    def rec(record_type, **fields):
        return {**meta, "record_type": record_type, **fields}

    locations = [
        rec(
            "location",
            id="enterprise",
            name="ConsignAI Network",
            kind="enterprise",
            market="National",
            parent_id=None,
        )
    ]
    for m, market in enumerate(MARKETS):
        locations.append(
            rec(
                "location",
                id=f"wh{m}",
                name=f"{market} Distribution",
                kind="warehouse",
                market=market,
                parent_id="enterprise",
            )
        )
    for i in range(contractors):
        locations.append(
            rec(
                "location",
                id=f"c{i:03}",
                name=f"{CONTRACTORS[i % 10]} {i + 1:03}",
                kind="contractor",
                market=MARKETS[i % 5],
                parent_id="enterprise",
                capacity_units=10000,
            )
        )
    for i in range(max(1, contractors // 10)):
        locations.append(
            rec(
                "location",
                id=f"f{i:03}",
                name=f"Field site {i + 1:03}",
                kind="field",
                market=MARKETS[i % 5],
                parent_id=f"c{i:03}",
                capacity_units=2500,
            )
        )
    yield from locations
    for k in range(skus):
        yield rec(
            "material",
            id=f"sku{k:04}",
            name=f"{MATERIALS[k % 5]} · {k + 1:03}",
            category=CATEGORIES[k % 5],
            unit="m" if k % 5 == 0 else "ea",
            unit_cost_cents=(25 + k % 91) * 100,
            lead_time_days=7 + k % 8,
            pack_size=1 if k % 3 else 5,
        )
    positions = []
    for i in range(contractors):
        for j in range(min(slots, skus)):
            k = (i * min(slots, skus) + j) % skus
            anomaly = (
                ("variance", "usage_spike", "inactive", "shortage", "overallocated")[i % 5]
                if j == 0
                else None
            )
            positions.append(
                {
                    "location": f"c{i:03}",
                    "sku": f"sku{k:04}",
                    "stock": 150,
                    "rate": 2 + k % 5,
                    "anomaly": anomaly,
                    "market": i % 5,
                    "offset": 0,
                }
            )
    for i in range(max(1, contractors // 10)):
        positions.append(
            {
                "location": f"f{i:03}",
                "sku": f"sku{i % skus:04}",
                "stock": 150,
                "rate": 2,
                "anomaly": None,
                "market": i % 5,
                "offset": 0,
            }
        )
    # Warehouses own all SKUs needed in their market, enabling physically balanced issuance.
    warehouse_stock = {(p["market"], p["sku"]): 1500 for p in positions}
    counter = 0
    for d in range(days):
        day = str(start + timedelta(days=d))

        def movement(kind, sku, quantity, src=None, dst=None):
            nonlocal counter
            counter += 1
            return rec(
                "movement",
                id=f"{source}:t{counter:08}",
                day=day,
                sku=sku,
                kind=kind,
                quantity=quantity,
                from_location=src,
                to_location=dst,
                reference=f"SYN-{counter:08}",
            )

        for p in positions:
            if d:
                rate = p["rate"]
                usage = max(0, round(rate + rng.gauss(0, 0.7)))
                if p["anomaly"] == "inactive" and d >= days - 65:
                    usage = 0
                if p["anomaly"] == "usage_spike" and d == days - 1:
                    usage = rate * 12
                shortage = p["anomaly"] == "shortage" and d >= days - 28
                if p["stock"] < rate * 20 and not shortage:
                    qty = rate * 35
                    key = (p["market"], p["sku"])
                    if warehouse_stock[key] < qty + 250:
                        yield movement("receipt", p["sku"], 1500, dst=f"wh{p['market']}")
                        warehouse_stock[key] += 1500
                    yield movement("issue", p["sku"], qty, src=f"wh{p['market']}", dst=p["location"])
                    p["stock"] += qty
                    warehouse_stock[key] -= qty
                if p["anomaly"] == "shortage" and d == days - 8:
                    target = rate * 9
                    delta = target - p["stock"]
                    if delta:
                        yield movement("adjustment", p["sku"], delta, dst=p["location"])
                        p["stock"] = target
                usage = min(usage, max(0, p["stock"] + p["offset"]))
                if usage:
                    yield movement("usage", p["sku"], usage, src=p["location"])
                    p["stock"] -= usage
                if p["anomaly"] == "variance" and d == days - 5:
                    p["offset"] = -min(17, p["stock"])
                # A real transfer between contractor and its field site, with both legs.
            on_hand = max(0, p["stock"] + p["offset"])
            reserved = on_hand + 9 if p["anomaly"] == "overallocated" and d == days - 1 else min(3, on_hand)
            yield rec(
                "snapshot",
                id=f"{source}:s:{p['location']}:{p['sku']}:{d}",
                day=day,
                sku=p["sku"],
                location_id=p["location"],
                on_hand=on_hand,
                reserved=reserved,
            )
        for (market, sku), stock in sorted(warehouse_stock.items()):
            yield rec(
                "snapshot",
                id=f"{source}:s:wh{market}:{sku}:{d}",
                day=day,
                sku=sku,
                location_id=f"wh{market}",
                on_hand=stock,
                reserved=0,
            )


def ground_truth(contractors=100, skus=500, slots=8, **_):
    return [
        {
            "location_id": f"c{i:03}",
            "sku": f"sku{(i * min(slots, skus)) % skus:04}",
            "kind": ("variance", "usage_spike", "inactive", "shortage", "overallocated")[i % 5],
        }
        for i in range(contractors)
    ]


def write_dataset(path: Path, **config):
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if str(path).endswith(".gz") else open
    count = 0
    with opener(path, "wt", encoding="utf-8") as out:
        for record in generate(**config):
            out.write(json.dumps(record, separators=(",", ":")) + "\n")
            count += 1
    path.with_name("ground-truth.json").write_text(json.dumps(ground_truth(**config), indent=2))
    return count
