from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TelemetryQuery(BaseModel):
    regions: List[str]
    threshold_ms: float

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")

@app.post("/")
def get_metrics(body: TelemetryQuery):
    if not os.path.exists(DATA_PATH):
        return {"error": "Data file not found"}
    try:
        df = pd.read_json(DATA_PATH)
        results = []
        for r in body.regions:
            region_df = df[df['region'].str.lower() == r.lower()]
            if region_df.empty:
                results.append({
                    "region": r, "avg_latency": 0.0, "p95_latency": 0.0,
                    "avg_uptime": 0.0, "breaches": 0
                })
                continue
            latencies = region_df['latency_ms']
            uptimes = region_df['uptime_pct']
            results.append({
                "region": r,
                "avg_latency": float(latencies.mean()),
                "p95_latency": float(latencies.quantile(0.95)),
                "avg_uptime": float(uptimes.mean()),
                "breaches": int((latencies > body.threshold_ms).sum())
            })
        return results
    except Exception as e:
        return {"error": str(e)}
