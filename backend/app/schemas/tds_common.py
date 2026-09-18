from pydantic import BaseModel

from app.models.tds_enums import TDSValidationSeverity


class TDSValidationFinding(BaseModel):
    code: str
    severity: TDSValidationSeverity
    entity: str
    entity_id: str
    message: str
    field: str | None = None
