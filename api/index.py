from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import os

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Request Schema
class TelemetryQuery(BaseModel):
    regions: List[str]
    threshold_ms: float

# Path pointing to your JSON file
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")

@app.post("/")
def get_metrics(body: TelemetryQuery):
    if not os.path.exists(DATA_PATH):
        return {"error": f"Telemetry file not found at {DATA_PATH}"}
    
    # Read the JSON file directly into a DataFrame
    df = pd.read_json(DATA_PATH)
    
    # Normalize column text headers just in case of spaces/capitalization differences
    df.columns = [c.lower().strip() for c in df.columns]
    
    # Column mapping matching the assignments
    latency_col = 'latency' if 'latency' in df.columns else 'latency_ms'
    uptime_col = 'uptime'
    region_col = 'region'
    
    results = {}
    
    for r in body.regions:
        # Filter for rows matching the specified region
        region_df = df[df[region_col].astype(str).str.lower() == r.lower()]
        
        if region_df.empty:
            continue
            
        latencies = region_df[latency_col].dropna()
        uptimes = region_df[uptime_col].dropna()
        
        if len(latencies) == 0:
            continue
            
        # Standard analytical metrics
        avg_latency = float(latencies.mean())
        p95_latency = float(latencies.quantile(0.95))
        avg_uptime = float(uptimes.mean())
        breaches = int((latencies > body.threshold_ms).sum())
        
        results[r] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return results
