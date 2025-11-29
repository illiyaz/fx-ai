from pydantic import BaseModel, Field
from typing import List, Literal

ShockLevel = Literal["none", "caution", "high", "critical"]

class Prediction(BaseModel):
    ts: str
    pair: str
    horizon: str
    prob_up: float
    exp_delta_bps: float = Field(alias="exp_delta_bps")
    p10: float
    p90: float
    confidence: float
    model_id: str
    features_json: str | None = None

class Event(BaseModel):
    ts: str
    src: str
    headline: str
    event_type: str
    region: str | None = None
    country: str | None = None
    severity: int
    direction: Literal["USD_positive", "USD_negative", "mixed", "unknown"]
    pairs: List[str]
    impact_score: float
    confidence: float

class Shock(BaseModel):
    ts: str
    pair: str
    r5m: float
    volp: float
    spreadp: float
    jump_sigma: float
    level: ShockLevel
    reason: str

class Decision(BaseModel):
    ts: str
    pair: str
    horizon: str
    prior_prob_up: float
    posterior_prob_up: float
    range_p10: float
    range_p90: float
    shock_level: ShockLevel
    event_impact: float
    recommendation: Literal["NOW", "WAIT", "PARTIAL"]
    explanation: str
    policy_version: str