from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import numpy as np
import os

app = FastAPI()

# Only keep the standard CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TelemetryQuery(BaseModel):
    regions: List[str]
    threshold_ms: float

# Ensure your path logic is robust
DATA_PATH = os.path.join(os.getcwd(), "q-vercel-latency.json")

@app.post("/")
def get_metrics(body: TelemetryQuery):
    if not os.path.exists(DATA_PATH):
        return {"error": f"Data file not found at {DATA_PATH}"}
    
    try:
        df = pd.read_json(DATA_PATH)
        
        region_col = 'region'
        latency_col = 'latency_ms'
        uptime_col = 'uptime_pct'
        
        results = {}
        for r in body.regions:
            region_df = df[df[region_col].astype(str).str.lower() == r.lower()]
            
            if region_df.empty:
                results[r] = {"avg_latency": 0.0, "p95_latency": 0.0, "avg_uptime": 0.0, "breaches": 0}
                continue
                
            latencies = region_df[latency_col].dropna().values
            uptimes = region_df[uptime_col].dropna().values
            
            results[r] = {
                "avg_latency": float(np.mean(latencies)),
                "p95_latency": float(np.percentile(latencies, 95)),
                "avg_uptime": float(np.mean(uptimes)),
                "breaches": int(np.sum(latencies > body.threshold_ms))
            }
        return results
        
    except Exception as e:
        return {"error": str(e)}
