from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import os

app = FastAPI()

# Perfect CORS configuration for both POST and OPTIONS checks
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

# This path handles Vercel's multi-directory internal structure accurately
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "q-vercel-latency.json")

@app.post("/")
def get_metrics(body: TelemetryQuery):
    # Safety Check: If file isn't found, handle gracefully instead of throwing a 500 crash
    if not os.path.exists(DATA_PATH):
        return {"error": f"File not found at location: {DATA_PATH}"}
    
    try:
        # Load the data file safely
        df = pd.read_json(DATA_PATH)
        
        # Normalize column headers to lowercase and strip whitespaces
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Determine exact column names
        latency_col = 'latency' if 'latency' in df.columns else 'latency_ms'
        uptime_col = 'uptime'
        region_col = 'region'
        
        results = {}
        
        for r in body.regions:
            # Filter rows per region (case-insensitive strings)
            region_df = df[df[region_col].astype(str).str.lower() == r.lower()]
            
            if region_df.empty:
                # If a requested region isn't found, provide default empty structures 
                # so the script doesn't crash on statistical functions
                results[r] = {
                    "avg_latency": 0.0,
                    "p95_latency": 0.0,
                    "avg_uptime": 0.0,
                    "breaches": 0
                }
                continue
                
            latencies = region_df[latency_col].dropna()
            uptimes = region_df[uptime_col].dropna()
            
            # Explicit standard type casting (float/int) avoids native NumPy type serialization errors
            avg_latency = float(latencies.mean()) if len(latencies) > 0 else 0.0
            p95_latency = float(latencies.quantile(0.95)) if len(latencies) > 0 else 0.0
            avg_uptime = float(uptimes.mean()) if len(uptimes) > 0 else 0.0
            breaches = int((latencies > body.threshold_ms).sum())
            
            results[r] = {
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
                "avg_uptime": avg_uptime,
                "breaches": breaches
            }
            
        return results

    except Exception as e:
        return {"error": f"Internal execution crash: {str(e)}"}
