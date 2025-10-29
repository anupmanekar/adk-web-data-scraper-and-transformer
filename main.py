import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app
from interface.adapters.tasks import TaskAdapter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session DB URL (e.g., SQLite)
#SESSION_DB_URL = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    #session_service_uri=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

# You can add more FastAPI routes or configurations below if needed
# Example:
@app.get("/hello")
async def read_root():
    return {"Hello": "World"}

@app.get("/extract")
async def extract_aidin_data():
    logger.info("Starting AIDIN data extraction...")
    aidin_json_data = {}
    task_adapter = TaskAdapter()
    aidin_raw_data = await task_adapter.extract_raw_text_from_aidin(None)
    combined_raw_text = f"Quick View Info: {aidin_raw_data['quick_view_data']}\nPatient Info: {aidin_raw_data['patient_info']}\nInsurance Data: {aidin_raw_data['insurance_data']}"
    aidin_json_data = await task_adapter.transform_raw_text_to_json(combined_raw_text)
    logger.info(f'Extracted AIDIN JSON Data: {aidin_json_data}')
    # write content to a file
    with open("patient_downloads/aidin_extracted_data.json", "w") as f:
        f.write(str(aidin_json_data))
    return aidin_json_data

if __name__ == "__main__":
    # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))