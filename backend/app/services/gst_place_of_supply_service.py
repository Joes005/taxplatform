"""Determines whether a transaction is intra-state (CGST+SGST) or
inter-state (IGST) from supplier and place-of-supply state codes.

This intentionally covers only the common case used throughout Phase 4:
comparing the supplier's registered state to the place of supply. GST law
has special place-of-supply rules for specific scenarios (certain
services, SEZ, exports, ...) that this engine does not attempt to derive
automatically — those stay REVIEW_REQUIRED in the classification layer
rather than being silently decided here (PHASE4 section 8).
"""

from app.core.exceptions import ValidationAppError
from app.models.gst_enums import SupplyType


class GSTPlaceOfSupplyService:
    @staticmethod
    def determine_supply_type(
        supplier_state_code: str, place_of_supply_state_code: str
    ) -> SupplyType:
        if not supplier_state_code or not place_of_supply_state_code:
            raise ValidationAppError(
                "Both supplier state code and place of supply state code are required "
                "to determine intra-state vs inter-state treatment",
                code="MISSING_PLACE_OF_SUPPLY",
            )
        if supplier_state_code == place_of_supply_state_code:
            return SupplyType.INTRA_STATE
        return SupplyType.INTER_STATE
