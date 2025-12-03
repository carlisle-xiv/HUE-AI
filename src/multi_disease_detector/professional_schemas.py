from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ProfessionalRole(str, Enum):
    """Medical professional role types."""
    PHYSICIAN = "physician"
    NURSE = "nurse"
    RADIOLOGIST = "radiologist"
    PHARMACIST = "pharmacist"
    SPECIALIST = "specialist"
    RESIDENT = "resident"
    PA = "physician_assistant"
    NP = "nurse_practitioner"
    OTHER = "other"


class Urgency(str, Enum):
    """Clinical urgency levels."""
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"
    EMERGENT = "EMERGENT"


class ClinicalLikelihood(str, Enum):
    """Likelihood levels for differential diagnoses."""
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    UNLIKELY = "UNLIKELY"


class DifferentialDiagnosis(BaseModel):
    """Individual differential diagnosis with rationale."""
    condition: str = Field(..., description="Medical condition/diagnosis name")
    likelihood: ClinicalLikelihood = Field(..., description="Likelihood of this diagnosis")
    rationale: str = Field(..., description="Clinical reasoning for this diagnosis")
    key_findings: Optional[List[str]] = Field(None, description="Supporting clinical findings")
    rule_out_criteria: Optional[List[str]] = Field(None, description="Criteria that would rule out this diagnosis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "condition": "Pulmonary Embolism",
                "likelihood": "HIGH",
                "rationale": "Wells score >6, elevated D-dimer, acute dyspnea with pleuritic chest pain",
                "key_findings": ["Tachycardia", "Hypoxemia", "Unilateral leg swelling"],
                "rule_out_criteria": ["Negative CT-PA", "Alternative diagnosis confirmed"]
            }
        }
    )


class TreatmentConsideration(BaseModel):
    """Treatment option with dosing and contraindications."""
    treatment: str = Field(..., description="Treatment name/intervention")
    indication: str = Field(..., description="Clinical indication for this treatment")
    dosing: Optional[str] = Field(None, description="Recommended dosing if applicable")
    contraindications: Optional[List[str]] = Field(None, description="Contraindications to consider")
    monitoring: Optional[List[str]] = Field(None, description="Parameters to monitor")
    evidence_level: Optional[str] = Field(None, description="Level of evidence (e.g., Class I, Level A)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "treatment": "Enoxaparin",
                "indication": "Anticoagulation for PE",
                "dosing": "1mg/kg SC q12h or 1.5mg/kg SC daily",
                "contraindications": ["Active bleeding", "Severe thrombocytopenia", "CrCl <30"],
                "monitoring": ["Anti-Xa levels", "Platelet count", "Signs of bleeding"],
                "evidence_level": "Class I, Level A"
            }
        }
    )


class ClinicalInsights(BaseModel):
    """Structured clinical insights for professional response."""
    differential_diagnoses: List[DifferentialDiagnosis] = Field(
        default_factory=list,
        description="Ranked differential diagnoses with rationale"
    )
    recommended_workup: List[str] = Field(
        default_factory=list,
        description="Recommended diagnostic tests/imaging/labs"
    )
    treatment_considerations: List[TreatmentConsideration] = Field(
        default_factory=list,
        description="Treatment options with clinical details"
    )
    clinical_pearls: List[str] = Field(
        default_factory=list,
        description="Important clinical pearls and teaching points"
    )
    pertinent_positives: Optional[List[str]] = Field(
        None,
        description="Significant positive findings from history/exam"
    )
    pertinent_negatives: Optional[List[str]] = Field(
        None,
        description="Significant negative findings (helps narrow DDx)"
    )
    red_flags: Optional[List[str]] = Field(
        None,
        description="Warning signs requiring immediate attention"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "differential_diagnoses": [
                    {
                        "condition": "Acute Coronary Syndrome",
                        "likelihood": "HIGH",
                        "rationale": "Typical chest pain, ECG changes, elevated troponin"
                    }
                ],
                "recommended_workup": ["Serial troponins q3h", "Repeat ECG", "Echocardiogram"],
                "treatment_considerations": [
                    {
                        "treatment": "Aspirin",
                        "indication": "Antiplatelet therapy",
                        "dosing": "325mg loading, then 81mg daily"
                    }
                ],
                "clinical_pearls": ["HEART score >6 indicates high risk for MACE"],
                "pertinent_positives": ["Diaphoresis", "Radiation to left arm"],
                "pertinent_negatives": ["No reproducible chest wall tenderness"],
                "red_flags": ["Hemodynamic instability", "Cardiogenic shock"]
            }
        }
    )


class ImagingFindings(BaseModel):
    """Structured imaging findings for radiologist-grade analysis."""
    modality: str = Field(..., description="Imaging modality (CT, MRI, X-ray, US, etc.)")
    body_region: str = Field(..., description="Anatomical region imaged")
    technique: Optional[str] = Field(None, description="Technical parameters, contrast, sequences")
    findings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured findings by anatomical structure"
    )
    impression: str = Field(..., description="Overall radiological impression")
    recommendations: Optional[List[str]] = Field(
        None,
        description="Follow-up recommendations"
    )
    standardized_scoring: Optional[Dict[str, str]] = Field(
        None,
        description="Standardized scoring systems (BIRADS, Lung-RADS, LI-RADS, etc.)"
    )
    comparison: Optional[str] = Field(
        None,
        description="Comparison with prior studies if available"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "modality": "CT Chest with Contrast",
                "body_region": "Thorax",
                "technique": "Helical acquisition, PE protocol, 100mL Omnipaque 350",
                "findings": [
                    {
                        "structure": "Pulmonary arteries",
                        "finding": "Filling defect in right lower lobe segmental artery",
                        "size": "1.2cm",
                        "significance": "Consistent with acute PE"
                    }
                ],
                "impression": "Acute pulmonary embolism, right lower lobe",
                "recommendations": ["Correlate with D-dimer", "Consider lower extremity duplex"],
                "standardized_scoring": {"PE_Severity": "Intermediate-low risk (simplified PESI)"},
                "comparison": "No prior CT available for comparison"
            }
        }
    )


class ProfessionalChatRequest(BaseModel):
    """
    Professional chat request for medical professionals.
    
    Similar to SimplifiedChatRequest but includes professional role
    and expects expert-level clinical responses.
    """
    message: str = Field(..., description="Clinical question or case presentation")
    professional_role: Optional[ProfessionalRole] = Field(
        None,
        description="Role of the medical professional (helps tailor response)"
    )
    patient_id: Optional[UUID] = Field(None, description="Patient UUID for tracking")
    stream: bool = Field(False, description="Enable streaming responses (SSE)")
    
    # Optional image as base64 string
    image: Optional[str] = Field(
        None,
        description="Optional base64-encoded medical image for analysis"
    )
    
    # Clinical context
    clinical_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Clinical context: chief complaint, HPI, PMH, medications, vitals, labs"
    )
    
    # Optional patient context data (compatible with patient endpoint)
    consultation_data: Optional[Dict[str, Any]] = Field(None, description="Recent consultation information")
    vitals_data: Optional[Dict[str, Any]] = Field(None, description="Latest vital signs")
    habits_data: Optional[Dict[str, Any]] = Field(None, description="Patient habits tracking")
    conditions_data: Optional[Dict[str, Any]] = Field(None, description="Active medical conditions")
    ai_consultation_data: Optional[Dict[str, Any]] = Field(None, description="Previous AI consultation data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "55M presenting with acute onset chest pain, diaphoretic. ECG shows ST elevation in V2-V4. Troponin pending. DDx and immediate management?",
                "professional_role": "physician",
                "stream": False,
                "clinical_context": {
                    "chief_complaint": "Chest pain",
                    "history_present_illness": "Acute onset 2 hours ago, crushing substernal pain radiating to left arm",
                    "past_medical_history": ["HTN", "DM2", "Hyperlipidemia"],
                    "medications": ["Metformin", "Lisinopril", "Atorvastatin"],
                    "vitals": {
                        "BP": "168/95",
                        "HR": 102,
                        "RR": 22,
                        "SpO2": "94% RA"
                    },
                    "labs": {
                        "Troponin_initial": "pending"
                    }
                }
            }
        }
    )


class ProfessionalChatResponse(BaseModel):
    """
    Professional chat response with expert-level clinical insights.
    """
    session_id: UUID = Field(..., description="Session ID for conversation continuity")
    message: str = Field(..., description="AI-generated clinical response")
    
    # Structured clinical insights
    clinical_insights: Optional[ClinicalInsights] = Field(
        None,
        description="Structured clinical analysis with DDx, workup, treatment"
    )
    
    # Imaging-specific response (for radiologists)
    imaging_findings: Optional[ImagingFindings] = Field(
        None,
        description="Structured radiological findings (when image is analyzed)"
    )
    
    # Risk and urgency
    risk_stratification: str = Field(
        ...,
        description="Clinical risk level: LOW, MODERATE, HIGH, CRITICAL"
    )
    urgency: Urgency = Field(
        ...,
        description="Clinical urgency: ROUTINE, URGENT, STAT, EMERGENT"
    )
    
    # References and evidence
    references: List[str] = Field(
        default_factory=list,
        description="Clinical guidelines and literature references"
    )
    
    # Metadata
    tools_used: List[str] = Field(
        default_factory=list,
        description="Tools used during generation"
    )
    thinking_summary: Optional[str] = Field(
        None,
        description="Summary of clinical reasoning process"
    )
    
    # Professional disclaimer (less verbose than patient version)
    clinical_caveat: str = Field(
        default="Clinical decision support only. Verify findings independently. Final clinical decisions rest with the treating provider.",
        description="Brief professional disclaimer"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "660e8400-e29b-41d4-a716-446655440000",
                "message": "Clinical analysis suggests STEMI with high-risk features...",
                "clinical_insights": {
                    "differential_diagnoses": [
                        {
                            "condition": "STEMI - Anterior Wall",
                            "likelihood": "HIGH",
                            "rationale": "ST elevation V2-V4, typical presentation"
                        }
                    ],
                    "recommended_workup": ["Serial troponins", "Urgent cardiology consult"],
                    "treatment_considerations": [],
                    "clinical_pearls": ["Door-to-balloon time <90 minutes critical"]
                },
                "risk_stratification": "CRITICAL",
                "urgency": "EMERGENT",
                "references": ["ACC/AHA STEMI Guidelines 2021"],
                "tools_used": ["tavily_web_search"],
                "thinking_summary": "Analyzed ECG findings → Identified STEMI criteria → Generated management plan",
                "clinical_caveat": "Clinical decision support only. Verify findings independently."
            }
        }
    )


class ProfessionalStreamEvent(BaseModel):
    """
    Streaming event for professional SSE responses.
    
    Event types:
    - clinical_thinking: Clinical reasoning process
    - content: Response content chunks
    - differential: Differential diagnosis updates
    - workup: Recommended workup suggestions
    - imaging_analysis: Imaging findings (for radiology)
    - tool: Tool usage information
    - complete: Final event with full response
    - error: Error occurred
    """
    type: str = Field(
        ...,
        description="Event type: clinical_thinking, content, differential, workup, imaging_analysis, tool, complete, error"
    )
    data: Any = Field(..., description="Event data (varies by type)")
    timestamp: Optional[str] = Field(None, description="Event timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "clinical_thinking",
                    "data": "Analyzing presentation: acute chest pain with ST elevation suggests ACS...",
                    "timestamp": "2025-12-03T10:00:00"
                },
                {
                    "type": "differential",
                    "data": {
                        "condition": "STEMI",
                        "likelihood": "HIGH",
                        "rationale": "ST elevation in contiguous leads"
                    },
                    "timestamp": "2025-12-03T10:00:01"
                },
                {
                    "type": "complete",
                    "data": {
                        "session_id": "uuid",
                        "risk_stratification": "CRITICAL",
                        "urgency": "EMERGENT"
                    },
                    "timestamp": "2025-12-03T10:00:10"
                }
            ]
        }
    )

