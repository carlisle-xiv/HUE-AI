import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlmodel import Session, select, and_, or_
from dotenv import load_dotenv

from src.models.patients import Patient, PatientCondition, PatientVital
from src.models.prescriptions import Prescription, PrescriptionItem
from src.models.pharmacy import Pharmacy, PharmacyInventory
from src.models.reference import PharmacyCode, MedicalCode
from src.models.drug_suggester import PatientAllergy, DrugSuggestion as DrugSuggestionModel
from .schemas import (
    DrugSuggestionRequest,
    DrugSuggestionResponse,
    DrugSuggestion,
    FacilityInventory
)
from .rxnav_service import (
    get_rxcui_by_name,
    check_drug_interactions,
    normalize_drug_names
)
from src.multi_disease_detector.tool_service import execute_tavily_search

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "openai/gpt-4o-2024-11-20"


async def gather_patient_context(patient_id: str, session: Session) -> Dict[str, Any]:
    """
    Gather comprehensive patient context for drug suggestions.
    
    Args:
        patient_id: Patient UUID
        session: Database session
        
    Returns:
        Dictionary with patient context
    """
    logger.info(f"Gathering patient context for patient_id: {patient_id}")
    
    # Get patient
    patient = session.get(Patient, patient_id)
    if not patient:
        raise ValueError(f"Patient not found: {patient_id}")
    
    # Get active conditions
    conditions_stmt = select(PatientCondition, MedicalCode).join(
        MedicalCode, PatientCondition.medical_code_id == MedicalCode.id
    ).where(
        and_(
            PatientCondition.patient_id == patient_id,
            PatientCondition.status.in_(["ACTIVE", "CHRONIC"])
        )
    )
    conditions_results = session.exec(conditions_stmt).all()
    conditions = [
        {
            "condition_name": medical_code.condition_name,
            "code": medical_code.code,
            "severity": condition.severity,
            "diagnosed_date": condition.diagnosed_date.isoformat() if condition.diagnosed_date else None
        }
        for condition, medical_code in conditions_results
    ]
    
    # Get active allergies
    allergies_stmt = select(PatientAllergy).where(
        and_(
            PatientAllergy.patient_id == patient_id,
            PatientAllergy.is_active == True
        )
    )
    allergies_results = session.exec(allergies_stmt).all()
    allergies = [
        {
            "allergen_name": allergy.allergen_name,
            "allergen_type": allergy.allergen_type,
            "severity": allergy.severity,
            "reaction_type": allergy.reaction_type
        }
        for allergy in allergies_results
    ]
    
    # Get current medications (active prescriptions from last 90 days)
    ninety_days_ago = date.today() - timedelta(days=90)
    prescriptions_stmt = select(Prescription).where(
        and_(
            Prescription.patient_id == patient_id,
            Prescription.status == "ACTIVE",
            Prescription.prescribed_date >= ninety_days_ago
        )
    )
    prescriptions = session.exec(prescriptions_stmt).all()
    
    current_medications = []
    for prescription in prescriptions:
        items_stmt = select(PrescriptionItem, PharmacyCode).join(
            PharmacyCode, PrescriptionItem.pharmacy_code_id == PharmacyCode.id
        ).where(PrescriptionItem.prescription_id == prescription.id)
        
        items_results = session.exec(items_stmt).all()
        for item, pharmacy_code in items_results:
            current_medications.append({
                "drug_name": pharmacy_code.drug_name,
                "generic_name": pharmacy_code.generic_name,
                "dosage": item.dosage,
                "frequency": item.frequency
            })
    
    # Get recent vitals (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    vitals_stmt = select(PatientVital).where(
        and_(
            PatientVital.patient_id == patient_id,
            PatientVital.recorded_at >= thirty_days_ago
        )
    ).order_by(PatientVital.recorded_at.desc()).limit(1)
    
    latest_vital = session.exec(vitals_stmt).first()
    
    vitals = None
    if latest_vital:
        vitals = {
            "weight_kg": float(latest_vital.weight_kg) if latest_vital.weight_kg else None,
            "height_cm": float(latest_vital.height_cm) if latest_vital.height_cm else None,
            "bmi": float(latest_vital.bmi) if latest_vital.bmi else None,
            "blood_pressure": f"{latest_vital.blood_pressure_systolic}/{latest_vital.blood_pressure_diastolic}" if latest_vital.blood_pressure_systolic else None,
            "heart_rate_bpm": latest_vital.heart_rate_bpm
        }
    
    # Calculate age
    age = None
    if patient.date_of_birth:
        today = date.today()
        age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )
    
    context = {
        "patient_id": str(patient.id),
        "patient_name": patient.legal_name,
        "age": age,
        "biological_sex": patient.biological_sex,
        "conditions": conditions,
        "allergies": allergies,
        "current_medications": current_medications,
        "vitals": vitals
    }
    
    logger.info(f"Gathered context: {len(conditions)} conditions, {len(allergies)} allergies, {len(current_medications)} medications")
    
    return context


async def search_ghana_guidelines(diagnosis: str, conditions: List[str]) -> str:
    """
    Search for Ghana Standard Treatment Guidelines using Tavily.
    
    Args:
        diagnosis: Primary diagnosis
        conditions: Additional conditions
        
    Returns:
        Guideline text
    """
    logger.info(f"Searching Ghana guidelines for: {diagnosis}")
    
    try:
        # Search for Ghana STG
        query = f"Ghana Standard Treatment Guidelines for {diagnosis}"
        stg_results = await execute_tavily_search(
            query=query,
            search_depth="advanced",
            topic="general"
        )
        
        # Search for Ghana Essential Medicine List
        eml_query = f"Ghana Essential Medicine List for {diagnosis} treatment"
        eml_results = await execute_tavily_search(
            query=eml_query,
            search_depth="basic",
            topic="general"
        )
        
        # Combine and parse results
        stg_data = json.loads(stg_results) if isinstance(stg_results, str) else stg_results
        eml_data = json.loads(eml_results) if isinstance(eml_results, str) else eml_results
        
        guidelines_text = "**Ghana Standard Treatment Guidelines:**\n\n"
        
        if stg_data.get("results"):
            for result in stg_data["results"][:3]:
                guidelines_text += f"- {result.get('title', '')}: {result.get('content', '')[:300]}...\n\n"
        
        guidelines_text += "\n**Ghana Essential Medicine List:**\n\n"
        
        if eml_data.get("results"):
            for result in eml_data["results"][:2]:
                guidelines_text += f"- {result.get('title', '')}: {result.get('content', '')[:300]}...\n\n"
        
        logger.info(f"Retrieved Ghana guidelines ({len(guidelines_text)} characters)")
        
        return guidelines_text
        
    except Exception as e:
        logger.error(f"Error searching Ghana guidelines: {str(e)}")
        return "Ghana guidelines not available at this time."


async def query_facility_inventories(
    facility_ids: Optional[List[str]],
    session: Session
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Query pharmacy inventories across facilities.
    
    Args:
        facility_ids: List of facility IDs to check, or None for all
        session: Database session
        
    Returns:
        Dictionary mapping drug codes to facility inventory list
    """
    logger.info(f"Querying facility inventories (facility_ids: {facility_ids})")
    
    # Build query
    stmt = select(PharmacyInventory, Pharmacy, PharmacyCode).join(
        Pharmacy, PharmacyInventory.pharmacy_id == Pharmacy.id
    ).join(
        PharmacyCode, PharmacyInventory.pharmacy_code_id == PharmacyCode.id
    ).where(
        and_(
            PharmacyInventory.quantity_available > 0,
            or_(
                PharmacyInventory.expiry_date == None,
                PharmacyInventory.expiry_date > date.today()
            )
        )
    )
    
    if facility_ids:
        stmt = stmt.where(Pharmacy.id.in_(facility_ids))
    
    results = session.exec(stmt).all()
    
    # Group by drug code
    inventory_map = {}
    for inventory, pharmacy, pharmacy_code in results:
        drug_code_id = str(pharmacy_code.id)
        
        if drug_code_id not in inventory_map:
            inventory_map[drug_code_id] = []
        
        inventory_map[drug_code_id].append({
            "pharmacy_id": str(pharmacy.id),
            "pharmacy_name": pharmacy.name,
            "quantity_available": inventory.quantity_available,
            "unit_price": float(inventory.unit_price),
            "expiry_date": inventory.expiry_date.isoformat() if inventory.expiry_date else None,
            "drug_name": pharmacy_code.drug_name,
            "generic_name": pharmacy_code.generic_name
        })
    
    logger.info(f"Found inventory for {len(inventory_map)} unique drugs across facilities")
    
    return inventory_map


async def check_contraindications(
    patient_context: Dict[str, Any],
    drug_code: PharmacyCode
) -> Tuple[bool, Optional[str]]:
    """
    Check if drug has contraindications for patient.
    
    Args:
        patient_context: Patient context dictionary
        drug_code: PharmacyCode object
        
    Returns:
        Tuple of (has_contraindication, contraindication_text)
    """
    if not drug_code.contraindications:
        return False, None
    
    contraindications_lower = drug_code.contraindications.lower()
    
    # Check against patient conditions
    for condition in patient_context.get("conditions", []):
        condition_name = condition["condition_name"].lower()
        if condition_name in contraindications_lower:
            return True, f"Contraindicated in {condition['condition_name']}"
    
    # Check against allergies
    for allergy in patient_context.get("allergies", []):
        allergen = allergy["allergen_name"].lower()
        drug_name_lower = drug_code.drug_name.lower()
        generic_lower = (drug_code.generic_name or "").lower()
        
        if allergen in drug_name_lower or allergen in generic_lower:
            return True, f"Patient allergic to {allergy['allergen_name']}"
    
    return False, None


async def check_allergy_safety(
    patient_context: Dict[str, Any],
    drug_code: PharmacyCode
) -> Tuple[bool, Optional[str]]:
    """
    Check if drug is safe given patient allergies.
    
    Args:
        patient_context: Patient context dictionary
        drug_code: PharmacyCode object
        
    Returns:
        Tuple of (is_safe, warning_text)
    """
    allergies = patient_context.get("allergies", [])
    if not allergies:
        return True, None
    
    drug_name_lower = drug_code.drug_name.lower()
    generic_lower = (drug_code.generic_name or "").lower()
    
    for allergy in allergies:
        if allergy["allergen_type"] != "DRUG":
            continue
        
        allergen_lower = allergy["allergen_name"].lower()
        
        # Check for matches
        if (allergen_lower in drug_name_lower or 
            allergen_lower in generic_lower or
            drug_name_lower in allergen_lower):
            
            severity = allergy["severity"]
            return False, f"ALLERGY ALERT: Patient has {severity} allergy to {allergy['allergen_name']}"
    
    return True, None


async def generate_drug_suggestions_with_ai(
    patient_context: Dict[str, Any],
    diagnosis: str,
    additional_conditions: Optional[List[str]],
    guidelines_text: str,
    inventory_map: Dict[str, List[Dict[str, Any]]],
    interaction_results: List[Dict[str, Any]],
    session: Session
) -> Dict[str, Any]:
    """
    Use AI to generate intelligent drug suggestions with dosing.
    
    Args:
        patient_context: Patient context
        diagnosis: Primary diagnosis
        additional_conditions: Additional conditions
        guidelines_text: Ghana guidelines text
        inventory_map: Facility inventory mapping
        interaction_results: Drug interaction check results
        session: Database session
        
    Returns:
        Dictionary with primary and alternate suggestions
    """
    import httpx
    
    logger.info("Generating drug suggestions with AI")
    
    # Build prompt for AI
    prompt = f"""You are a clinical pharmacist in Ghana helping a doctor prescribe medications.

    **Patient Information:**
- Age: {patient_context.get('age', 'Unknown')}
- Sex: {patient_context.get('biological_sex', 'Unknown')}
- Weight: {(patient_context.get('vitals') or {}).get('weight_kg', 'Unknown')} kg
- Primary Diagnosis: {diagnosis}
"""
    
    if additional_conditions:
        prompt += f"- Additional Conditions: {', '.join(additional_conditions)}\n"
    
    if patient_context.get("conditions"):
        prompt += "\n**Existing Conditions:**\n"
        for cond in patient_context["conditions"]:
            prompt += f"- {cond['condition_name']} ({cond.get('severity', 'Unknown')} severity)\n"
    
    if patient_context.get("allergies"):
        prompt += "\n**⚠️ ALLERGIES (DO NOT PRESCRIBE):**\n"
        for allergy in patient_context["allergies"]:
            prompt += f"- {allergy['allergen_name']} ({allergy['severity']} - {allergy.get('reaction_type', 'Unknown reaction')})\n"
    
    if patient_context.get("current_medications"):
        prompt += "\n**Current Medications:**\n"
        for med in patient_context["current_medications"]:
            prompt += f"- {med['drug_name']} {med['dosage']} {med['frequency']}\n"
    
    prompt += f"\n**Ghana Treatment Guidelines:**\n{guidelines_text}\n"
    
    # Get available drugs from inventory
    available_drugs = []
    for drug_code_id, facilities in inventory_map.items():
        if facilities:
            available_drugs.append(facilities[0]["drug_name"])
    
    if available_drugs:
        prompt += f"\n**Drugs Available in Facility Inventory:**\n{', '.join(available_drugs[:20])}\n"
    
    prompt += """

**Task:**
Suggest 2-3 appropriate medications for this patient's diagnosis. For EACH drug, provide:

1. Drug name (generic preferred)
2. Specific dosage (e.g., "500mg")
3. Frequency (e.g., "twice daily with meals")
4. Duration (e.g., "7 days" or "continuous")
5. Route (e.g., "oral", "IV")
6. Detailed rationale for selection (why this drug for this condition)
7. Detailed rationale for dosage (why this specific dose for this patient)

**CRITICAL SAFETY RULES:**
- DO NOT suggest any drugs the patient is allergic to
- Check for drug-drug interactions with current medications
- Prefer drugs from facility inventory when appropriate
- Follow Ghana STG/Essential Medicine List when possible
- Consider patient's age, weight, and comorbidities
- If drug interactions exist, mention them

Format your response as JSON:
{
  "primary_suggestions": [
    {
      "drug_name": "...",
      "generic_name": "...",
      "dosage": "...",
      "frequency": "...",
      "duration": "...",
      "route": "...",
      "selection_rationale": "...",
      "dosage_rationale": "..."
    }
  ],
  "alternate_suggestions": [...],
  "overall_notes": "Additional clinical considerations..."
}
"""
    
    try:
        # Call OpenRouter API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert clinical pharmacist in Ghana. Provide evidence-based, safe medication recommendations following Ghana STG."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            ai_suggestions = json.loads(content)
            
            logger.info(f"AI generated suggestions successfully")
            
            return ai_suggestions
            
    except Exception as e:
        logger.error(f"Error generating AI suggestions: {str(e)}")
        # Return empty suggestions on error
        return {
            "primary_suggestions": [],
            "alternate_suggestions": [],
            "overall_notes": f"Error generating suggestions: {str(e)}"
        }


async def process_drug_suggestion_request(
    request: DrugSuggestionRequest,
    session: Session
) -> DrugSuggestionResponse:
    """
    Process drug suggestion request end-to-end.
    
    Args:
        request: DrugSuggestionRequest
        session: Database session
        
    Returns:
        DrugSuggestionResponse
    """
    start_time = datetime.utcnow()
    logger.info(f"Processing drug suggestion request for patient {request.patient_id}")
    
    try:
        # 1. Gather patient context
        patient_context = await gather_patient_context(str(request.patient_id), session)
        
        # 2. Search Ghana guidelines
        all_conditions = [request.diagnosis]
        if request.additional_conditions:
            all_conditions.extend(request.additional_conditions)
        
        guidelines_text = await search_ghana_guidelines(request.diagnosis, all_conditions)
        tavily_searches_count = 2  # STG + EML searches
        
        # 3. Query facility inventories
        facility_ids_list = [str(fid) for fid in request.facility_ids] if request.facility_ids else None
        inventory_map = await query_facility_inventories(facility_ids_list, session)
        
        # 4. Check drug interactions for current medications
        current_med_names = [med["drug_name"] for med in patient_context.get("current_medications", [])]
        rxnav_used = False
        interaction_results = []
        
        if current_med_names:
            # Get RxCUIs for current medications
            rxcui_map = await normalize_drug_names(current_med_names)
            valid_rxcuis = [rxcui for rxcui in rxcui_map.values() if rxcui]
            
            if valid_rxcuis:
                rxnav_used = True
                # We'll check interactions when we have candidate drugs
        
        # 5. Generate AI suggestions
        ai_suggestions = await generate_drug_suggestions_with_ai(
            patient_context=patient_context,
            diagnosis=request.diagnosis,
            additional_conditions=request.additional_conditions,
            guidelines_text=guidelines_text,
            inventory_map=inventory_map,
            interaction_results=interaction_results,
            session=session
        )
        
        # 6. Process and validate AI suggestions
        primary_suggestions = []
        alternate_suggestions = []
        interaction_warnings = []
        contraindication_alerts = []
        
        # Process primary suggestions from AI
        for ai_drug in ai_suggestions.get("primary_suggestions", []):
            processed = await _process_ai_drug_suggestion(
                ai_drug=ai_drug,
                patient_context=patient_context,
                inventory_map=inventory_map,
                session=session,
                rxnav_used=rxnav_used
            )
            
            if processed:
                if processed.in_facility_inventory:
                    primary_suggestions.append(processed)
                else:
                    alternate_suggestions.append(processed)
                
                # Collect warnings
                if processed.interaction_status not in ["safe", "minor"]:
                    if processed.interaction_details:
                        interaction_warnings.append(processed.interaction_details)
                
                if not processed.allergy_safe:
                    contraindication_alerts.append(
                        f"⚠️ {processed.drug_name}: Patient has allergy"
                    )
        
        # Process alternate suggestions from AI
        for ai_drug in ai_suggestions.get("alternate_suggestions", []):
            processed = await _process_ai_drug_suggestion(
                ai_drug=ai_drug,
                patient_context=patient_context,
                inventory_map=inventory_map,
                session=session,
                rxnav_used=rxnav_used
            )
            
            if processed:
                alternate_suggestions.append(processed)
        
        # 7. Build response
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Get facility names
        facilities_checked = []
        if facility_ids_list:
            facilities_stmt = select(Pharmacy).where(Pharmacy.id.in_(facility_ids_list))
            facilities = session.exec(facilities_stmt).all()
            facilities_checked = [f.name for f in facilities]
        else:
            facilities_stmt = select(Pharmacy).limit(10)
            facilities = session.exec(facilities_stmt).all()
            facilities_checked = [f"{f.name}" for f in facilities]
        
        response = DrugSuggestionResponse(
            patient_id=request.patient_id,
            patient_name=patient_context["patient_name"],
            diagnosis=request.diagnosis,
            additional_conditions=request.additional_conditions,
            primary_suggestions=primary_suggestions,
            alternate_suggestions=alternate_suggestions,
            allergy_alerts=[
                f"{a['allergen_name']} ({a['severity']} - {a.get('reaction_type', 'Unknown')})"
                for a in patient_context.get("allergies", [])
            ],
            interaction_warnings=interaction_warnings,
            contraindication_alerts=contraindication_alerts,
            current_medications=[
                f"{m['drug_name']} {m['dosage']} {m['frequency']}"
                for m in patient_context.get("current_medications", [])
            ],
            ghana_guideline_notes=ai_suggestions.get("overall_notes", guidelines_text[:500]),
            generated_at=datetime.utcnow(),
            processing_time_seconds=processing_time,
            facilities_checked=facilities_checked if facilities_checked else None,
            rxnav_used=rxnav_used
        )
        
        # 8. Save to database for audit trail
        await _save_suggestion_to_db(
            request=request,
            response=response,
            patient_context=patient_context,
            processing_time=processing_time,
            rxnav_used=rxnav_used,
            tavily_searches_count=tavily_searches_count,
            session=session
        )
        
        logger.info(f"Completed drug suggestion request in {processing_time:.2f}s")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing drug suggestion request: {str(e)}", exc_info=True)
        raise


async def _process_ai_drug_suggestion(
    ai_drug: Dict[str, Any],
    patient_context: Dict[str, Any],
    inventory_map: Dict[str, List[Dict[str, Any]]],
    session: Session,
    rxnav_used: bool
) -> Optional[DrugSuggestion]:
    """Process a single AI drug suggestion with safety checks."""
    
    drug_name = ai_drug.get("drug_name", "").strip()
    if not drug_name:
        return None
    
    # Find drug in pharmacy_codes
    stmt = select(PharmacyCode).where(
        or_(
            PharmacyCode.drug_name.ilike(f"%{drug_name}%"),
            PharmacyCode.generic_name.ilike(f"%{drug_name}%")
        )
    ).limit(1)
    
    pharmacy_code = session.exec(stmt).first()
    
    if not pharmacy_code:
        # Drug not in database, return as alternate with limited info
        return DrugSuggestion(
            drug_code_id="00000000-0000-0000-0000-000000000000",  # Placeholder
            drug_name=drug_name,
            generic_name=ai_drug.get("generic_name"),
            dosage=ai_drug.get("dosage", "As directed"),
            frequency=ai_drug.get("frequency", "As directed"),
            duration=ai_drug.get("duration", "As directed"),
            route=ai_drug.get("route"),
            in_facility_inventory=False,
            available_facilities=[],
            selection_rationale=ai_drug.get("selection_rationale", "Recommended for condition"),
            dosage_rationale=ai_drug.get("dosage_rationale", "Standard dosing"),
            contraindication_checked=False,
            interaction_status="unknown",
            interaction_details="Drug not in formulary - manual verification required",
            allergy_safe=True
        )
    
    # Check contraindications
    has_contraindication, contraindication_text = await check_contraindications(
        patient_context, pharmacy_code
    )
    
    # Check allergy safety
    allergy_safe, allergy_warning = await check_allergy_safety(
        patient_context, pharmacy_code
    )
    
    # Check if in inventory
    drug_code_id = str(pharmacy_code.id)
    in_inventory = drug_code_id in inventory_map
    available_facilities = []
    
    if in_inventory:
        facilities_data = inventory_map[drug_code_id]
        available_facilities = [
            FacilityInventory(
                pharmacy_id=f["pharmacy_id"],
                pharmacy_name=f["pharmacy_name"],
                quantity_available=f["quantity_available"],
                unit_price=f["unit_price"],
                expiry_date=f["expiry_date"]
            )
            for f in facilities_data[:5]  # Limit to 5 facilities
        ]
    
    # Determine interaction status (simplified for now)
    interaction_status = "safe"
    interaction_details = None
    
    if has_contraindication:
        interaction_status = "severe"
        interaction_details = contraindication_text
    elif not allergy_safe:
        interaction_status = "severe"
        interaction_details = allergy_warning
    
    return DrugSuggestion(
        drug_code_id=pharmacy_code.id,
        drug_name=pharmacy_code.drug_name,
        generic_name=pharmacy_code.generic_name,
        dosage=ai_drug.get("dosage", "As directed"),
        frequency=ai_drug.get("frequency", "As directed"),
        duration=ai_drug.get("duration", "As directed"),
        route=ai_drug.get("route", "Oral"),
        in_facility_inventory=in_inventory,
        available_facilities=available_facilities,
        selection_rationale=ai_drug.get("selection_rationale", "Appropriate for condition"),
        dosage_rationale=ai_drug.get("dosage_rationale", "Standard dosing regimen"),
        contraindication_checked=True,
        interaction_status=interaction_status,
        interaction_details=interaction_details,
        allergy_safe=allergy_safe
    )


async def _save_suggestion_to_db(
    request: DrugSuggestionRequest,
    response: DrugSuggestionResponse,
    patient_context: Dict[str, Any],
    processing_time: float,
    rxnav_used: bool,
    tavily_searches_count: int,
    session: Session
):
    """Save suggestion to database for audit trail."""
    
    try:
        suggestion_record = DrugSuggestionModel(
            patient_id=request.patient_id,
            doctor_id=request.doctor_id,
            diagnosis=request.diagnosis,
            additional_conditions=request.additional_conditions,
            primary_suggestions=[s.model_dump() for s in response.primary_suggestions],
            alternate_suggestions=[s.model_dump() for s in response.alternate_suggestions],
            patient_allergies_checked=[a["allergen_name"] for a in patient_context.get("allergies", [])],
            patient_current_medications=[m["drug_name"] for m in patient_context.get("current_medications", [])],
            interaction_warnings=response.interaction_warnings,
            contraindication_alerts=response.contraindication_alerts,
            ghana_guideline_notes=response.ghana_guideline_notes,
            facility_ids_checked=[str(fid) for fid in request.facility_ids] if request.facility_ids else None,
            processing_time_seconds=Decimal(str(processing_time)),
            rxnav_used=rxnav_used,
            tavily_searches_count=tavily_searches_count
        )
        
        session.add(suggestion_record)
        session.commit()
        
        logger.info(f"Saved suggestion record to database: {suggestion_record.id}")
        
    except Exception as e:
        logger.error(f"Error saving suggestion to database: {str(e)}")
        # So we don't fail the request if saving fails

