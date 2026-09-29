import hashlib
import json
import time
import uuid
from collections import Counter, defaultdict
from datetime import date, timedelta

from consignai.domain.engine import (
    ALGORITHM_VERSION,
    PARAMETERS,
    calendar_days,
    detect,
    forecast,
    recommend_transfers,
)
from consignai.services.ingestion import now


def compute(store, as_of=None):
    started = time.perf_counter()
    if as_of is None:
        as_of = store.query("SELECT MAX(day) AS day FROM snapshots")[0]["day"]
    if not as_of:
        raise ValueError("No snapshots available; import stock evidence first")
    as_of = str(as_of)
    end = date.fromisoformat(as_of)
    since = str(end - timedelta(days=89))
    # One database snapshot prevents a mixed view if an import commits concurrently.
    with store.connect(readonly=True) as conn:
        conn.execute("BEGIN")
        version = conn.execute("SELECT value FROM metadata WHERE key='data_version'").fetchone()[0]
        rows = conn.execute(
            """
        WITH ranked AS (
          SELECT *, ROW_NUMBER() OVER(PARTITION BY location_id,sku ORDER BY day) first_n,
            ROW_NUMBER() OVER(PARTITION BY location_id,sku ORDER BY day DESC) last_n
          FROM snapshots WHERE day<=?
        )
        SELECT s.location_id,s.sku,s.on_hand,s.reserved,s.day snapshot_day,s.id snapshot_id,
          b.day opening_day,b.id opening_id,b.on_hand opening,
          l.name location_name,l.kind location_kind,l.market,l.owner_id,l.capacity_units,l.transfer_enabled,
          m.name material_name,m.category,m.unit,m.unit_cost_cents,m.lead_time_days,m.pack_size,
          COALESCE(SUM(g.delta),0) net_movement,
          MAX(CASE WHEN g.usage>0 THEN g.day END) last_usage,
          COUNT(g.movement_id) movement_count
        FROM ranked s JOIN ranked b ON s.location_id=b.location_id AND s.sku=b.sku AND b.first_n=1
        JOIN locations l ON s.location_id=l.id JOIN materials m ON s.sku=m.id
        LEFT JOIN legs g ON g.location_id=s.location_id AND g.sku=s.sku AND g.day>b.day AND g.day<=s.day
        WHERE s.last_n=1 AND l.kind!='enterprise' GROUP BY s.location_id,s.sku
        """,
            (as_of,),
        ).fetchall()
        daily = conn.execute(
            "SELECT location_id,sku,day,SUM(usage) units FROM legs WHERE day BETWEEN ? AND ? AND usage>0 GROUP BY location_id,sku,day",
            (since, as_of),
        ).fetchall()
        coverage = conn.execute(
            "SELECT location_id,sku,COUNT(*) n,SUM(CASE WHEN on_hand=0 THEN 1 ELSE 0 END) censored FROM snapshots WHERE day BETWEEN ? AND ? GROUP BY location_id,sku",
            (str(end - timedelta(days=27)), as_of),
        ).fetchall()
        latest_usage = conn.execute(
            "SELECT movement_id,location_id,sku FROM legs WHERE day=? AND usage>0", (as_of,)
        ).fetchall()
        trend = [
            dict(r)
            for r in conn.execute(
                "SELECT s.day,SUM(s.on_hand*m.unit_cost_cents) value_cents,SUM(s.on_hand) units FROM snapshots s JOIN materials m ON s.sku=m.id WHERE s.day BETWEEN ? AND ? GROUP BY s.day ORDER BY s.day",
                (since, as_of),
            )
        ]
        counts = {
            r["type"]: r["n"] for r in conn.execute("SELECT type,COUNT(*) n FROM records GROUP BY type")
        }
        contractors = conn.execute("SELECT COUNT(*) FROM locations WHERE kind='contractor'").fetchone()[0]
        source_ids = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT json_extract(body,'$.source_id') FROM records WHERE type='location'"
            )
        ]
    if not rows:
        raise ValueError("No stock evidence at or before this date")
    histories = defaultdict(dict)
    for r in daily:
        histories[(r["location_id"], r["sku"])][r["day"]] = r["units"]
    cov = {(r["location_id"], r["sku"]): dict(r) for r in coverage}
    usage_ids = defaultdict(list)
    for r in latest_usage:
        usage_ids[(r["location_id"], r["sku"])].append(r["movement_id"])
    positions = []
    alerts = []
    for r in rows:
        p = dict(r)
        key = (p["location_id"], p["sku"])
        p["history_days"] = (end - date.fromisoformat(p["opening_day"])).days
        p["snapshot_age_days"] = (end - date.fromisoformat(p["snapshot_day"])).days
        p["days_inactive"] = (end - date.fromisoformat(p["last_usage"] or p["opening_day"])).days
        p["expected"] = p["opening"] + p["net_movement"]
        p["variance"] = p["on_hand"] - p["expected"]
        p["available"] = max(0, p["on_hand"] - p["reserved"])
        p["history_complete"] = cov.get(key, {}).get("n", 0) == 28 and p["history_days"] >= 28
        p["censored_days"] = cov.get(key, {}).get("censored", 0)
        p["history"] = [histories[key].get(d, 0) for d in calendar_days(as_of)]
        p["recent_usage_ids"] = usage_ids[key][:28]
        model = forecast(p["history"] if p["history_complete"] else [])
        p.update(model)
        if p["location_kind"] == "warehouse":
            p["daily_demand"] = None
            p["method"] = "warehouse_not_forecast"
        p["forecast_quality"] = "censored_by_stockout" if p["censored_days"] else "observed_consumption"
        p["days_of_supply"] = (
            round(p["available"] / p["daily_demand"], 1)
            if p["daily_demand"] and p["snapshot_age_days"] <= 2
            else None
        )
        found = detect(p, as_of)
        p["risk_kinds"] = [a["kind"] for a in found]
        p["risk_score"] = min(
            100, sum({"critical": 50, "high": 30, "medium": 15}[a["severity"]] for a in found)
        )
        positions.append(p)
        alerts.extend(found)
    order = {"critical": 0, "high": 1, "medium": 2}
    alerts.sort(key=lambda a: (order[a["severity"]], -a["value_cents"], a["id"]))
    transfers = recommend_transfers(positions)

    def aggregate_cover(group):
        usable = [p for p in group if p["daily_demand"] is not None and p["snapshot_age_days"] <= 2]
        demand = sum(p["daily_demand"] for p in usable)
        return round(sum(p["available"] for p in usable) / demand, 1) if demand else None

    contractor_rollups = []
    for location in sorted({p["location_id"] for p in positions if p["location_kind"] == "contractor"}):
        group = [p for p in positions if p["location_id"] == location]
        contractor_rollups.append(
            {
                "location_id": location,
                "location_name": group[0]["location_name"],
                "market": group[0]["market"],
                "risk_score": sum(p["risk_score"] for p in group),
                "days_of_supply": aggregate_cover(group),
                "materials": [
                    {"sku": p["sku"], "name": p["material_name"], "risk_score": p["risk_score"]}
                    for p in sorted(group, key=lambda x: (-x["risk_score"], x["sku"]))
                ],
            }
        )
    contractor_rollups.sort(key=lambda p: (-p["risk_score"], p["location_id"]))
    markets = []
    for market in sorted({p["market"] for p in positions}):
        ps = [p for p in positions if p["market"] == market]
        aa = [a for a in alerts if a["market"] == market]
        markets.append(
            {
                "market": market,
                "value_cents": sum(p["on_hand"] * p["unit_cost_cents"] for p in ps),
                "exceptions": len(aa),
                "categories": {
                    c: sum(p["risk_score"] for p in ps if p["category"] == c)
                    for c in sorted({p["category"] for p in ps})
                },
                "shortages": sum(a["kind"] == "shortage" for a in aa),
                "days_of_supply": aggregate_cover(ps),
            }
        )
    counts_alert = Counter(a["kind"] for a in alerts)
    summary = {
        "inventory_value_cents": sum(p["on_hand"] * p["unit_cost_cents"] for p in positions),
        "variance_value_cents": sum(abs(p["variance"]) * p["unit_cost_cents"] for p in positions),
        "exception_count": len(alerts),
        "shortage_count": counts_alert["shortage"],
        "contractors": contractors,
        "skus": counts.get("material", 0),
        "positions": len(positions),
        "record_count": sum(counts.values()),
        "movement_count": counts.get("movement", 0),
        "snapshot_count": counts.get("snapshot", 0),
        "redistribution_value_cents": sum(p["value_cents"] for p in transfers),
        "anomaly_counts": dict(counts_alert),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "sources": source_ids,
    }
    return {
        "id": str(uuid.uuid4()),
        "created_at": now(),
        "as_of": as_of,
        "dataset_version": str(version),
        "algorithm_version": ALGORITHM_VERSION,
        "parameters": PARAMETERS,
        "summary": summary,
        "positions": positions,
        "alerts": alerts,
        "transfers": transfers,
        "markets": markets,
        "contractors": contractor_rollups,
        "trend": trend,
    }


def run_analysis(store, as_of=None):
    with store.lock:
        result = compute(store, as_of)
        with store.connect() as conn:
            conn.execute(
                "INSERT INTO runs VALUES (?,?,?,?)",
                (result["id"], result["created_at"], result["as_of"], json.dumps(result)),
            )
    return result


def state_digest(run):
    return hashlib.sha256(
        json.dumps({k: run[k] for k in ("positions", "alerts", "transfers")}, sort_keys=True).encode()
    ).hexdigest()
