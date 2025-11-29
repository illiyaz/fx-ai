from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
import structlog 
from datetime import datetime, timezone
import os

from fastapi import Query
from apps.common.clickhouse_client import query_df
from apps.features.featurize import build_features
from apps.models import baselines
from apps.common.clickhouse_client import insert_rows
from apps.models.loader import latest_model_row, load_model_by_id, SkPredictor
from apps.llm.fusion import BayesianFusionEngine, MLPrediction, NewsSentiment
from apps.llm.news_aggregator import get_news_aggregator

class Settings(BaseSettings):
    app_env: str = Field(default="local", validation_alias=AliasChoices("APP_ENV","ENV","ENVIRONMENT"))
    api_key: str = Field(default="changeme-dev-key", validation_alias=AliasChoices("API_KEY","APP_API_KEY"))
    api_port: int = Field(default=9090, validation_alias=AliasChoices("API_PORT","APP_API_PORT"))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True,extra="ignore",)

settings = Settings()
log = structlog.get_logger()

app = FastAPI(title="FX-AI Advisor", version="0.0.1")

# Decision policy knobs (env-overridable)
DECISION_POLICY = os.getenv("DECISION_POLICY", "expected").lower()  # "expected" | "prob"
DECISION_SPREAD_BPS = float(os.getenv("DECISION_SPREAD_BPS", "2.0"))
DECISION_PROB_TH = float(os.getenv("DECISION_PROB_TH", "0.6"))
DECISION_EMBARGO_MIN = int(os.getenv("DECISION_EMBARGO_MIN", "0"))  # minutes; 0 disables embargo

DEFAULT_MODEL_ID = os.getenv("DEFAULT_MODEL_ID")  # optional; when set, API tries to use this model

# Hybrid ML+LLM settings
ENABLE_LLM_FUSION = os.getenv("ENABLE_LLM_FUSION", "true").lower() == "true"
LLM_MAX_WEIGHT = float(os.getenv("LLM_MAX_WEIGHT", "0.4"))
LLM_MIN_CONFIDENCE = float(os.getenv("LLM_MIN_CONFIDENCE", "0.3"))
LLM_HIGH_IMPACT_THRESHOLD = float(os.getenv("LLM_HIGH_IMPACT_THRESHOLD", "7.0"))

# Initialize fusion engine and news aggregator
fusion_engine = BayesianFusionEngine(
    max_llm_weight=LLM_MAX_WEIGHT,
    min_confidence_threshold=LLM_MIN_CONFIDENCE,
    high_impact_threshold=LLM_HIGH_IMPACT_THRESHOLD
) if ENABLE_LLM_FUSION else None

news_aggregator = get_news_aggregator() if ENABLE_LLM_FUSION else None

# --- helpers for direction & action hints ---
def _split_pair(p: str) -> tuple[str, str]:
    p = (p or "").upper()
    return p[:3], p[3:6]


def build_direction_and_hint(pair: str, prob_up: float, expected_bps: float) -> tuple[str, str]:
    """Return (direction, action_hint).
    direction: "UP" if price likely to rise (base strengthens vs quote), else "DOWN".
    action_hint: plain-English guidance depending on direction.
    """
    base, quote = _split_pair(pair)
    # Choose sign primarily from expected move; fall back to prob when expected ~ 0
    sign = expected_bps
    if abs(sign) < 1e-9:
        sign = (2.0 * float(prob_up) - 1.0) * 1e-9  # tiny value with sign of probability
    direction = "UP" if sign >= 0 else "DOWN"

    if direction == "UP":
        hint = (
            f"{base} likely to strengthen vs {quote}. If you need to BUY {base}, "
            f"consider acting sooner; if you plan to SELL {base}, delaying may help."
        )
    else:
        hint = (
            f"{base} likely to weaken vs {quote}. If you need to SELL {base}, "
            f"consider acting sooner; if you plan to BUY {base}, waiting may help."
        )
    return direction, hint

def choose_recommendation(pred: dict, policy: str, spread_bps: float, prob_th: float) -> str:
    """Return "NOW" or "WAIT" based on the chosen policy.
    - policy="expected": act only if |expected_delta_bps| > spread_bps
    - policy="prob": act if prob_up >= prob_th
    """
    try:
        if policy == "expected":
            exp = float(pred.get("expected_delta_bps", pred.get("exp_delta_bps", 0.0)))
            return "NOW" if abs(exp) > float(spread_bps) else "WAIT"
        else:  # prob
            p = float(pred.get("prob_up", 0.5))
            return "NOW" if p >= float(prob_th) else "WAIT"
    except Exception:
        return "WAIT"

def require_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid api key")

@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}

'''
@app.get("/v1/forecast")
async def forecast(pair: str, h: str = "4h", _: None = Depends(require_key)):
    out = forecast_rolling_mean(pair, h)
    return out
'''


@app.get("/v1/forecast")
async def forecast(
    pair: str,
    h: str = "4h",
    policy: str | None = None,
    spread_bps: float | None = None,
    prob_th: float | None = None,
    model_id: str | None = None,
    embargo_min: int | None = None,
    use_hybrid: bool | None = None,  # New: explicitly enable/disable hybrid
    _: None = Depends(require_key),
):
    try:
        start_time = datetime.now()
        
        # Build features
        feats = build_features(pair)
        
        # Resolve model to use (query param wins, else env default, else latest by horizon)
        chosen_model_id = model_id or DEFAULT_MODEL_ID
        model_predictor = None
        if chosen_model_id:
            try:
                bundle = load_model_by_id(chosen_model_id)
                model_predictor = SkPredictor(bundle["model"], bundle["features"])
            except Exception:
                log.warning("model_load_failed", model_id=chosen_model_id)
        if model_predictor is None:
            # try latest by horizon
            row = latest_model_row(h)
            if row is not None:
                try:
                    bundle = load_model_by_id(row["model_id"])  # file name matches model_id
                    model_predictor = SkPredictor(bundle["model"], bundle["features"])
                    chosen_model_id = row["model_id"]
                except Exception:
                    log.warning("model_load_failed_latest", horizon=h)

        if feats is None or feats.empty:
            return {
                "pair": pair, "horizon": h, "prob_up": 0.5, "expected_delta_bps": 0.0,
                "range": {"p10": -5.0, "p90": 5.0}, "confidence": 0.0,
                "recommendation": "PARTIAL", "explanation": ["no features"], "model_id": "baseline_v0"
            }
        
        # Get ML prediction
        if model_predictor is not None:
            pred = model_predictor.predict(feats)
            pred["model_id"] = chosen_model_id or "unknown_lgbm"
        else:
            pred = baselines.predict_rolling_mean(feats)
            pred["model_id"] = "baseline_v0"
        
        # Determine if hybrid mode should be used
        use_hybrid_mode = use_hybrid if use_hybrid is not None else (ENABLE_LLM_FUSION and fusion_engine is not None)
        
        # Initialize hybrid variables
        prob_up_final = float(pred.get("prob_up", 0.5))
        expected_delta_final = float(pred.get("expected_delta_bps", pred.get("exp_delta_bps", 0.0)))
        news_sentiment = None
        fusion_weights = {"ml": 1.0, "llm": 0.0}
        news_summary = None
        
        # Apply hybrid fusion if enabled
        if use_hybrid_mode:
            try:
                # Get recent news sentiment
                news_sentiment = news_aggregator.get_recent_sentiment(pair, lookback_hours=1)
                
                if news_sentiment:
                    # Create ML prediction object
                    ml_pred = MLPrediction(
                        prob_up=prob_up_final,
                        expected_delta_bps=expected_delta_final,
                        confidence=0.65,  # Default ML confidence
                        model_id=pred["model_id"]
                    )
                    
                    # Fuse ML and LLM predictions
                    hybrid_result = fusion_engine.fuse(ml_pred, news_sentiment)
                    
                    # Update final predictions
                    prob_up_final = hybrid_result.prob_up_hybrid
                    expected_delta_final = hybrid_result.expected_delta_hybrid
                    fusion_weights = {
                        "ml": hybrid_result.fusion_weight_ml,
                        "llm": hybrid_result.fusion_weight_llm
                    }
                    news_summary = hybrid_result.news_summary
                    
                    log.info("hybrid_fusion_applied",
                            pair=pair,
                            prob_ml=ml_pred.prob_up,
                            prob_hybrid=prob_up_final,
                            weight_llm=fusion_weights["llm"])
                else:
                    log.debug("no_news_sentiment", pair=pair)
            except Exception as e:
                log.error("hybrid_fusion_error", error=str(e), pair=pair)
                # Fall back to ML-only on error
        
        # Effective knobs (query overrides env defaults)
        eff_policy = (policy or DECISION_POLICY).lower()
        eff_spread = float(spread_bps) if spread_bps is not None else DECISION_SPREAD_BPS
        eff_prob_th = float(prob_th) if prob_th is not None else DECISION_PROB_TH

        # Use final (possibly hybrid) predictions for recommendation
        pred_for_decision = {
            "prob_up": prob_up_final,
            "expected_delta_bps": expected_delta_final
        }
        rec = choose_recommendation(pred_for_decision, eff_policy, eff_spread, eff_prob_th)

        # Embargo: force WAIT inside X minutes to next high-importance event
        eff_embargo = int(embargo_min) if embargo_min is not None else DECISION_EMBARGO_MIN
        embargo_note = None
        try:
            mte = int(feats["minutes_to_event"].iloc[-1])  # per-row proximity from features
        except Exception:
            mte = None
        if eff_embargo > 0 and mte is not None and mte >= 0 and mte <= eff_embargo:
            rec = "WAIT"
            embargo_note = f"embargo: minutes_to_event={mte}<= {eff_embargo}"

        # --- build explanation parts once ---
        model_tag = (
            "baseline: rolling mean"
            if pred.get("model_id") == "baseline_v0"
            else f"model={pred.get('model_id')}"
        )
        explanation_parts = [
            model_tag,
            f"policy={eff_policy}; spread_bps={eff_spread}; prob_th={eff_prob_th}",
        ]
        
        # Add hybrid fusion info if used
        if use_hybrid_mode and fusion_weights["llm"] > 0.05:
            explanation_parts.append(
                f"hybrid: ML={fusion_weights['ml']:.0%}, News={fusion_weights['llm']:.0%}"
            )
            if news_summary:
                explanation_parts.append(news_summary)
        
        if embargo_note:
            explanation_parts.append(embargo_note)

        # Direction & action hint derived from final (hybrid) signal
        direction, action_hint = build_direction_and_hint(
            pair,
            prob_up_final,
            expected_delta_final,
        )
        explanation_parts.append(f"dir={direction}")
        explanation_parts.append(action_hint)

        # --- decision logging (fxai.decisions) ---
        try:
            now_ts = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for ClickHouse DateTime
            explanation_str = "; ".join(explanation_parts)
            
            # Use original ML prob as prior, hybrid as posterior
            prior_prob = float(pred.get("prob_up", 0.5))
            posterior_prob = prob_up_final
            
            decision_row = (
                now_ts,                      # ts (DateTime64(3) compatible)
                pair,                        # pair
                h,                           # horizon
                prior_prob,                  # prior_prob_up (ML only)
                posterior_prob,              # posterior_prob_up (after news fusion)
                expected_delta_final,        # expected_delta_bps (hybrid)
                -5.0,                        # range_p10 (align with response)
                5.0,                         # range_p90
                'none',                      # shock_level Enum8
                news_sentiment.impact_score if news_sentiment else 0.0,  # event_impact
                rec,                        # recommendation
                explanation_str,             # explanation
                pred.get("model_id", "baseline_v0")                # policy_version (use model id)
            )
            insert_rows(
                "fxai.decisions",
                [decision_row],
                [
                    "ts","pair","horizon","prior_prob_up","posterior_prob_up", "expected_delta_bps",
                    "range_p10","range_p90","shock_level","event_impact",
                    "recommendation","explanation","policy_version"
                ],
            )
        except Exception:
            log.exception("decision_log_error", pair=pair, h=h)
        
        # Log hybrid prediction if enabled
        if use_hybrid_mode and news_sentiment:
            try:
                processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                hybrid_row = (
                    now_ts,
                    pair,
                    h,
                    prior_prob,
                    expected_delta_final - (expected_delta_final - float(pred.get("expected_delta_bps", 0.0))),  # ML delta
                    pred.get("model_id", "baseline_v0"),
                    news_sentiment.sentiment_score,
                    news_sentiment.confidence,
                    news_sentiment.impact_score,
                    news_summary or "",
                    posterior_prob,
                    expected_delta_final,
                    fusion_weights["ml"],
                    fusion_weights["llm"],
                    rec,
                    explanation_str,
                    processing_time_ms,
                    0.0  # LLM cost (tracked separately)
                )
                insert_rows(
                    "fxai.hybrid_predictions",
                    [hybrid_row],
                    [
                        "ts","pair","horizon","prob_up_ml","expected_delta_ml","ml_model_id",
                        "sentiment_score","sentiment_confidence","news_impact","news_summary",
                        "prob_up_hybrid","expected_delta_hybrid","fusion_weight_ml","fusion_weight_llm",
                        "recommendation","explanation","processing_time_ms","llm_cost_usd"
                    ]
                )
            except Exception:
                log.exception("hybrid_log_error", pair=pair, h=h)

        # Build response
        response = {
            "pair": pair,
            "horizon": h,
            "prob_up": prob_up_final,
            "expected_delta_bps": expected_delta_final,
            "range": {"p10": -5.0, "p90": 5.0},
            "confidence": 0.2,
            "recommendation": rec,
            "explanation": explanation_parts,
            "model_id": pred.get("model_id", "baseline_v0"),
            "direction": direction,
            "action_hint": action_hint,
        }
        
        # Add hybrid-specific fields if fusion was used
        if use_hybrid_mode and fusion_weights["llm"] > 0.0:
            response["hybrid"] = {
                "enabled": True,
                "prob_up_ml": float(pred.get("prob_up", 0.5)),
                "prob_up_hybrid": prob_up_final,
                "expected_delta_ml": float(pred.get("expected_delta_bps", 0.0)),
                "expected_delta_hybrid": expected_delta_final,
                "fusion_weights": fusion_weights,
                "news_sentiment": news_sentiment.sentiment_score if news_sentiment else None,
                "news_confidence": news_sentiment.confidence if news_sentiment else None,
                "news_impact": news_sentiment.impact_score if news_sentiment else None,
                "news_summary": news_summary
            }
        else:
            response["hybrid"] = {"enabled": False}
        
        return response
    except Exception as e:
        log.exception("forecast_error", pair=pair, h=h)
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=500, detail=f"forecast_error: {type(e).__name__}: {e}")



@app.get("/v1/bars/recent")
async def bars_recent(
    pair: str = Query(..., description="Currency pair, e.g., USDINR"),
    limit: int = Query(50, ge=1, le=1000),
    _: None = Depends(require_key),
):
    df = query_df(f"""
        SELECT ts, pair, open, high, low, close, spread_avg
        FROM fxai.bars_1m
        WHERE pair = '{pair}'
        ORDER BY ts DESC
        LIMIT {limit}
    """)
    return df.to_dict(orient="records")

@app.get("/v1/validations/recent")
async def validations_recent(
    pair: str | None = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    _: None = Depends(require_key),
):
    cond = f"WHERE pair = '{pair}'" if pair else ""
    df = query_df(f"""
        SELECT ts, pair, rule, level, message
        FROM fxai.validations
        {cond}
        ORDER BY ts DESC
        LIMIT {limit}
    """)
    return df.to_dict(orient="records")


@app.get("/v1/news/recent")
def get_recent_news(
    limit: int = Query(default=10, ge=1, le=100),
    _: None = Depends(require_key),
):
    """Get recent news items."""
    df = query_df(f"""
        SELECT id, ts, source, headline, content, url, author
        FROM fxai.news_items
        ORDER BY ts DESC
        LIMIT {limit}
    """)
    return df.to_dict(orient="records")


@app.get("/v1/sentiment/recent")
def get_recent_sentiment(
    limit: int = Query(default=10, ge=1, le=100),
    _: None = Depends(require_key),
):
    """Get recent sentiment scores."""
    df = query_df(f"""
        SELECT 
            news_id, ts, model_version,
            sentiment_overall, sentiment_usd, sentiment_inr,
            confidence, impact_score, urgency, explanation
        FROM fxai.sentiment_scores
        ORDER BY ts DESC
        LIMIT {limit}
    """)
    return df.to_dict(orient="records")


@app.get("/v1/bars/recent")
def get_recent_bars(
    pair: str = Query(default="USDINR"),
    limit: int = Query(default=50, ge=1, le=500),
    _: None = Depends(require_key),
):
    """Get recent price bars."""
    df = query_df(f"""
        SELECT ts, pair, open, high, low, close, volume
        FROM fxai.bars_1m
        WHERE pair = '{pair}'
        ORDER BY ts DESC
        LIMIT {limit}
    """)
    # Reverse to get chronological order
    df = df.iloc[::-1]
    return df.to_dict(orient="records")