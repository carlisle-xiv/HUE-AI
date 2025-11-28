"""
RxNav API integration service for drug interaction checking and normalization.
Provides caching for performance optimization.
"""

import json
import logging
import httpx
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal

from sqlmodel import Session, select
from src.database import engine
from src.models.drug_suggester import DrugInteractionCache

# Configure logging
logger = logging.getLogger(__name__)

# RxNav API configuration
RXNAV_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
CACHE_EXPIRY_DAYS = 7
REQUEST_TIMEOUT = 10  # seconds


async def get_rxcui_by_name(drug_name: str) -> Optional[str]:
    """
    Get RxCUI (RxNorm Concept Unique Identifier) for a drug name.
    
    Args:
        drug_name: Name of the drug to lookup
        
    Returns:
        RxCUI string or None if not found
    """
    try:
        url = f"{RXNAV_BASE_URL}/rxcui.json"
        params = {"name": drug_name}
        
        logger.info(f"Looking up RxCUI for drug: '{drug_name}'")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract RxCUI from response
            id_group = data.get("idGroup", {})
            rxnorm_ids = id_group.get("rxnormId", [])
            
            if rxnorm_ids and len(rxnorm_ids) > 0:
                rxcui = rxnorm_ids[0]  # Take first match
                logger.info(f"Found RxCUI '{rxcui}' for drug '{drug_name}'")
                return rxcui
            else:
                logger.warning(f"No RxCUI found for drug '{drug_name}'")
                return None
                
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting RxCUI for '{drug_name}': {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting RxCUI for '{drug_name}': {str(e)}")
        return None


async def check_drug_interactions(drug_rxcuis: List[str], drug_names: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Check interactions between multiple drugs using RxNav API.
    Uses caching to avoid redundant API calls.
    
    Args:
        drug_rxcuis: List of RxCUI codes to check
        drug_names: Mapping of RxCUI to drug names
        
    Returns:
        List of interaction dictionaries
    """
    if len(drug_rxcuis) < 2:
        logger.info("Less than 2 drugs provided, no interactions to check")
        return []
    
    interactions = []
    
    try:
        # Build list of unique pairs
        pairs_to_check = []
        for i, rxcui1 in enumerate(drug_rxcuis):
            for rxcui2 in drug_rxcuis[i+1:]:
                # Sort to ensure consistent cache key
                pair = tuple(sorted([rxcui1, rxcui2]))
                pairs_to_check.append(pair)
        
        logger.info(f"Checking {len(pairs_to_check)} drug pairs for interactions")
        
        # Check cache first
        with Session(engine) as session:
            for pair in pairs_to_check:
                rxcui1, rxcui2 = pair
                
                # Query cache
                statement = select(DrugInteractionCache).where(
                    DrugInteractionCache.drug1_rxcui == rxcui1,
                    DrugInteractionCache.drug2_rxcui == rxcui2
                ).order_by(DrugInteractionCache.checked_at.desc())
                
                cached = session.exec(statement).first()
                
                if cached and not cached.is_expired():
                    # Use cached result
                    logger.info(f"Using cached interaction data for {cached.drug1_name} + {cached.drug2_name}")
                    
                    if cached.interaction_severity:
                        interactions.append({
                            "drug1_name": cached.drug1_name,
                            "drug2_name": cached.drug2_name,
                            "drug1_rxcui": cached.drug1_rxcui,
                            "drug2_rxcui": cached.drug2_rxcui,
                            "severity": cached.interaction_severity,
                            "description": cached.interaction_description,
                            "source": cached.source,
                            "cached": True
                        })
                else:
                    # Fetch from API
                    interaction = await _fetch_interaction_from_api(
                        rxcui1, rxcui2,
                        drug_names.get(rxcui1, "Unknown"),
                        drug_names.get(rxcui2, "Unknown"),
                        session
                    )
                    
                    if interaction:
                        interactions.append(interaction)
        
        logger.info(f"Found {len(interactions)} drug interactions")
        return interactions
        
    except Exception as e:
        logger.error(f"Error checking drug interactions: {str(e)}")
        return []


async def _fetch_interaction_from_api(
    rxcui1: str,
    rxcui2: str,
    drug1_name: str,
    drug2_name: str,
    session: Session
) -> Optional[Dict[str, Any]]:
    """
    Fetch drug interaction from RxNav API and cache result.
    
    Args:
        rxcui1: First drug RxCUI
        rxcui2: Second drug RxCUI
        drug1_name: First drug name
        drug2_name: Second drug name
        session: Database session
        
    Returns:
        Interaction dictionary or None
    """
    try:
        url = f"{RXNAV_BASE_URL}/interaction/interaction.json"
        params = {"rxcui": rxcui1}
        
        logger.info(f"Fetching interaction data from RxNav for {drug1_name} + {drug2_name}")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse interaction data
            interaction_data = None
            severity = None
            description = None
            
            interaction_type_groups = data.get("interactionTypeGroup", [])
            
            for type_group in interaction_type_groups:
                interaction_types = type_group.get("interactionType", [])
                
                for interaction_type in interaction_types:
                    interaction_pairs = interaction_type.get("interactionPair", [])
                    
                    for pair in interaction_pairs:
                        # Check if this pair involves our second drug
                        interaction_concepts = pair.get("interactionConcept", [])
                        
                        # Check if rxcui2 is in the interaction
                        rxcuis_in_pair = [
                            concept.get("minConceptItem", {}).get("rxcui")
                            for concept in interaction_concepts
                        ]
                        
                        if rxcui2 in rxcuis_in_pair:
                            severity = pair.get("severity", "UNKNOWN")
                            description = pair.get("description", "No description available")
                            interaction_data = pair
                            break
                    
                    if interaction_data:
                        break
                
                if interaction_data:
                    break
            
            # Cache the result (even if no interaction found)
            cache_entry = DrugInteractionCache(
                drug1_rxcui=rxcui1,
                drug2_rxcui=rxcui2,
                drug1_name=drug1_name,
                drug2_name=drug2_name,
                interaction_severity=severity,
                interaction_description=description,
                source="RxNav",
                checked_at=datetime.utcnow(),
                expires_at=DrugInteractionCache.calculate_expiry_date(CACHE_EXPIRY_DAYS),
                raw_response=data
            )
            
            session.add(cache_entry)
            session.commit()
            
            logger.info(f"Cached interaction check for {drug1_name} + {drug2_name}")
            
            if severity:
                return {
                    "drug1_name": drug1_name,
                    "drug2_name": drug2_name,
                    "drug1_rxcui": rxcui1,
                    "drug2_rxcui": rxcui2,
                    "severity": severity,
                    "description": description,
                    "source": "RxNav",
                    "cached": False
                }
            else:
                return None
                
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching interaction from RxNav: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error fetching interaction from RxNav: {str(e)}")
        return None


async def get_drug_class(rxcui: str) -> Optional[Dict[str, Any]]:
    """
    Get therapeutic class information for a drug.
    
    Args:
        rxcui: RxCUI code
        
    Returns:
        Dictionary with drug class information
    """
    try:
        url = f"{RXNAV_BASE_URL}/rxclass/class/byRxcui.json"
        params = {"rxcui": rxcui, "relaSource": "ATC"}  # ATC = Anatomical Therapeutic Chemical
        
        logger.info(f"Getting drug class for RxCUI: {rxcui}")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract class information
            rxclass_min_concept_list = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
            
            if rxclass_min_concept_list:
                classes = []
                for concept in rxclass_min_concept_list:
                    rxclass_min_concept = concept.get("rxclassMinConceptItem", {})
                    classes.append({
                        "class_id": rxclass_min_concept.get("classId"),
                        "class_name": rxclass_min_concept.get("className"),
                        "class_type": rxclass_min_concept.get("classType")
                    })
                
                logger.info(f"Found {len(classes)} drug classes for RxCUI {rxcui}")
                return {
                    "rxcui": rxcui,
                    "classes": classes
                }
            else:
                logger.warning(f"No drug class found for RxCUI {rxcui}")
                return None
                
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting drug class: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting drug class: {str(e)}")
        return None


async def find_alternative_drugs(rxcui: str) -> List[Dict[str, str]]:
    """
    Find therapeutic alternatives for a drug.
    
    Args:
        rxcui: RxCUI code
        
    Returns:
        List of alternative drug dictionaries
    """
    try:
        url = f"{RXNAV_BASE_URL}/rxcui/{rxcui}/related.json"
        params = {"tty": "SCD+SBD"}  # Semantic Clinical Drug + Semantic Branded Drug
        
        logger.info(f"Finding alternatives for RxCUI: {rxcui}")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract related concepts
            related_group = data.get("relatedGroup", {})
            concept_groups = related_group.get("conceptGroup", [])
            
            alternatives = []
            for group in concept_groups:
                concept_properties = group.get("conceptProperties", [])
                for prop in concept_properties:
                    alternatives.append({
                        "rxcui": prop.get("rxcui"),
                        "name": prop.get("name"),
                        "synonym": prop.get("synonym", ""),
                        "tty": prop.get("tty")
                    })
            
            logger.info(f"Found {len(alternatives)} alternatives for RxCUI {rxcui}")
            return alternatives
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error finding alternatives: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error finding alternatives: {str(e)}")
        return []


async def normalize_drug_names(drug_names: List[str]) -> Dict[str, Optional[str]]:
    """
    Normalize a list of drug names to RxCUI codes.
    
    Args:
        drug_names: List of drug names
        
    Returns:
        Dictionary mapping drug names to RxCUI codes
    """
    results = {}
    
    for drug_name in drug_names:
        rxcui = await get_rxcui_by_name(drug_name)
        results[drug_name] = rxcui
    
    return results

