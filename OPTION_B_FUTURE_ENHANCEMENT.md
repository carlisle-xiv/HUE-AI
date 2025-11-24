# Option B: Comprehensive Medical Response Enhancement (Future Task)

## Status
**Not Started** - This is a follow-up enhancement to Option A (Image Specificity Fix)

## Prerequisites
✅ Option A must be completed, tested, and validated in production  
✅ User feedback collected on image response improvements  
✅ Baseline metrics established for response quality

---

## Problem Statement

Currently, the system provides different quality responses based on input type:

| Input Type | Current Behavior | Desired Behavior |
|-----------|------------------|------------------|
| **Image + Question** | ✅ Specific findings (after Option A) | ✅ Specific findings |
| **Symptoms + Vitals** | ❌ Often generic advice | ✅ Specific, actionable guidance |
| **General Education** | ✅ Good educational content | ✅ Maintain quality |

**The Gap:** Users asking about THEIR symptoms with PROVIDED context (vitals, history) still get generic responses like "chest pain can be caused by many things..." instead of "Your elevated BP (160/95) combined with chest pain requires immediate attention..."

---

## Solution Overview

Enhance the base system prompt to distinguish between:
1. **Personal Health Queries** - Questions about user's own health with context
2. **Educational Queries** - General health information requests

Apply different response strategies:
- **Personal → Specific, contextual, actionable**
- **Educational → Informative, comprehensive, general**

---

## Scope

### In Scope
1. Enhanced system prompt with dual-mode instructions
2. Intent classification to detect personal vs. educational queries
3. Context-aware response generation for symptoms + vitals
4. Improved risk assessment integration into responses
5. Better utilization of patient history and conditions

### Out of Scope
- Image analysis improvements (handled by Option A)
- Additional tool development
- UI/UX changes
- Database schema modifications

---

## Technical Approach

### 1. Intent Classification

Add a lightweight intent classifier at the beginning of response generation:

```python
def classify_user_intent(message: str, has_patient_context: bool) -> str:
    """
    Classify user query intent.
    
    Returns:
        - "PERSONAL_HEALTH": User asking about their own health
        - "EDUCATIONAL": User seeking general health information
        - "FOLLOW_UP": Continuation of previous conversation
    """
    # Check for personal pronouns and health indicators
    personal_indicators = [
        "my", "i have", "i'm feeling", "should i",
        "am i", "do i need", "is my", "my symptoms"
    ]
    
    educational_indicators = [
        "what is", "what are", "how does", "tell me about",
        "explain", "definition of", "information about"
    ]
    
    message_lower = message.lower()
    
    # Personal health query if:
    # - Contains personal pronouns AND health context
    # - Has patient context (vitals, symptoms, etc.)
    if any(ind in message_lower for ind in personal_indicators):
        return "PERSONAL_HEALTH"
    
    # Educational if clearly asking for general info
    if any(ind in message_lower for ind in educational_indicators):
        if not has_patient_context:
            return "EDUCATIONAL"
    
    # Default to personal if patient context exists
    return "PERSONAL_HEALTH" if has_patient_context else "EDUCATIONAL"
```

### 2. Enhanced System Prompts

#### For Personal Health Queries:
```python
PERSONAL_HEALTH_PROMPT = """
You are an AI health consultant analyzing a patient's specific health situation.

**CRITICAL INSTRUCTIONS:**
1. Your response must address THEIR specific situation:
   - Reference their actual symptoms, vitals, and history provided
   - Provide personalized guidance based on THEIR data
   - Give specific, actionable recommendations

2. If vital signs are abnormal, explicitly state what's concerning:
   - "Your blood pressure of 160/95 is elevated..."
   - "Your heart rate of 110 bpm while resting is higher than normal..."

3. If symptoms are described, connect them to their context:
   - "Given your chest pain along with elevated BP and family history of heart disease..."

4. Provide specific next steps:
   - "Based on these symptoms, you should see a doctor within 24 hours..."
   - "This combination suggests you may need emergency care..."

DO NOT give generic "here are the possible causes" lists. Focus on THEIR situation.
"""

#### For Educational Queries:
```python
EDUCATIONAL_PROMPT = """
You are an AI health educator providing clear, accurate health information.

**INSTRUCTIONS:**
1. Provide comprehensive, educational content
2. Use clear explanations suitable for patients
3. Include relevant statistics and guidelines when helpful
4. Maintain accuracy and cite general medical knowledge

This is a general information request, so provide educational content.
"""
```

### 3. Dynamic Prompt Construction

```python
def build_enhanced_system_prompt(
    intent: str,
    patient_context: str,
    has_image_analysis: bool
) -> str:
    """Build system prompt based on query intent and available context."""
    
    base = "You are an AI health consultant. "
    
    # Add intent-specific instructions
    if intent == "PERSONAL_HEALTH":
        base += PERSONAL_HEALTH_PROMPT
    else:
        base += EDUCATIONAL_PROMPT
    
    # Add image-specific instructions if present (Option A)
    if has_image_analysis:
        base += IMAGE_ANALYSIS_PROMPT
    
    # Add patient context
    if patient_context:
        base += f"\n\nPatient Context:\n{patient_context}"
    
    return base
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Implement intent classification function
- [ ] Create enhanced prompt templates
- [ ] Add dynamic prompt builder
- [ ] Unit tests for intent classification

### Phase 2: Integration (Week 2)
- [ ] Integrate into `build_chat_messages()` (service.py)
- [ ] Integrate into OpenAI service (openai_service.py)
- [ ] Add logging for intent classification
- [ ] Integration tests

### Phase 3: Validation (Week 3)
- [ ] A/B testing framework setup
- [ ] Collect baseline metrics (response quality, user satisfaction)
- [ ] Run tests with various query types
- [ ] Analyze improvement metrics

### Phase 4: Refinement (Week 4)
- [ ] Adjust thresholds based on validation results
- [ ] Fine-tune prompt wording
- [ ] Edge case handling
- [ ] Documentation and training materials

---

## Testing Strategy

### Test Cases

#### 1. Personal Health with Vitals
**Input:**
```json
{
  "message": "I have chest pain and shortness of breath",
  "vitals_data": {
    "blood_pressure_systolic": 160,
    "blood_pressure_diastolic": 95,
    "heart_rate_bpm": 110
  }
}
```

**Expected Response:**
```
"Based on your specific situation - chest pain and shortness of breath 
combined with elevated blood pressure (160/95) and elevated heart rate 
(110 bpm) - this requires immediate medical attention. These symptoms 
together can indicate a serious cardiac issue.

I strongly recommend:
1. Call emergency services (911) or go to the ER immediately
2. Do not drive yourself - have someone take you
3. Take aspirin if available and not allergic (standard cardiac protocol)

Your elevated vital signs combined with these symptoms cannot wait for 
a regular appointment."
```

#### 2. Educational Query (Should NOT Change)
**Input:**
```json
{
  "message": "What is hypertension?"
}
```

**Expected Response:**
```
"Hypertension, also known as high blood pressure, is a condition where...
[Standard educational content - unchanged]"
```

#### 3. Personal Health with History
**Input:**
```json
{
  "message": "Should I be concerned about my headaches?",
  "conditions_data": {
    "conditions": [
      {"condition_name": "Hypertension", "status": "ACTIVE"}
    ]
  },
  "vitals_data": {
    "blood_pressure_systolic": 165,
    "blood_pressure_diastolic": 100
  }
}
```

**Expected Response:**
```
"Given your active hypertension diagnosis and your current blood pressure 
reading of 165/100 (which is significantly elevated), your headaches are 
concerning and need immediate attention.

Severe headaches can be a sign that your blood pressure is dangerously high...
[Specific guidance based on THEIR situation]"
```

---

## Success Metrics

### Quantitative
- **Response Specificity Score:** % of responses that reference user's specific data
- **Actionability Score:** % of responses with clear next steps
- **User Satisfaction:** Rating increase (baseline vs. Option B)
- **Follow-up Reduction:** Fewer "what about MY situation?" follow-ups

### Qualitative
- Response feels personalized to user's situation
- Clear, actionable guidance provided
- Appropriate urgency level for symptoms
- No loss of educational quality for general queries

### Target Improvements
- 90%+ of personal health queries include specific data references
- 85%+ include actionable next steps
- 40%+ improvement in user satisfaction scores
- 30%+ reduction in clarification follow-ups

---

## Risks & Mitigations

### Risk 1: Over-Specificity Leading to Incorrect Medical Advice
**Mitigation:**
- Maintain strong disclaimers
- Always recommend doctor consultation for serious symptoms
- Never provide definitive diagnoses
- Include safety nets ("If symptoms worsen, seek immediate care")

### Risk 2: Intent Classification Errors
**Mitigation:**
- Conservative defaults (personal health when uncertain)
- Logging and monitoring of classifications
- Manual review of edge cases
- Continuous refinement based on feedback

### Risk 3: Degraded Educational Responses
**Mitigation:**
- Preserve current educational prompt quality
- A/B testing to ensure no regression
- Separate evaluation metrics for educational queries

---

## Dependencies

### Technical
- Option A (image specificity) must be stable
- Logging infrastructure for intent tracking
- A/B testing capability (optional but recommended)

### Resources
- 1-2 weeks development time
- Testing resources for validation
- Medical SME review of enhanced prompts

---

## Future Enhancements (Beyond Option B)

1. **Machine Learning Intent Classification**
   - Replace rule-based with ML model
   - Train on user interaction data
   - Continuous improvement

2. **Contextual Risk Scoring**
   - ML-based severity assessment
   - Real-time urgency detection
   - Automated escalation paths

3. **Multi-Turn Context Awareness**
   - Remember previous conversation context
   - Build patient profile over session
   - Progressive disclosure strategy

4. **Personalized Communication Style**
   - Adapt complexity to user literacy level
   - Cultural sensitivity adjustments
   - Preference learning (detailed vs. concise)

---

## Approval & Next Steps

### Before Starting Option B:

1. ✅ Validate Option A in production (1-2 weeks)
2. ✅ Collect user feedback on image improvements
3. ✅ Establish baseline metrics
4. ✅ Get stakeholder approval for Option B scope
5. ✅ Allocate development resources

### Decision Points:

- **GO:** If Option A shows measurable improvement and stakeholders approve
- **WAIT:** If Option A needs refinement or resources unavailable
- **PIVOT:** If user feedback suggests different priorities

---

## Questions for Discussion

1. Should intent classification be rule-based or ML-based initially?
2. What baseline metrics should we collect before Option B?
3. How do we handle edge cases (mixed intents in one query)?
4. Should we implement gradual rollout or full deployment?
5. What level of medical SME review is needed for enhanced prompts?

---

## Contact

**Task Owner:** AI Development Team  
**Medical Reviewer:** TBD  
**Priority:** Medium (after Option A validation)  
**Timeline:** 4 weeks estimated (after Option A stable)

---

**Last Updated:** November 2024  
**Status:** Planning Phase - Awaiting Option A Validation

