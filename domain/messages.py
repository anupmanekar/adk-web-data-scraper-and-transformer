from pydantic import BaseModel
from typing import Any, Dict, Optional

class AgentResponse(BaseModel):
    userId: str
    message: str
    sessionId: Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json()

class AidinExtractedData(BaseModel):
    patient_info: Dict[str, Any]
    insurance_data: Dict[str, Any]