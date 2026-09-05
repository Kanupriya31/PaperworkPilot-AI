from __future__ import annotations

from copy import deepcopy
from typing import Any

from agent.demo import DEMO_FORM_TEXT, DEMO_PROFILE, demo_extraction as parking_extraction


DEFAULT_DEMO_ID = "parking-permit"


def evidence(quote: str, location: str) -> dict[str, str]:
    return {"quote": quote, "location": location}


SCHOOL_FORM = """HARBORVIEW SCHOOL DISTRICT — SCIENCE MUSEUM FIELD TRIP CONSENT

Return this completed form to the school office by October 14, 2026.

STUDENT INFORMATION
Student full legal name: ______________________________
Student date of birth: ____ / ____ / ______
Grade and homeroom: _________________________________

PARENT OR LEGAL GUARDIAN
Guardian full name: __________________________________
Home address: ________________________________________
Email address: _______________________________________
Primary phone number: ________________________________

EMERGENCY AND HEALTH INFORMATION
Emergency contact name, relationship, and phone: ______________________________
List allergies, medical needs, or medications. Write NONE if there are none: __________________
Attach a current health action plan only if the student needs medication or allergy support during the trip.
School staff cannot administer medication without a signed medication authorization already on file.

PERMISSION
I give permission for the student named above to attend the Science Museum trip on October 21, 2026: Yes / No
The trip fee is $18. Pay through the family portal or by check payable to Harborview School District. Do not send cash.

Guardian signature: ______________________________  Date: ______________"""


SCHOOL_PROFILE = {
    "fullName": "Elena Garcia",
    "address": "72 Harbor Lane, Bayview, NY 11702",
    "email": "elena.garcia@example.com",
    "phone": "(631) 555-0182",
}


def school_extraction() -> dict[str, Any]:
    return {
        "formTitle": "Science Museum Field Trip Consent",
        "formPurpose": "Give Harborview School District permission and safety information for a student's museum trip.",
        "plainLanguageSummary": "Provide student, guardian, emergency, and health details; decide whether the student may attend; arrange the fee; and sign the consent form.",
        "estimatedTime": "About 8 minutes, plus time to locate any health plan",
        "urgency": {"level": "high", "reason": "The completed form is due October 14, 2026, before the October 21 trip."},
        "fields": [
            {"id": "student-name", "label": "Student full legal name", "plainLanguage": "The student's complete legal name", "type": "text", "required": True, "whyItMatters": "Identifies the student attending the trip.", "profileKey": "none", "evidence": evidence("Student full legal name:", "Student information")},
            {"id": "student-dob", "label": "Student date of birth", "plainLanguage": "The student's birth date", "type": "date", "required": True, "whyItMatters": "Helps the school verify the student record.", "profileKey": "none", "evidence": evidence("Student date of birth:", "Student information")},
            {"id": "grade", "label": "Grade and homeroom", "plainLanguage": "The student's current grade and teacher or homeroom", "type": "text", "required": True, "whyItMatters": "Routes the form to the correct class list.", "profileKey": "none", "evidence": evidence("Grade and homeroom:", "Student information")},
            {"id": "guardian", "label": "Guardian full name", "plainLanguage": "The parent or legal guardian completing the form", "type": "text", "required": True, "whyItMatters": "Identifies the adult providing consent.", "profileKey": "fullName", "evidence": evidence("Guardian full name:", "Parent or legal guardian")},
            {"id": "guardian-address", "label": "Guardian home address", "plainLanguage": "The guardian's current home address", "type": "text", "required": True, "whyItMatters": "Provides the school's address of record for the guardian.", "profileKey": "address", "evidence": evidence("Home address:", "Parent or legal guardian")},
            {"id": "guardian-email", "label": "Guardian email", "plainLanguage": "A current email address for trip updates", "type": "text", "required": True, "whyItMatters": "Lets the school send trip information.", "profileKey": "email", "evidence": evidence("Email address:", "Parent or legal guardian")},
            {"id": "guardian-phone", "label": "Guardian phone", "plainLanguage": "A phone number the school can call", "type": "text", "required": True, "whyItMatters": "Lets the school reach the guardian quickly.", "profileKey": "phone", "evidence": evidence("Primary phone number:", "Parent or legal guardian")},
            {"id": "emergency", "label": "Emergency contact", "plainLanguage": "A backup adult's name, relationship, and phone", "type": "text", "required": True, "whyItMatters": "Provides another contact if the guardian cannot be reached.", "profileKey": "none", "evidence": evidence("Emergency contact name, relationship, and phone:", "Emergency and health information")},
            {"id": "health", "label": "Allergies, medical needs, or medications", "plainLanguage": "List relevant needs or write NONE", "type": "text", "required": True, "whyItMatters": "Helps staff plan safe support during the trip.", "profileKey": "none", "evidence": evidence("List allergies, medical needs, or medications", "Emergency and health information")},
            {"id": "permission", "label": "Trip permission choice", "plainLanguage": "Choose Yes or No for attendance", "type": "choice", "required": True, "whyItMatters": "Records whether the student has permission to attend.", "profileKey": "none", "evidence": evidence("attend the Science Museum trip on October 21, 2026: Yes / No", "Permission")},
            {"id": "signature", "label": "Guardian signature and date", "plainLanguage": "Sign only after reviewing every response", "type": "signature", "required": True, "whyItMatters": "Confirms the guardian's decision and the information supplied.", "profileKey": "none", "evidence": evidence("Guardian signature:", "Permission")},
        ],
        "documents": [
            {"name": "Current health action plan, if applicable", "required": False, "reason": "Needed only when medication or allergy support is required during the trip.", "acceptableExamples": ["School-approved allergy action plan", "Current medication care plan"], "evidence": evidence("Attach a current health action plan only if", "Emergency and health information")},
        ],
        "warnings": [
            {"severity": "important", "title": "Medication needs prior authorization", "detail": "A health plan alone does not authorize staff to administer medication.", "evidence": evidence("cannot administer medication without a signed medication authorization", "Emergency and health information")},
            {"severity": "caution", "title": "Do not send cash", "detail": "Use the family portal or a check for the $18 trip fee.", "evidence": evidence("Do not send cash", "Permission")},
        ],
        "nextBestAction": "Confirm the student's health and medication needs first so you know whether an action plan is required.",
        "confidenceNote": "High confidence on the visible consent requirements. A guardian must verify health information and sign personally.",
    }


UTILITY_FORM = """NORTHSTAR ENERGY — CUSTOMER HARDSHIP ASSISTANCE APPLICATION

Use this form to request a temporary payment arrangement. Approval is not guaranteed.

CUSTOMER
Customer full legal name: ______________________________
Service address: _______________________________________
Mailing address, if different: __________________________
Phone number: __________________________________________
Email address: _________________________________________
Northstar account number: ______________________________
Last four digits of Social Security number: ____________

HOUSEHOLD
Number of people in household: __________
Total monthly gross household income: $________________
Reason for hardship: ___________________________________

REQUIRED DOCUMENTS
Include: (1) a copy of the current Northstar utility bill, (2) photo identification,
and (3) proof of all household income received in the last 30 days, such as pay stubs or a benefits statement.

Submit within 10 calendar days of the date printed on your disconnection notice.
Upload through the secure customer portal or deliver in person. Do not email this form or its attachments.

I certify that the information is true and complete.
Customer signature: ______________________________  Date: ______________"""


UTILITY_PROFILE = {
    "fullName": "Jordan Lee",
    "address": "908 Pine Avenue, Unit 12, Northstar, NY 10461",
    "email": "jordan.lee@example.com",
    "phone": "(718) 555-0169",
}


def utility_extraction() -> dict[str, Any]:
    return {
        "formTitle": "Customer Hardship Assistance Application",
        "formPurpose": "Request a temporary Northstar Energy payment arrangement after a financial hardship.",
        "plainLanguageSummary": "Provide customer, account, household, and income information; collect three supporting documents; use a secure submission channel; and sign the certification.",
        "estimatedTime": "About 15 minutes once income records are ready",
        "urgency": {"level": "high", "reason": "The application is due within 10 days of the date on the customer's disconnection notice."},
        "fields": [
            {"id": "full-name", "label": "Customer full legal name", "plainLanguage": "Your legal name as shown on the account and ID", "type": "text", "required": True, "whyItMatters": "Matches the request to the customer record.", "profileKey": "fullName", "evidence": evidence("Customer full legal name:", "Customer")},
            {"id": "service-address", "label": "Service address", "plainLanguage": "The address receiving Northstar service", "type": "text", "required": True, "whyItMatters": "Identifies the service location.", "profileKey": "address", "evidence": evidence("Service address:", "Customer")},
            {"id": "phone", "label": "Phone number", "plainLanguage": "A current phone number for notices", "type": "text", "required": True, "whyItMatters": "Allows Northstar to communicate a decision.", "profileKey": "phone", "evidence": evidence("Phone number:", "Customer")},
            {"id": "email", "label": "Email address", "plainLanguage": "A current email address for status updates", "type": "text", "required": True, "whyItMatters": "Allows Northstar to send non-sensitive updates.", "profileKey": "email", "evidence": evidence("Email address:", "Customer")},
            {"id": "account", "label": "Northstar account number", "plainLanguage": "The account number printed on the utility bill", "type": "text", "required": True, "whyItMatters": "Routes the request to the correct account.", "profileKey": "none", "evidence": evidence("Northstar account number:", "Customer")},
            {"id": "ssn", "label": "Last four digits of Social Security number", "plainLanguage": "Only the last four digits, entered after confirming the submission channel", "type": "text", "required": True, "whyItMatters": "Used by the utility to verify identity.", "profileKey": "none", "evidence": evidence("Last four digits of Social Security number:", "Customer")},
            {"id": "household", "label": "Household size", "plainLanguage": "The number of people living in the household", "type": "number", "required": True, "whyItMatters": "May affect hardship-program review.", "profileKey": "none", "evidence": evidence("Number of people in household:", "Household")},
            {"id": "income", "label": "Total monthly gross household income", "plainLanguage": "Household income before taxes for one month", "type": "number", "required": True, "whyItMatters": "Supports financial hardship review.", "profileKey": "none", "evidence": evidence("Total monthly gross household income:", "Household")},
            {"id": "reason", "label": "Reason for hardship", "plainLanguage": "A short factual explanation of the financial change", "type": "text", "required": True, "whyItMatters": "Explains why temporary assistance is requested.", "profileKey": "none", "evidence": evidence("Reason for hardship:", "Household")},
            {"id": "signature", "label": "Customer signature and date", "plainLanguage": "Sign after confirming every statement and attachment", "type": "signature", "required": True, "whyItMatters": "Certifies that the application is true and complete.", "profileKey": "none", "evidence": evidence("Customer signature:", "Certification")},
        ],
        "documents": [
            {"name": "Current Northstar utility bill", "required": True, "reason": "Provides the service address, account number, and notice context.", "acceptableExamples": ["Most recent Northstar statement"], "evidence": evidence("current Northstar utility bill", "Required documents")},
            {"name": "Photo identification", "required": True, "reason": "Supports identity verification.", "acceptableExamples": ["Driver's license", "State identification card"], "evidence": evidence("photo identification", "Required documents")},
            {"name": "Proof of household income from the last 30 days", "required": True, "reason": "Documents the income reported in the application.", "acceptableExamples": ["Pay stubs", "Benefits statement"], "evidence": evidence("proof of all household income received in the last 30 days", "Required documents")},
        ],
        "warnings": [
            {"severity": "important", "title": "Sensitive identity information", "detail": "Confirm the form and secure portal before entering Social Security information.", "evidence": evidence("Last four digits of Social Security number", "Customer")},
            {"severity": "important", "title": "Deadline depends on your notice", "detail": "Calculate the deadline from the date printed on the disconnection notice; the form does not supply that date.", "evidence": evidence("within 10 calendar days of the date printed on your disconnection notice", "Submission instructions")},
            {"severity": "caution", "title": "Do not use email", "detail": "The form contains identity and income information and explicitly prohibits email submission.", "evidence": evidence("Do not email this form or its attachments", "Submission instructions")},
        ],
        "nextBestAction": "Find the current utility bill and disconnection notice first; together they provide the account number and deadline date.",
        "confidenceNote": "High confidence on visible requirements. A human must verify the portal, deadline, income figures, and sensitive identity field.",
    }


DEMO_CASES: dict[str, dict[str, Any]] = {
    "parking-permit": {
        "id": "parking-permit", "label": "Parking permit", "badge": "FLAGSHIP",
        "description": "Ambiguous deadline, three attachments, retry recovery, and a human checkpoint.",
        "sourceName": "Riverglen parking permit demo", "reviewNote": "Keep the deadline-year warning in the final checklist.",
        "failureScenario": "verifier-timeout", "flow": "approve",
        "formText": DEMO_FORM_TEXT, "profile": DEMO_PROFILE, "extraction": parking_extraction,
    },
    "school-trip": {
        "id": "school-trip", "label": "School trip consent", "badge": "FAMILY",
        "description": "Guardian matching, conditional medical paperwork, payment rules, and signature review.",
        "sourceName": "Harborview field trip consent demo", "reviewNote": "Confirm health needs and keep the medication authorization warning.",
        "failureScenario": "none", "flow": "approve",
        "formText": SCHOOL_FORM, "profile": SCHOOL_PROFILE, "extraction": school_extraction,
    },
    "utility-hardship": {
        "id": "utility-hardship", "label": "Utility hardship", "badge": "SENSITIVE",
        "description": "Sensitive identity data, income evidence, a notice-based deadline, and secure routing.",
        "sourceName": "Northstar utility hardship demo", "reviewNote": "Verify the secure portal and deadline before adding sensitive information.",
        "failureScenario": "none", "flow": "approve",
        "formText": UTILITY_FORM, "profile": UTILITY_PROFILE, "extraction": utility_extraction,
    },
    "dependency-outage": {
        "id": "dependency-outage", "label": "Dependency outage recovery", "badge": "RESILIENCE",
        "description": "The primary extraction dependency is unavailable, so the graph routes to a local recovery path.",
        "sourceName": "Dependency outage recovery demo", "reviewNote": "Keep the dependency recovery notice in the final plan.",
        "failureScenario": "extractor-dependency", "flow": "approve",
        "formText": DEMO_FORM_TEXT, "profile": DEMO_PROFILE, "extraction": parking_extraction,
    },
    "revision-loop": {
        "id": "revision-loop", "label": "Reject, revise, resume", "badge": "HUMAN LOOP",
        "description": "Request a change, preserve the checkpoint, and resume the same run after revision.",
        "sourceName": "Reject revise resume demo", "reviewNote": "Request change: keep the deadline warning and explain why the year cannot be guessed.",
        "failureScenario": "none", "flow": "revision",
        "formText": DEMO_FORM_TEXT, "profile": DEMO_PROFILE, "extraction": parking_extraction,
    },
}


def get_demo_case(case_id: str = DEFAULT_DEMO_ID) -> dict[str, Any]:
    if case_id not in DEMO_CASES:
        raise KeyError(case_id)
    return {key: deepcopy(value) for key, value in DEMO_CASES[case_id].items() if key != "extraction"}


def list_demo_cases() -> list[dict[str, str]]:
    return [
        {key: str(case[key]) for key in ("id", "label", "badge", "description", "failureScenario", "flow")}
        for case in DEMO_CASES.values()
    ]


def demo_extraction(case_id: str = DEFAULT_DEMO_ID) -> dict[str, Any]:
    case = DEMO_CASES.get(case_id, DEMO_CASES[DEFAULT_DEMO_ID])
    return deepcopy(case["extraction"]())
