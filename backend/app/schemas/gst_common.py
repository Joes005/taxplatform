from pydantic import BaseModel

from app.models.gst_enums import ValidationSeverity


class GSTValidationFinding(BaseModel):
    code: str
    severity: ValidationSeverity
    entity: str
    entity_id: str
    message: str
    field: str | None = None
