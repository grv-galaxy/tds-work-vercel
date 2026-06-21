from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import numpy as np
import os

app = FastAPI()

# 1. Broad Middleware for general CORS
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

# Set path to the JSON data file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "q-vercel-latency.json")

# 2. Global middleware to force headers on every response
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        })
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.post("/")
def get_metrics(body: TelemetryQuery):
    if not os.path.exists(DATA_PATH):
        return {"error": "Data file not found"}
    
    try:
        df = pd.read_json(DATA_PATH)
        
        # Columns based on your provided JSON structure
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
            
            # Perform calculations with explicit type casting
            results[r] = {
                "avg_latency": float(np.mean(latencies)),
                "p95_latency": float(np.percentile(latencies, 95)),
                "avg_uptime": float(np.mean(uptimes)),
                "breaches": int(np.sum(latencies > body.threshold_ms))
            }
            
        return results
        
    except Exception as e:
        return {"error": str(e)}
