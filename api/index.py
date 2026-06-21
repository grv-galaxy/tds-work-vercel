from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import numpy as np
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

class TelemetryQuery(BaseModel):
    regions: List[str]
    threshold_ms: float

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "q-vercel-latency.json")

@app.post("/")
def get_metrics(body: TelemetryQuery):
    if not os.path.exists(DATA_PATH):
        return {"error": f"Data file not found at {DATA_PATH}"}
    
    try:
        df = pd.read_json(DATA_PATH)
        
        # Mapping explicitly matching your JSON properties
        region_col = 'region'
        latency_col = 'latency_ms'
        uptime_col = 'uptime_pct'
        
        results = {}
        
        for r in body.regions:
            # Filter rows per targeted region
            region_df = df[df[region_col].astype(str).str.lower() == r.lower()]
            
            if region_df.empty:
                results[r] = {
                    "avg_latency": 0.0,
                    "p95_latency": 0.0,
                    "avg_uptime": 0.0,
                    "breaches": 0
                }
                continue
                
            latencies = region_df[latency_col].dropna().values
            uptimes = region_df[uptime_col].dropna().values
            
            if len(latencies) == 0:
                continue
            
            # Formulating statistical values 
            avg_latency = float(np.mean(latencies))
            p95_latency = float(np.percentile(latencies, 95))
            avg_uptime = float(np.mean(uptimes))
            breaches = int(np.sum(latencies > body.threshold_ms))
            
            results[r] = {
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
                "avg_uptime": avg_uptime,
                "breaches": breaches
            }
            
        return results
        
    except Exception as e:
        return {"error": f"Execution crash: {str(e)}"}
