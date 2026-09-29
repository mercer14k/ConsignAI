"""Persistent weekly jobs, called by the single API process. No paid scheduler."""

import json
import logging
from datetime import datetime, timezone

from consignai.services.analysis import run_analysis
from consignai.services.ingestion import now


def weekly_job(store, at=None):
    at = at or datetime.now(timezone.utc)
    year, week, _ = at.isocalendar()
    period = f"{year}-W{week:02}"
    with store.lock:
        if store.query("SELECT period FROM jobs WHERE period=?", (period,)):
            return None
        run = run_analysis(store)
        with store.connect() as conn:
            conn.execute("INSERT INTO jobs VALUES (?,?,?)", (period, run["id"], now()))
        logging.getLogger("consignai.jobs").info(
            json.dumps(
                {
                    "event": "weekly_analysis",
                    "period": period,
                    "run_id": run["id"],
                    "algorithm_version": run["algorithm_version"],
                }
            )
        )
        return run
