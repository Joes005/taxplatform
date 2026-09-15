"""Lightweight, structural-only GST helpers.

Per Phase 3 scope: no government API calls, no checksum/liveness
verification — just the regex structure of a GSTIN and the state-code
lookup table used to label `state_code` fields for humans. A GSTIN's first
two digits are the GST state code of the registered state.
"""

import re

# 15 chars: 2-digit state code, 10-char PAN, 1-digit entity code,
# literal 'Z', 1 checksum char (not verified here — structure only).
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

# GST state codes (Schedule III / TIN state codes), the ones in common use.
GST_STATE_CODES: dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
}


def is_valid_gstin_format(gstin: str) -> bool:
    return bool(GSTIN_PATTERN.match(gstin.strip().upper()))


def state_code_from_gstin(gstin: str) -> str | None:
    if not is_valid_gstin_format(gstin):
        return None
    return gstin[:2]


def state_name_for_code(state_code: str | None) -> str | None:
    if not state_code:
        return None
    return GST_STATE_CODES.get(state_code)
