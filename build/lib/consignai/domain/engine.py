"""Deterministic accounting, robust demand estimates and constrained transfer proposals."""

import math
from datetime import date, timedelta

import numpy as np

ALGORITHM_VERSION = "ledger-1.0/robust-mean-1.0/rules-1.0"
PARAMETERS = {
    "lookback_days": 28,
    "inactive_days": 60,
    "stale_after_days": 2,
    "donor_cover_days": 45,
    "recipient_cover_days": 21,
    "transfer_lead_days": 2,
    "spike_min_units": 8,
    "spike_mad_multiplier": 6,
}


def forecast(history):
    """Winsorized calendar-day mean. Missing days must be handled by the caller."""
    a = np.asarray(history, dtype=float)
    if len(a) < 28:
        return {"daily_demand": None, "method": "insufficient_history", "sample_days": len(a)}
    a = a[-28:]
    ceiling = float(np.quantile(a, 0.95))
    return {
        "daily_demand": round(float(np.minimum(a, ceiling).mean()), 4),
        "method": "winsorized_28d_mean",
        "sample_days": 28,
    }


def detect(position, as_of):
    """Returns multiple independent exceptions. No synthetic labels enter this function."""
    p = position
    findings = []

    def add(kind, severity, title, detail, evidence=None):
        findings.append(
            {
                "id": f"{as_of}:{p['location_id']}:{p['sku']}:{kind}",
                "kind": kind,
                "severity": severity,
                "title": title,
                "detail": detail,
                "location_id": p["location_id"],
                "location_name": p["location_name"],
                "market": p["market"],
                "sku": p["sku"],
                "material_name": p["material_name"],
                "category": p["category"],
                "unit": p["unit"],
                "variance": p["variance"],
                "value_cents": abs(p["variance"]) * p["unit_cost_cents"]
                if kind == "variance"
                else p["on_hand"] * p["unit_cost_cents"],
                "days_of_supply": p["days_of_supply"],
                "evidence_ids": evidence or [p["opening_id"], p["snapshot_id"]],
            }
        )

    if p["snapshot_age_days"] > 2:
        add(
            "stale",
            "high",
            "Stock count is out of date",
            f"Last reported {p['snapshot_day']}; current inventory is unknown.",
        )
        return findings
    if p["variance"]:
        add(
            "variance",
            "critical" if abs(p["variance"]) >= 10 else "high",
            "Unexplained stock variance",
            f"Expected {p['expected']} {p['unit']}; reported {p['on_hand']}. Difference {p['variance']:+d}. Investigate the ledger and physical count.",
        )
    if p["reserved"] > p["on_hand"]:
        add(
            "overallocated",
            "high",
            "Reservations exceed reported stock",
            f"{p['reserved']} reserved against {p['on_hand']} on hand.",
        )
    if p["location_kind"] in ("contractor", "field"):
        if p["history_days"] >= 60 and p["days_inactive"] >= 60 and p["on_hand"] > 0:
            add(
                "inactive",
                "medium",
                "Stock without recent consumption",
                f"No recorded consumption for {p['days_inactive']} days. Validate future project need before recovering stock.",
            )
        if p["days_of_supply"] is not None and p["days_of_supply"] < p["lead_time_days"]:
            add(
                "shortage",
                "critical" if p["days_of_supply"] < 3 else "high",
                "Coverage below replenishment lead time",
                f"{p['days_of_supply']:.1f} days of available supply against {p['lead_time_days']} days replenishment lead time.",
            )
        h = p["history"]
        if len(h) >= 28 and p["history_complete"]:
            baseline = np.asarray(h[-28:-1])
            median = float(np.median(baseline))
            mad = float(np.median(abs(baseline - median)))
            threshold = median + max(8, 6 * 1.4826 * mad)
            if h[-1] > threshold:
                add(
                    "usage_spike",
                    "high",
                    "Consumption outside the recent pattern",
                    f"{h[-1]} units used on the analysis date; median {median:.1f}, robust threshold {threshold:.1f}.",
                    p["recent_usage_ids"] or None,
                )
    return findings


def recommend_transfers(positions):
    """Greedy proposals with shared donor/capacity budgets. Does not move stock."""
    proposals = []
    surplus = {}
    capacity = {}
    for p in positions:
        capacity.setdefault(p["location_id"], p["capacity_units"])
        capacity[p["location_id"]] -= p["on_hand"]
        demand = p["daily_demand"] or 0
        reserve = max(25, math.ceil(demand * 45))
        eligible = p["transfer_enabled"] and p["snapshot_age_days"] <= 2 and p["variance"] == 0
        # Missing history is never interpreted as zero contractor demand.
        eligible = eligible and (p["location_kind"] == "warehouse" or p["daily_demand"] is not None)
        surplus[(p["location_id"], p["sku"])] = max(0, p["available"] - reserve) if eligible else 0
    recipients = sorted(
        (
            p
            for p in positions
            if p["days_of_supply"] is not None
            and p["days_of_supply"] < p["lead_time_days"]
            and p["variance"] == 0
            and p["snapshot_age_days"] <= 2
            and p["transfer_enabled"]
            and p["reserved"] <= p["on_hand"]
        ),
        key=lambda p: (p["days_of_supply"], p["location_id"], p["sku"]),
    )
    for target in recipients:
        need = max(
            0, math.ceil(target["daily_demand"] * max(21, target["lead_time_days"] + 7)) - target["available"]
        )
        for donor in sorted(
            positions, key=lambda p: (-surplus[(p["location_id"], p["sku"])], p["location_id"])
        ):
            key = (donor["location_id"], donor["sku"])
            if (
                donor["sku"] != target["sku"]
                or donor["location_id"] == target["location_id"]
                or donor["market"] != target["market"]
                or donor["owner_id"] != target["owner_id"]
            ):
                continue
            qty = min(need, surplus[key], max(0, capacity[target["location_id"]]))
            qty = qty // target["pack_size"] * target["pack_size"]
            if qty <= 0:
                continue
            surplus[key] -= qty
            capacity[target["location_id"]] -= qty
            need -= qty
            proposals.append(
                {
                    "id": f"move:{donor['location_id']}:{target['location_id']}:{target['sku']}",
                    "from_location": donor["location_id"],
                    "from_name": donor["location_name"],
                    "to_location": target["location_id"],
                    "to_name": target["location_name"],
                    "sku": target["sku"],
                    "material_name": target["material_name"],
                    "market": target["market"],
                    "quantity": qty,
                    "unit": target["unit"],
                    "value_cents": qty * target["unit_cost_cents"],
                    "coverage_before": target["days_of_supply"],
                    "coverage_after": round(
                        (
                            target["available"]
                            + sum(
                                x["quantity"]
                                for x in proposals
                                if x["to_location"] == target["location_id"] and x["sku"] == target["sku"]
                            )
                            + qty
                        )
                        / target["daily_demand"],
                        1,
                    ),
                    "transfer_lead_days": 2,
                    "expedite_required": target["days_of_supply"] < 2,
                    "constraints": [
                        "same SKU & owner",
                        "same market",
                        "donor safety stock retained",
                        "reservations protected",
                        "recipient capacity",
                        "pack multiple",
                    ],
                    "status": "proposal",
                    "evidence_ids": [donor["snapshot_id"], target["snapshot_id"]],
                }
            )
            if need < target["pack_size"]:
                break
    return proposals


def calendar_days(end, n=28):
    day = date.fromisoformat(str(end))
    return [str(day - timedelta(days=i)) for i in reversed(range(n))]
