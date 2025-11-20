"""
ML-Based Risk Assessment System for Medical Queries

Uses a hybrid approach combining:
1. Rule-based emergency detection for obvious critical cases
2. MiniLM semantic embeddings for intent classification
3. Context-aware severity scoring

This reduces false positives while accurately identifying real emergencies.
"""

import logging
import os
import re
from typing import Tuple, Optional, Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Feature flag to enable/disable ML-based risk assessment
USE_SMART_RISK_ASSESSMENT = os.getenv("USE_SMART_RISK_ASSESSMENT", "true").lower() == "true"

# Lazy load ML model (only when needed)
_model = None
_model_load_attempted = False


def get_sentence_transformer():
    """
    Lazy load the sentence transformer model.
    Only loads once, then cached.
    """
    global _model, _model_load_attempted
    
    if _model_load_attempted:
        return _model
    
    _model_load_attempted = True
    
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        logger.info("Loading MiniLM model for risk assessment...")
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Use CPU explicitly (no GPU needed for this small model)
        if torch.cuda.is_available():
            logger.info("GPU available but using CPU for MiniLM (faster for small batches)")
        
        logger.info("MiniLM model loaded successfully")
        return _model
        
    except Exception as e:
        logger.error(f"Failed to load MiniLM model: {str(e)}")
        logger.warning("Falling back to rule-based risk assessment")
        return None


# ===== RULE-BASED EMERGENCY DETECTION =====

CRITICAL_EMERGENCY_PATTERNS = [
    # Life-threatening symptoms (require immediate action)
    r"\bcan't breathe\b|\bcannot breathe\b|\bunable to breathe\b",
    r"\bchest (pain|pressure).*(crushing|severe|radiating|arm|jaw)\b",
    r"\bstroke symptoms?\b|\bface drooping\b|\bslurred speech\b",
    r"\bseizure\b|\bconvuls",
    r"\bunconscious\b|\bunresponsive\b|\bpassed out\b",
    r"\bbleeding (heavily|profusely|won't stop)\b",
    r"\bsuicidal\b|\bhurt (myself|themselves)\b|\bwant to die\b",
    r"\bsevere (allergic reaction|anaphylaxis)\b",
    r"\bchest pain.*(shortness of breath|sweating|nausea)\b",
]

URGENT_MEDICAL_PATTERNS = [
    # Serious but not immediately life-threatening
    r"\bsevere pain\b.*\b(abdomen|stomach|head)\b",
    r"\bhigh fever\b.*(confusion|stiff neck|rash)\b",
    r"\bcoughing up blood\b|\bvomiting blood\b",
    r"\bsudden.*(vision loss|numbness|weakness)\b",
]


def detect_critical_emergency(text: str) -> bool:
    """
    Fast rule-based detection of obvious medical emergencies.
    Returns True if text contains critical emergency patterns.
    """
    text_lower = text.lower()
    
    for pattern in CRITICAL_EMERGENCY_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.info(f"Critical emergency pattern detected: {pattern}")
            return True
    
    return False


def detect_urgent_situation(text: str) -> bool:
    """
    Detect urgent (but not immediately life-threatening) situations.
    """
    text_lower = text.lower()
    
    for pattern in URGENT_MEDICAL_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.info(f"Urgent medical pattern detected: {pattern}")
            return True
    
    return False


# ===== INTENT CLASSIFICATION =====

# Reference embeddings for different intent categories
# These will be computed once and cached
INTENT_CATEGORIES = {
    "INFORMATIONAL": [
        "What is diabetes?",
        "How does hypertension work?",
        "Explain the symptoms of malaria",
        "What are the treatment guidelines for tuberculosis?",
        "According to medical standards, how is hypertension managed?",
        "Can you tell me about HIV prevention methods?",
        "What causes high blood pressure?",
        "How do I prevent heart disease?",
        "General information about medication side effects",
    ],
    "SYMPTOM_REPORT": [
        "I have a headache",
        "I'm experiencing chest pain",
        "I feel dizzy and nauseous",
        "My blood pressure is very high today",
        "I've been having fever for 3 days",
        "I'm feeling shortness of breath",
        "My symptoms are getting worse",
        "I woke up with severe pain",
    ],
    "MEDICATION_QUERY": [
        "Should I take aspirin?",
        "Can I stop my medication?",
        "What are the side effects of this drug?",
        "How long should I take antibiotics?",
        "Is it safe to combine these medications?",
        "When should I take my blood pressure medicine?",
    ],
    "MONITORING": [
        "Is my blood pressure normal?",
        "Are these test results concerning?",
        "Should I be worried about this reading?",
        "Is this symptom getting better?",
        "How often should I check my glucose?",
    ]
}

# Cache for reference embeddings
_reference_embeddings: Optional[Dict[str, Any]] = None


@lru_cache(maxsize=1)
def get_reference_embeddings():
    """
    Compute and cache reference embeddings for intent categories.
    """
    global _reference_embeddings
    
    if _reference_embeddings is not None:
        return _reference_embeddings
    
    model = get_sentence_transformer()
    if model is None:
        return None
    
    try:
        import numpy as np
        
        _reference_embeddings = {}
        
        for intent, examples in INTENT_CATEGORIES.items():
            # Encode all examples for this intent
            embeddings = model.encode(examples, convert_to_tensor=False)
            # Store mean embedding as the category centroid
            _reference_embeddings[intent] = np.mean(embeddings, axis=0)
        
        logger.info(f"Cached reference embeddings for {len(_reference_embeddings)} intent categories")
        return _reference_embeddings
        
    except Exception as e:
        logger.error(f"Failed to compute reference embeddings: {str(e)}")
        return None


def classify_intent_ml(user_message: str) -> Optional[str]:
    """
    Classify user intent using MiniLM embeddings and cosine similarity.
    
    Returns:
        Intent category (INFORMATIONAL, SYMPTOM_REPORT, MEDICATION_QUERY, MONITORING)
        or None if ML classification fails
    """
    model = get_sentence_transformer()
    if model is None:
        return None
    
    reference_embeddings = get_reference_embeddings()
    if reference_embeddings is None:
        return None
    
    try:
        import numpy as np
        from numpy.linalg import norm
        
        # Encode user message
        user_embedding = model.encode(user_message, convert_to_tensor=False)
        
        # Calculate cosine similarity with each intent category
        similarities = {}
        for intent, ref_embedding in reference_embeddings.items():
            # Cosine similarity
            similarity = np.dot(user_embedding, ref_embedding) / (
                norm(user_embedding) * norm(ref_embedding)
            )
            similarities[intent] = similarity
        
        # Get best matching intent
        best_intent = max(similarities, key=similarities.get)
        best_score = similarities[best_intent]
        
        logger.info(f"Intent classification: {best_intent} (confidence: {best_score:.3f})")
        logger.debug(f"All similarities: {similarities}")
        
        # Require minimum confidence threshold
        if best_score < 0.4:
            logger.warning("Low confidence in intent classification, using fallback")
            return None
        
        return best_intent
        
    except Exception as e:
        logger.error(f"Error in ML intent classification: {str(e)}")
        return None


def classify_intent_rules(user_message: str) -> str:
    """
    Fallback rule-based intent classification when ML is unavailable.
    """
    text_lower = user_message.lower()
    
    # Informational patterns
    informational_patterns = [
        r"^what (is|are|causes?|happens?)",
        r"^how (does|do|can|to)",
        r"^(explain|describe|tell me about)",
        r"\b(guidelines?|standards?|recommendations?)\b",
        r"\baccording to\b",
        r"\b(general|typical|common) (information|symptoms?|treatment)\b",
    ]
    
    for pattern in informational_patterns:
        if re.search(pattern, text_lower):
            return "INFORMATIONAL"
    
    # Symptom report patterns
    symptom_patterns = [
        r"^i (have|am|feel|experience)",
        r"^i've been",
        r"^my (head|chest|stomach|body)",
        r"\b(experiencing|suffering from|dealing with)\b.*\b(pain|fever|symptoms?)\b",
    ]
    
    for pattern in symptom_patterns:
        if re.search(pattern, text_lower):
            return "SYMPTOM_REPORT"
    
    # Medication query patterns
    medication_patterns = [
        r"\b(should|can|may) i (take|stop|use)\b",
        r"\b(medication|medicine|drug|pill)s?\b",
        r"\b(side effects?|interactions?|dosage)\b",
    ]
    
    for pattern in medication_patterns:
        if re.search(pattern, text_lower):
            return "MEDICATION_QUERY"
    
    # Monitoring patterns
    monitoring_patterns = [
        r"\b(is .*(normal|okay|fine|concerning))\b",
        r"\b(should i (be )?worried)\b",
        r"\b(test results?|readings?)\b",
    ]
    
    for pattern in monitoring_patterns:
        if re.search(pattern, text_lower):
            return "MONITORING"
    
    # Default to symptom report if uncertain
    return "SYMPTOM_REPORT"


def classify_intent(user_message: str) -> str:
    """
    Classify user message intent using hybrid approach.
    First tries ML, falls back to rules if ML fails.
    """
    # Try ML classification first
    if USE_SMART_RISK_ASSESSMENT:
        ml_intent = classify_intent_ml(user_message)
        if ml_intent:
            return ml_intent
    
    # Fallback to rule-based
    return classify_intent_rules(user_message)


# ===== SEVERITY SCORING =====

def get_temporal_urgency(text: str) -> float:
    """
    Analyze temporal indicators to determine urgency.
    Returns multiplier (0.5 to 2.0)
    """
    text_lower = text.lower()
    
    # Acute/sudden indicators (increase urgency)
    acute_patterns = [
        r"\b(sudden|suddenly|just now|started today)\b",
        r"\b(severe|intense|unbearable|worst)\b",
        r"\b(getting worse|worsening|deteriorating)\b",
        r"\b(can't|cannot|unable to)\b",
    ]
    
    # Chronic indicators (decrease urgency)
    chronic_patterns = [
        r"\b(for (weeks|months|years))\b",
        r"\b(chronic|long-term|ongoing)\b",
        r"\b(mild|slight|minor)\b",
        r"\b(improving|better|getting better)\b",
    ]
    
    acute_score = sum(1 for pattern in acute_patterns if re.search(pattern, text_lower))
    chronic_score = sum(1 for pattern in chronic_patterns if re.search(pattern, text_lower))
    
    if acute_score > chronic_score:
        return min(2.0, 1.0 + (acute_score * 0.3))
    elif chronic_score > acute_score:
        return max(0.5, 1.0 - (chronic_score * 0.2))
    else:
        return 1.0


def calculate_severity_score(
    user_message: str,
    intent: str,
    patient_context: str
) -> int:
    """
    Calculate severity score (0-100) based on intent, content, and context.
    
    Scoring:
    - 0-25: Informational, low risk
    - 26-50: Monitoring, mild concern
    - 51-75: Active symptoms, should see doctor
    - 76-100: Urgent/emergency
    """
    base_score = 0
    
    # Base score by intent
    intent_scores = {
        "INFORMATIONAL": 10,      # Low risk
        "MONITORING": 30,         # Mild concern
        "MEDICATION_QUERY": 40,   # Moderate concern
        "SYMPTOM_REPORT": 50,     # Active symptoms
    }
    
    base_score = intent_scores.get(intent, 40)
    
    # Apply temporal urgency multiplier
    temporal_multiplier = get_temporal_urgency(user_message)
    base_score = int(base_score * temporal_multiplier)
    
    # Check for high-risk keywords in user message (not patient context)
    user_lower = user_message.lower()
    
    high_risk_symptoms = [
        "severe pain", "chest pain", "difficulty breathing", 
        "shortness of breath", "bleeding", "vomiting blood",
        "confusion", "disoriented", "high fever"
    ]
    
    risk_matches = sum(1 for symptom in high_risk_symptoms if symptom in user_lower)
    base_score += (risk_matches * 15)
    
    # Reduce score for informational/educational language
    informational_indicators = [
        "what is", "how does", "explain", "guidelines", 
        "according to", "information about", "learn about"
    ]
    
    info_matches = sum(1 for indicator in informational_indicators if indicator in user_lower)
    if info_matches > 0:
        base_score = max(10, base_score - (info_matches * 10))
    
    # Cap at 100
    return min(100, max(0, base_score))


# ===== MAIN RISK ASSESSMENT FUNCTION =====

def calculate_risk_assessment_smart(
    ai_message: str,
    patient_context: str,
    user_message: str
) -> Tuple[str, bool]:
    """
    Smart, ML-enhanced risk assessment with context awareness.
    
    Args:
        ai_message: AI's response (checked for emergency language)
        patient_context: Patient's medical history (not used for risk scoring)
        user_message: Original user query (primary signal for intent/risk)
    
    Returns:
        Tuple of (risk_level, should_see_doctor)
        - risk_level: "LOW", "MEDIUM", "HIGH", or "EMERGENCY"
        - should_see_doctor: Boolean recommendation
    """
    try:
        # Step 1: Fast emergency detection (bypass ML for obvious cases)
        if detect_critical_emergency(user_message):
            logger.info("Critical emergency detected by rule-based system")
            return "EMERGENCY", True
        
        if detect_critical_emergency(ai_message):
            logger.info("AI response indicates emergency situation")
            return "EMERGENCY", True
        
        # Step 2: Urgent situation check
        if detect_urgent_situation(user_message):
            logger.info("Urgent medical situation detected")
            return "HIGH", True
        
        # Step 3: Classify intent
        intent = classify_intent(user_message)
        logger.info(f"Classified intent: {intent}")
        
        # Step 4: Calculate severity score
        severity_score = calculate_severity_score(
            user_message=user_message,
            intent=intent,
            patient_context=patient_context
        )
        
        logger.info(f"Severity score: {severity_score}/100")
        
        # Step 5: Map severity score to risk level
        if severity_score >= 76:
            risk_level = "EMERGENCY"
            should_see_doctor = True
        elif severity_score >= 51:
            risk_level = "HIGH"
            should_see_doctor = True
        elif severity_score >= 26:
            risk_level = "MEDIUM"
            should_see_doctor = True
        else:
            risk_level = "LOW"
            should_see_doctor = False
        
        logger.info(f"Final risk assessment: {risk_level}, See doctor: {should_see_doctor}")
        
        return risk_level, should_see_doctor
        
    except Exception as e:
        logger.error(f"Error in smart risk assessment: {str(e)}")
        # Fallback to conservative assessment
        logger.warning("Falling back to conservative HIGH risk assessment due to error")
        return "HIGH", True


# ===== LEGACY FUNCTION (BACKWARD COMPATIBILITY) =====

def calculate_risk_assessment_legacy(message: str, patient_context: str) -> Tuple[str, bool]:
    """
    Original keyword-based risk assessment (kept for backward compatibility).
    This is the old implementation with high false positive rates.
    """
    # Simple keyword-based risk assessment
    emergency_keywords = [
        "chest pain", "severe pain", "difficulty breathing", "unconscious",
        "bleeding heavily", "stroke", "heart attack", "emergency", "911"
    ]
    
    high_risk_keywords = [
        "blood pressure", "diabetes", "chronic", "severe", "urgent",
        "worsening", "persistent", "infection", "high fever"
    ]
    
    medium_risk_keywords = [
        "pain", "discomfort", "symptoms", "condition", "medication",
        "treatment", "concern", "monitor"
    ]
    
    combined_text = (message + " " + patient_context).lower()
    
    # Check for emergency
    if any(keyword in combined_text for keyword in emergency_keywords):
        return "EMERGENCY", True
    
    # Check for high risk
    if any(keyword in combined_text for keyword in high_risk_keywords):
        return "HIGH", True
    
    # Check for medium risk
    if any(keyword in combined_text for keyword in medium_risk_keywords):
        return "MEDIUM", True
    
    # Default to low risk
    return "LOW", False


# ===== PUBLIC API =====

def calculate_risk_assessment(
    message: str,
    patient_context: str,
    user_message: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Main risk assessment function with feature flag support.
    
    Args:
        message: AI response message
        patient_context: Patient's medical context
        user_message: Original user query (optional, for smart assessment)
    
    Returns:
        Tuple of (risk_level, should_see_doctor)
    """
    # Use smart assessment if enabled and user_message is provided
    if USE_SMART_RISK_ASSESSMENT and user_message:
        return calculate_risk_assessment_smart(
            ai_message=message,
            patient_context=patient_context,
            user_message=user_message
        )
    else:
        # Fallback to legacy assessment
        logger.info("Using legacy risk assessment")
        return calculate_risk_assessment_legacy(message, patient_context)

