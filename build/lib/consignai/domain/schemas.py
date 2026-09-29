"""Typed canonical records. Quantities are integral base units; money is integer cents."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:-]+$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Identifier
    source_id: Identifier
    ingested_at: datetime
    validation_status: Literal["valid"] = "valid"
    lineage: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def timezone_required(self):
        if self.ingested_at.tzinfo is None:
            raise ValueError("ingested_at must include a timezone")
        return self


class Location(Record):
    record_type: Literal["location"] = "location"
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["enterprise", "warehouse", "contractor", "field"]
    market: str = Field(min_length=1, max_length=50)
    owner_id: Identifier = "enterprise"
    parent_id: Identifier | None = None
    capacity_units: int = Field(default=1000000, ge=0)
    transfer_enabled: bool = True


class Material(Record):
    record_type: Literal["material"] = "material"
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    unit: Literal["ea", "m"] = "ea"
    unit_cost_cents: int = Field(ge=0, le=100000000)
    lead_time_days: int = Field(ge=1, le=180)
    pack_size: int = Field(ge=1, le=10000)


class Movement(Record):
    record_type: Literal["movement"] = "movement"
    day: date
    sku: Identifier
    kind: Literal["receipt", "issue", "transfer", "usage", "adjustment"]
    quantity: int = Field(ge=-10000000, le=10000000)
    from_location: Identifier | None = None
    to_location: Identifier | None = None
    reference: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def valid_legs(self):
        if self.kind != "adjustment" and self.quantity <= 0:
            raise ValueError("movement quantity must be positive")
        if self.kind == "adjustment" and self.quantity == 0:
            raise ValueError("adjustment quantity must be nonzero")
        if self.kind in ("receipt", "adjustment") and (not self.to_location or self.from_location):
            raise ValueError("receipt/adjustment needs only to_location")
        if self.kind == "usage" and (not self.from_location or self.to_location):
            raise ValueError("usage needs only from_location")
        if self.kind in ("issue", "transfer") and (
            not self.from_location or not self.to_location or self.from_location == self.to_location
        ):
            raise ValueError("issue/transfer needs two different locations")
        return self


class Snapshot(Record):
    record_type: Literal["snapshot"] = "snapshot"
    day: date
    sku: Identifier
    location_id: Identifier
    on_hand: int = Field(ge=0, le=100000000)
    reserved: int = Field(default=0, ge=0, le=100000000)
    # reserved may exceed on_hand: this is an operational exception, not malformed input.


InputRecord = Annotated[Location | Material | Movement | Snapshot, Field(discriminator="record_type")]
record_adapter = TypeAdapter(InputRecord)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: date | None = None


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["explained", "abstained"]
    summary: str = Field(max_length=800)
    evidence_ids: list[str] = Field(max_length=30)
    next_action: Literal["verify_count", "review_usage", "review_transfer", "collect_evidence"]


class ModelExplanation(Explanation):
    summary: str = Field(max_length=800, pattern=r"^[^0-9]*$")


class ErrorDetail(BaseModel):
    code: str
    message: str
    trace_id: str
    details: list[dict] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Page(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


class RunResponse(BaseModel):
    id: str
    as_of: str
    created_at: str
    dataset_version: str
    algorithm_version: str
    parameters: dict
    summary: dict
    positions: list[dict]
    alerts: list[dict]
    transfers: list[dict]
    markets: list[dict]
    trend: list[dict]


class OverviewResponse(BaseModel):
    id: str
    as_of: date
    created_at: datetime
    dataset_version: str
    algorithm_version: str
    parameters: dict
    summary: dict
    markets: list[dict]
    contractors: list[dict]
    trend: list[dict]
    stale_analysis: bool


class ImportReport(BaseModel):
    id: str
    created_at: datetime
    filename: str
    status: Literal["accepted", "rejected"]
    rows: int
    accepted: int
    duplicates: int
    errors: list[dict]


class EvidenceResponse(BaseModel):
    run_id: str
    position: dict
    snapshots: list[Snapshot]
    movements: list[dict]
    total: int
    offset: int
    limit: int
    alerts: list[dict]


class NarrativeResponse(BaseModel):
    explanation: Explanation
    mode: Literal["abstained", "deterministic", "local_ai", "deterministic_fallback"]
    telemetry: dict


class AnalysisResponse(BaseModel):
    id: str
    as_of: date
    summary: dict
