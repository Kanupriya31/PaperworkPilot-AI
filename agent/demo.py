from __future__ import annotations


DEMO_FORM_TEXT = """CITY OF RIVERGLEN — RESIDENTIAL PARKING PERMIT APPLICATION

All applicants must complete Sections A through D. Incomplete applications will be returned.

SECTION A — APPLICANT
Full legal name: ______________________________
Date of birth: ____ / ____ / ______
Email address: ________________________________
Phone number: _________________________________

SECTION B — RESIDENCE
Street address: ________________________________
Unit: ______  ZIP code: __________
Are you the property owner?  Yes / No

SECTION C — VEHICLE
License plate number: __________________________
State: ______  Vehicle make/model: ______________

SECTION D — REQUIRED DOCUMENTATION
Attach: (1) current driver's license, (2) current vehicle registration, and
(3) one proof of residence dated within the last 60 days, such as a utility bill or lease.

Applicant signature: __________________ Date: __________

Applications must be received by September 30. Submit online or in person at City Hall.
Do not mail original identity documents."""


DEMO_PROFILE = {
    "fullName": "Maya Johnson",
    "address": "184 Willow Street, Apt 3B, Riverglen, NY 10027",
    "dateOfBirth": "1994-06-18",
    "email": "maya@example.com",
    "phone": "(212) 555-0147",
}


def evidence(quote: str, location: str) -> dict[str, str]:
    return {"quote": quote, "location": location}


def demo_extraction() -> dict:
    return {
        "formTitle": "Residential Parking Permit Application",
        "formPurpose": "Apply for permission to park a registered vehicle in a Riverglen residential permit zone.",
        "plainLanguageSummary": "The city needs to confirm who you are, where you live, and which registered vehicle needs a permit. Complete four sections, attach three documents, then sign and submit.",
        "estimatedTime": "About 12 minutes once your documents are ready",
        "urgency": {
            "level": "medium",
            "reason": "The form lists September 30 but does not identify the year.",
        },
        "fields": [
            {"id": "full-name", "label": "Full legal name", "plainLanguage": "Your name exactly as it appears on your ID", "type": "text", "required": True, "whyItMatters": "Used to match the application to your ID.", "profileKey": "fullName", "evidence": evidence("Full legal name:", "Section A")},
            {"id": "dob", "label": "Date of birth", "plainLanguage": "Your birth date in month/day/year format", "type": "date", "required": True, "whyItMatters": "Helps confirm your identity.", "profileKey": "dateOfBirth", "evidence": evidence("Date of birth:", "Section A")},
            {"id": "address", "label": "Street address, unit, and ZIP", "plainLanguage": "The Riverglen address where you currently live", "type": "text", "required": True, "whyItMatters": "Determines whether you qualify for the permit zone.", "profileKey": "address", "evidence": evidence("Street address:", "Section B")},
            {"id": "owner", "label": "Property owner status", "plainLanguage": "Choose Yes if you own the home; otherwise choose No", "type": "choice", "required": True, "whyItMatters": "May determine which residence documents apply.", "profileKey": "none", "evidence": evidence("Are you the property owner?  Yes / No", "Section B")},
            {"id": "plate", "label": "License plate number and state", "plainLanguage": "The plate number and issuing state on your registration", "type": "text", "required": True, "whyItMatters": "The permit will be tied to this vehicle.", "profileKey": "none", "evidence": evidence("License plate number:", "Section C")},
            {"id": "vehicle", "label": "Vehicle make and model", "plainLanguage": "For example: Toyota Corolla", "type": "text", "required": True, "whyItMatters": "Lets parking enforcement identify the vehicle.", "profileKey": "none", "evidence": evidence("Vehicle make/model:", "Section C")},
            {"id": "signature", "label": "Signature and date", "plainLanguage": "Sign and date after checking the application", "type": "signature", "required": True, "whyItMatters": "Confirms the application is accurate.", "profileKey": "none", "evidence": evidence("Applicant signature:", "After Section D")},
        ],
        "documents": [
            {"name": "Current driver's license", "required": True, "reason": "Confirms your identity.", "acceptableExamples": ["Unexpired driver's license showing your name"], "evidence": evidence("current driver's license", "Section D")},
            {"name": "Current vehicle registration", "required": True, "reason": "Confirms the plate and vehicle details.", "acceptableExamples": ["Official registration card", "Current digital registration, if accepted"], "evidence": evidence("current vehicle registration", "Section D")},
            {"name": "Proof of residence from the last 60 days", "required": True, "reason": "Confirms your current address.", "acceptableExamples": ["Utility bill", "Current lease"], "evidence": evidence("proof of residence dated within the last 60 days", "Section D")},
        ],
        "warnings": [
            {"severity": "important", "title": "Confirm the deadline year", "detail": "The form says September 30 but does not identify a year.", "evidence": evidence("received by September 30", "Submission instructions")},
            {"severity": "caution", "title": "Use copies, not original ID", "detail": "The form says not to mail original identity documents.", "evidence": evidence("Do not mail original identity documents", "Submission instructions")},
            {"severity": "info", "title": "Verify online upload rules", "detail": "The form allows online submission but does not list file formats or size limits.", "evidence": evidence("Submit online or in person", "Submission instructions")},
        ],
        "nextBestAction": "Find your vehicle registration first—it supplies the plate, state, make, and model in one step.",
        "confidenceNote": "High confidence on visible requirements. The deadline year and online upload rules still require human verification.",
    }

