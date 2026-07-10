import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from orchestrator import MeetingOrchestrator

app = FastAPI(
    title="EchoScribe AI Backend API",
    description="Backend analysis service for Meeting Notes Agent",
    version="1.0.0"
)

# Configure CORS to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    transcript: str
    template: str = "general"

@app.get("/health")
def health_check():
    """Health check endpoint to verify backend status."""
    return {"status": "healthy", "service": "meeting-notes-agent-backend"}

@app.post("/api/meeting/analyze")
def analyze_meeting(request: AnalyzeRequest):
    """
    Executes the full orchestrator pipeline on the provided transcript.
    Returns the serialized OrchestratorOutput JSON.
    """
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript content cannot be empty.")

    try:
        orchestrator = MeetingOrchestrator()
        # Web API runs the pipeline automatically without blocking CLI confirmation callbacks
        pipeline_output = orchestrator.run_pipeline(
            transcript_text=request.transcript,
            template=request.template
        )
        
        # Save a local audit log of the processed meeting
        notes = pipeline_output.meeting_notes
        timestamp_str = datetime_str = notes.date.replace("-", "").replace(":", "")[:15]
        safe_title = "".join(c for c in notes.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
        safe_title = safe_title.replace(" ", "_").lower()
        meeting_id = f"api_meeting_{timestamp_str}_{safe_title}"
        
        orchestrator.save_outputs(pipeline_output, "data/processed", meeting_id)

        # Return dict model dump matching OrchestratorOutput
        return pipeline_output.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
