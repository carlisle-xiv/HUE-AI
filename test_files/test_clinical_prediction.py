"""
Comprehensive test suite for Clinical Data Prediction feature.
Tests demand forecasting, expiry risk analysis, seasonality detection,
anomaly detection, and reorder recommendations.

Usage:
    python test_clinical_prediction.py --seed    # Seed test data only
    python test_clinical_prediction.py --test    # Run tests only (assumes data exists)
    python test_clinical_prediction.py --clear   # Clear test data only
    python test_clinical_prediction.py --all     # Seed, test, then clear (default)
    python test_clinical_prediction.py           # Same as --all
"""

import argparse
import asyncio
import os
import random
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1/clinical-prediction"

# Test data identifiers
TEST_PREFIX = "TEST_CLINICAL_"
TEST_PHARMACY_LICENSE_PREFIX = "TEST-PHARM-"


# ============================================================================
# Test Data Definitions
# ============================================================================

# Ghana-specific disease season drugs
GHANA_TEST_DRUGS = [
    # Antimalarials (Malaria season: May-October)
    {
        "drug_code": f"{TEST_PREFIX}NDC-001",
        "drug_name": "Artemether-Lumefantrine",
        "generic_name": "Artemether-Lumefantrine",
        "brand_names": ["Coartem", "Riamet"],
        "dosage_form": "Tablet",
        "strength": "20mg/120mg",
        "therapeutic_class": "Antimalarial",
        "fda_approved": True,
        "prescription_required": True
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-002",
        "drug_name": "Artesunate Injection",
        "generic_name": "Artesunate",
        "brand_names": ["Artesun"],
        "dosage_form": "Injection",
        "strength": "60mg",
        "therapeutic_class": "Antimalarial",
        "fda_approved": True,
        "prescription_required": True
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-003",
        "drug_name": "Quinine Sulfate",
        "generic_name": "Quinine",
        "brand_names": ["Qualaquin"],
        "dosage_form": "Tablet",
        "strength": "300mg",
        "therapeutic_class": "Antimalarial",
        "fda_approved": True,
        "prescription_required": True
    },
    # Respiratory (Harmattan: Nov-Feb)
    {
        "drug_code": f"{TEST_PREFIX}NDC-004",
        "drug_name": "Amoxicillin",
        "generic_name": "Amoxicillin",
        "brand_names": ["Amoxil", "Moxatag"],
        "dosage_form": "Capsule",
        "strength": "500mg",
        "therapeutic_class": "Antibiotic",
        "fda_approved": True,
        "prescription_required": True
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-005",
        "drug_name": "Azithromycin",
        "generic_name": "Azithromycin",
        "brand_names": ["Zithromax", "Z-Pack"],
        "dosage_form": "Tablet",
        "strength": "250mg",
        "therapeutic_class": "Antibiotic",
        "fda_approved": True,
        "prescription_required": True
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-006",
        "drug_name": "Dextromethorphan Cough Syrup",
        "generic_name": "Dextromethorphan",
        "brand_names": ["Robitussin"],
        "dosage_form": "Syrup",
        "strength": "15mg/5ml",
        "therapeutic_class": "Cough Suppressant",
        "fda_approved": True,
        "prescription_required": False
    },
    # Diarrhea (Hot/Early Rainy: Mar-May)
    {
        "drug_code": f"{TEST_PREFIX}NDC-007",
        "drug_name": "Oral Rehydration Salts (ORS)",
        "generic_name": "ORS",
        "brand_names": ["Pedialyte"],
        "dosage_form": "Powder",
        "strength": "27.9g/L",
        "therapeutic_class": "Electrolyte Supplement",
        "fda_approved": True,
        "prescription_required": False
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-008",
        "drug_name": "Zinc Sulfate",
        "generic_name": "Zinc",
        "brand_names": ["Zincate"],
        "dosage_form": "Tablet",
        "strength": "20mg",
        "therapeutic_class": "Mineral Supplement",
        "fda_approved": True,
        "prescription_required": False
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-009",
        "drug_name": "Metronidazole",
        "generic_name": "Metronidazole",
        "brand_names": ["Flagyl"],
        "dosage_form": "Tablet",
        "strength": "400mg",
        "therapeutic_class": "Antibiotic",
        "fda_approved": True,
        "prescription_required": True
    },
    # Skin Infections (Rainy season: Jun-Sep)
    {
        "drug_code": f"{TEST_PREFIX}NDC-010",
        "drug_name": "Clotrimazole Cream",
        "generic_name": "Clotrimazole",
        "brand_names": ["Lotrimin"],
        "dosage_form": "Cream",
        "strength": "1%",
        "therapeutic_class": "Antifungal",
        "fda_approved": True,
        "prescription_required": False
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-011",
        "drug_name": "Fluconazole",
        "generic_name": "Fluconazole",
        "brand_names": ["Diflucan"],
        "dosage_form": "Capsule",
        "strength": "150mg",
        "therapeutic_class": "Antifungal",
        "fda_approved": True,
        "prescription_required": True
    },
    # Common medications
    {
        "drug_code": f"{TEST_PREFIX}NDC-012",
        "drug_name": "Paracetamol",
        "generic_name": "Acetaminophen",
        "brand_names": ["Tylenol", "Panadol"],
        "dosage_form": "Tablet",
        "strength": "500mg",
        "therapeutic_class": "Analgesic",
        "fda_approved": True,
        "prescription_required": False
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-013",
        "drug_name": "Ibuprofen",
        "generic_name": "Ibuprofen",
        "brand_names": ["Advil", "Motrin"],
        "dosage_form": "Tablet",
        "strength": "400mg",
        "therapeutic_class": "NSAID",
        "fda_approved": True,
        "prescription_required": False
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-014",
        "drug_name": "Ciprofloxacin",
        "generic_name": "Ciprofloxacin",
        "brand_names": ["Cipro"],
        "dosage_form": "Tablet",
        "strength": "500mg",
        "therapeutic_class": "Antibiotic",
        "fda_approved": True,
        "prescription_required": True
    },
    {
        "drug_code": f"{TEST_PREFIX}NDC-015",
        "drug_name": "Omeprazole",
        "generic_name": "Omeprazole",
        "brand_names": ["Prilosec"],
        "dosage_form": "Capsule",
        "strength": "20mg",
        "therapeutic_class": "Proton Pump Inhibitor",
        "fda_approved": True,
        "prescription_required": False
    }
]

GHANA_TEST_PHARMACIES = [
    {
        "name": f"{TEST_PREFIX}HealthPlus Pharmacy Accra",
        "license_number": f"{TEST_PHARMACY_LICENSE_PREFIX}ACCRA-001",
        "address": {
            "street": "123 Independence Avenue",
            "city": "Accra",
            "region": "Greater Accra",
            "country": "Ghana",
            "postal_code": "GA-123"
        },
        "phone_number": "+233201234567",
        "email": "test.accra@healthplus.gh",
        "delivery_available": True,
        "delivery_radius_km": 15.0
    },
    {
        "name": f"{TEST_PREFIX}MediCare Pharmacy Kumasi",
        "license_number": f"{TEST_PHARMACY_LICENSE_PREFIX}KUMASI-001",
        "address": {
            "street": "45 Bantama Road",
            "city": "Kumasi",
            "region": "Ashanti",
            "country": "Ghana",
            "postal_code": "KS-456"
        },
        "phone_number": "+233209876543",
        "email": "test.kumasi@medicare.gh",
        "delivery_available": True,
        "delivery_radius_km": 10.0
    },
    {
        "name": f"{TEST_PREFIX}Coast Pharmacy Cape Coast",
        "license_number": f"{TEST_PHARMACY_LICENSE_PREFIX}CAPE-001",
        "address": {
            "street": "78 Commercial Street",
            "city": "Cape Coast",
            "region": "Central",
            "country": "Ghana",
            "postal_code": "CC-789"
        },
        "phone_number": "+233205551234",
        "email": "test.capecoast@coastpharm.gh",
        "delivery_available": False,
        "delivery_radius_km": None
    }
]


# ============================================================================
# Utility Functions
# ============================================================================

def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_subheader(text: str):
    """Print formatted subheader."""
    print("\n" + "-" * 80)
    print(f"  {text}")
    print("-" * 80)


def print_test_result(test_name: str, success: bool, message: str = "", duration: float = 0):
    """Print formatted test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    duration_str = f" ({duration:.2f}s)" if duration > 0 else ""
    print(f"  {status} | {test_name}{duration_str}")
    if message:
        print(f"         └─ {message}")


# ============================================================================
# Test Data Seeder
# ============================================================================

class ClinicalPredictionTestDataSeeder:
    """Seeds test data for clinical prediction testing."""
    
    def __init__(self):
        self.pharmacy_ids: List[UUID] = []
        self.drug_ids: List[UUID] = []
        self.pharmacy_user_ids: List[UUID] = []
        
    def seed_all(self) -> Dict[str, Any]:
        """Seed all test data and return IDs."""
        from sqlmodel import Session, select
        from src.database import engine
        from src.models.core import User, Wallet
        from src.models.pharmacy import Pharmacy, PharmacyInventory, DrugOrder, DrugOrderItem
        from src.models.reference import PharmacyCode
        
        print_header("SEEDING TEST DATA FOR CLINICAL PREDICTION")
        
        with Session(engine) as session:
            try:
                # 1. Create test drugs
                print("\n📦 Creating test drugs...")
                drug_map = self._create_drugs(session)
                print(f"   ✓ Created {len(drug_map)} test drugs")
                
                # 2. Create test users and pharmacies
                print("\n🏪 Creating test pharmacies...")
                pharmacy_map = self._create_pharmacies(session)
                print(f"   ✓ Created {len(pharmacy_map)} test pharmacies")
                
                # 3. Create inventory with varying expiry dates
                print("\n📋 Creating pharmacy inventory...")
                inventory_count = self._create_inventory(session, pharmacy_map, drug_map)
                print(f"   ✓ Created {inventory_count} inventory items")
                
                # 4. Create historical order data
                print("\n📊 Creating historical order data...")
                order_count = self._create_historical_orders(session, pharmacy_map, drug_map)
                print(f"   ✓ Created {order_count} historical orders")
                
                session.commit()
                
                # Store IDs for later use
                self.drug_ids = list(drug_map.values())
                self.pharmacy_ids = list(pharmacy_map.values())
                
                print("\n" + "=" * 80)
                print("✅ TEST DATA SEEDING COMPLETE")
                print("=" * 80)
                
                return {
                    "pharmacy_ids": [str(pid) for pid in self.pharmacy_ids],
                    "drug_ids": [str(did) for did in self.drug_ids],
                    "pharmacy_map": {k: str(v) for k, v in pharmacy_map.items()},
                    "drug_map": {k: str(v) for k, v in drug_map.items()}
                }
                
            except Exception as e:
                session.rollback()
                print(f"\n❌ Error seeding data: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
    
    def _create_drugs(self, session) -> Dict[str, UUID]:
        """Create test drugs and return mapping of drug_code to ID."""
        from sqlmodel import select
        from src.models.reference import PharmacyCode
        
        drug_map = {}
        
        for drug_data in GHANA_TEST_DRUGS:
            # Check if already exists
            existing = session.exec(
                select(PharmacyCode).where(
                    PharmacyCode.drug_code == drug_data["drug_code"]
                )
            ).first()
            
            if existing:
                drug_map[drug_data["drug_code"]] = existing.id
            else:
                drug = PharmacyCode(**drug_data)
                session.add(drug)
                session.flush()
                drug_map[drug_data["drug_code"]] = drug.id
        
        return drug_map
    
    def _create_pharmacies(self, session) -> Dict[str, UUID]:
        """Create test pharmacies and return mapping of license to ID."""
        from sqlmodel import select
        from src.models.core import User, Wallet
        from src.models.pharmacy import Pharmacy
        
        pharmacy_map = {}
        
        for idx, pharm_data in enumerate(GHANA_TEST_PHARMACIES):
            # Check if already exists
            existing = session.exec(
                select(Pharmacy).where(
                    Pharmacy.license_number == pharm_data["license_number"]
                )
            ).first()
            
            if existing:
                pharmacy_map[pharm_data["license_number"]] = existing.id
                continue
            
            # Create user for pharmacy
            user = User(
                email=pharm_data["email"],
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEcRGu",
                phone_number=pharm_data["phone_number"],
                user_type="PHARMACY",
                country="GH",
                is_active=True,
                email_verified=True,
                phone_verified=True
            )
            session.add(user)
            session.flush()
            self.pharmacy_user_ids.append(user.id)
            
            # Create pharmacy
            pharmacy = Pharmacy(
                user_id=user.id,
                name=pharm_data["name"],
                license_number=pharm_data["license_number"],
                address=pharm_data["address"],
                phone_number=pharm_data["phone_number"],
                email=pharm_data["email"],
                delivery_available=pharm_data["delivery_available"],
                delivery_radius_km=Decimal(str(pharm_data["delivery_radius_km"])) if pharm_data["delivery_radius_km"] else None,
                is_active=True,
                rating_average=Decimal("4.5"),
                total_ratings=50
            )
            session.add(pharmacy)
            session.flush()
            pharmacy_map[pharm_data["license_number"]] = pharmacy.id
            
            # Create wallet
            wallet = Wallet(
                user_id=user.id,
                balance=Decimal("10000.00")
            )
            session.add(wallet)
        
        return pharmacy_map
    
    def _create_inventory(self, session, pharmacy_map: Dict[str, UUID], drug_map: Dict[str, UUID]) -> int:
        """Create pharmacy inventory with varying expiry dates."""
        from src.models.pharmacy import PharmacyInventory
        from sqlmodel import select
        
        count = 0
        today = date.today()
        
        for license_num, pharmacy_id in pharmacy_map.items():
            for drug_code, drug_id in drug_map.items():
                # Check if already exists
                existing = session.exec(
                    select(PharmacyInventory).where(
                        PharmacyInventory.pharmacy_id == pharmacy_id,
                        PharmacyInventory.pharmacy_code_id == drug_id
                    )
                ).first()
                
                if existing:
                    count += 1
                    continue
                
                # Create varied expiry dates for testing
                # Some expired, some critical, some healthy
                expiry_scenarios = [
                    today - timedelta(days=5),     # Expired
                    today + timedelta(days=7),     # Critical (1 week)
                    today + timedelta(days=21),    # High risk (3 weeks)
                    today + timedelta(days=45),    # Medium risk
                    today + timedelta(days=90),    # Low risk
                    today + timedelta(days=180),   # Healthy
                    today + timedelta(days=365),   # Very healthy
                ]
                
                # Select expiry based on drug index for variety
                drug_idx = list(drug_map.keys()).index(drug_code)
                expiry_date = expiry_scenarios[drug_idx % len(expiry_scenarios)]
                
                # Vary quantities
                quantity = random.randint(20, 200)
                unit_price = Decimal(str(random.uniform(5.0, 150.0))).quantize(Decimal("0.01"))
                
                inventory = PharmacyInventory(
                    pharmacy_id=pharmacy_id,
                    pharmacy_code_id=drug_id,
                    quantity_available=quantity,
                    unit_price=unit_price,
                    expiry_date=expiry_date,
                    batch_number=f"BATCH-{drug_code[-3:]}-{random.randint(1000, 9999)}",
                    is_insurance_covered=random.choice([True, False])
                )
                session.add(inventory)
                count += 1
        
        return count
    
    def _create_historical_orders(self, session, pharmacy_map: Dict[str, UUID], drug_map: Dict[str, UUID]) -> int:
        """Create 12 months of historical order data with seasonal patterns."""
        from src.models.pharmacy import DrugOrder, DrugOrderItem, PharmacyInventory
        from src.models.patients import Patient
        from sqlmodel import select
        
        # Get or create a test patient for orders
        test_patient = session.exec(
            select(Patient).limit(1)
        ).first()
        
        if not test_patient:
            print("   ⚠️  No patient found, skipping historical orders")
            return 0
        
        count = 0
        today = date.today()
        
        # Define seasonal demand multipliers for different drug categories
        # Based on Ghana disease seasons
        seasonal_patterns = {
            "Antimalarial": {  # Malaria: May-October peak
                1: 0.4, 2: 0.4, 3: 0.5, 4: 0.6, 5: 1.2, 6: 1.5,
                7: 1.8, 8: 1.6, 9: 1.4, 10: 1.0, 11: 0.6, 12: 0.4
            },
            "Antibiotic": {  # Respiratory: Nov-Feb peak
                1: 1.4, 2: 1.3, 3: 0.8, 4: 0.6, 5: 0.5, 6: 0.5,
                7: 0.5, 8: 0.5, 9: 0.6, 10: 0.8, 11: 1.2, 12: 1.5
            },
            "Cough Suppressant": {  # Respiratory: Nov-Feb peak
                1: 1.5, 2: 1.4, 3: 0.7, 4: 0.5, 5: 0.4, 6: 0.4,
                7: 0.4, 8: 0.5, 9: 0.6, 10: 0.9, 11: 1.3, 12: 1.6
            },
            "Electrolyte Supplement": {  # Diarrhea: Mar-May peak
                1: 0.6, 2: 0.7, 3: 1.3, 4: 1.5, 5: 1.4, 6: 0.8,
                7: 0.7, 8: 0.6, 9: 0.6, 10: 0.5, 11: 0.5, 12: 0.5
            },
            "Antifungal": {  # Skin: Jun-Sep peak (rainy)
                1: 0.5, 2: 0.5, 3: 0.6, 4: 0.7, 5: 0.8, 6: 1.3,
                7: 1.5, 8: 1.4, 9: 1.2, 10: 0.8, 11: 0.6, 12: 0.5
            },
            "default": {  # Stable demand
                1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0,
                7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.0
            }
        }
        
        # Get drug info for seasonal mapping
        from src.models.reference import PharmacyCode
        drug_classes = {}
        for drug_code, drug_id in drug_map.items():
            drug = session.exec(
                select(PharmacyCode).where(PharmacyCode.id == drug_id)
            ).first()
            if drug:
                drug_classes[drug_id] = drug.therapeutic_class
        
        # Generate orders for past 12 months
        for months_ago in range(12, 0, -1):
            order_date = today - timedelta(days=months_ago * 30)
            month = order_date.month
            
            for license_num, pharmacy_id in pharmacy_map.items():
                # Get inventory for this pharmacy
                inventory_items = session.exec(
                    select(PharmacyInventory).where(
                        PharmacyInventory.pharmacy_id == pharmacy_id
                    )
                ).all()
                
                for inv_item in inventory_items:
                    # Determine seasonal multiplier
                    drug_class = drug_classes.get(inv_item.pharmacy_code_id, "default")
                    pattern = seasonal_patterns.get(drug_class, seasonal_patterns["default"])
                    multiplier = pattern.get(month, 1.0)
                    
                    # Base order frequency varies by drug
                    base_orders = random.randint(2, 8)
                    num_orders = max(1, int(base_orders * multiplier))
                    
                    # Add some randomness for anomaly detection testing
                    # Occasionally add spikes or drops
                    if random.random() < 0.05:  # 5% chance of anomaly
                        if random.random() < 0.5:
                            num_orders = num_orders * 3  # Spike
                        else:
                            num_orders = max(1, num_orders // 3)  # Drop
                    
                    # Create orders spread across the month
                    for order_idx in range(num_orders):
                        order_day = order_date + timedelta(days=random.randint(0, 28))
                        
                        # Create order
                        order = DrugOrder(
                            patient_id=test_patient.id,
                            pharmacy_id=pharmacy_id,
                            order_number=f"TEST-ORD-{uuid4().hex[:8].upper()}",
                            order_type="PRESCRIPTION",
                            total_amount=inv_item.unit_price * random.randint(1, 5),
                            insurance_covered_amount=Decimal("0"),
                            patient_pay_amount=inv_item.unit_price * random.randint(1, 5),
                            status="COMPLETED",
                            delivery_method="PICKUP",
                            created_at=datetime.combine(order_day, datetime.min.time())
                        )
                        session.add(order)
                        session.flush()
                        
                        # Create order item
                        qty = random.randint(1, 5)
                        order_item = DrugOrderItem(
                            drug_order_id=order.id,
                            pharmacy_inventory_id=inv_item.id,
                            quantity_ordered=qty,
                            unit_price=inv_item.unit_price,
                            total_price=inv_item.unit_price * qty,
                            created_at=datetime.combine(order_day, datetime.min.time())
                        )
                        session.add(order_item)
                        count += 1
        
        return count
    
    def clear_test_data(self):
        """Remove all test data."""
        from sqlmodel import Session, select, delete
        from src.database import engine
        from src.models.core import User, Wallet
        from src.models.pharmacy import Pharmacy, PharmacyInventory, DrugOrder, DrugOrderItem
        from src.models.reference import PharmacyCode
        from src.clinical_data_prediction.demand_forecasting.models import (
            DemandForecast, DemandAnomaly, SeasonalityPattern
        )
        
        print_header("CLEARING TEST DATA")
        
        with Session(engine) as session:
            try:
                # Use no_autoflush to prevent premature constraint checks
                with session.no_autoflush:
                    # 1. Find test pharmacies and drugs first
                    test_pharmacies = session.exec(
                        select(Pharmacy).where(
                            Pharmacy.license_number.like(f"{TEST_PHARMACY_LICENSE_PREFIX}%")
                        )
                    ).all()
                    
                    test_drugs = session.exec(
                        select(PharmacyCode).where(
                            PharmacyCode.drug_code.like(f"{TEST_PREFIX}%")
                        )
                    ).all()
                    
                    pharmacy_ids = [p.id for p in test_pharmacies]
                    drug_ids = [d.id for d in test_drugs]
                    user_ids = [pharmacy.user_id for pharmacy in test_pharmacies]
                    
                    # 2. Delete clinical prediction records (created by API during testing)
                    print("\n🗑️  Deleting clinical prediction records...")
                    
                    # Delete seasonality patterns for test drugs
                    pattern_count = 0
                    for drug_id in drug_ids:
                        patterns = session.exec(
                            select(SeasonalityPattern).where(
                                SeasonalityPattern.drug_id == drug_id
                            )
                        ).all()
                        for pattern in patterns:
                            session.delete(pattern)
                            pattern_count += 1
                    
                    # Delete demand forecasts for test pharmacies/drugs
                    forecast_count = 0
                    for pharmacy_id in pharmacy_ids:
                        forecasts = session.exec(
                            select(DemandForecast).where(
                                DemandForecast.pharmacy_id == pharmacy_id
                            )
                        ).all()
                        for forecast in forecasts:
                            session.delete(forecast)
                            forecast_count += 1
                    
                    for drug_id in drug_ids:
                        forecasts = session.exec(
                            select(DemandForecast).where(
                                DemandForecast.drug_id == drug_id
                            )
                        ).all()
                        for forecast in forecasts:
                            session.delete(forecast)
                            forecast_count += 1
                    
                    # Delete demand anomalies for test pharmacies/drugs
                    anomaly_count = 0
                    for pharmacy_id in pharmacy_ids:
                        anomalies = session.exec(
                            select(DemandAnomaly).where(
                                DemandAnomaly.pharmacy_id == pharmacy_id
                            )
                        ).all()
                        for anomaly in anomalies:
                            session.delete(anomaly)
                            anomaly_count += 1
                    
                    for drug_id in drug_ids:
                        anomalies = session.exec(
                            select(DemandAnomaly).where(
                                DemandAnomaly.drug_id == drug_id
                            )
                        ).all()
                        for anomaly in anomalies:
                            session.delete(anomaly)
                            anomaly_count += 1
                    
                    print(f"   ✓ Deleted {pattern_count} seasonality patterns")
                    print(f"   ✓ Deleted {forecast_count} demand forecasts")
                    print(f"   ✓ Deleted {anomaly_count} demand anomalies")
                    
                    # 3. Delete test orders and items
                    print("\n🗑️  Deleting test orders...")
                    order_count = 0
                    for pharmacy in test_pharmacies:
                        orders = session.exec(
                            select(DrugOrder).where(DrugOrder.pharmacy_id == pharmacy.id)
                        ).all()
                        for order in orders:
                            # Delete order items first
                            items = session.exec(
                                select(DrugOrderItem).where(DrugOrderItem.drug_order_id == order.id)
                            ).all()
                            for item in items:
                                session.delete(item)
                            session.delete(order)
                            order_count += 1
                    print(f"   ✓ Deleted {order_count} test orders")
                    
                    # 4. Delete test inventory
                    print("\n🗑️  Deleting test inventory...")
                    inv_count = 0
                    for pharmacy in test_pharmacies:
                        inventory = session.exec(
                            select(PharmacyInventory).where(
                                PharmacyInventory.pharmacy_id == pharmacy.id
                            )
                        ).all()
                        for inv in inventory:
                            session.delete(inv)
                            inv_count += 1
                    print(f"   ✓ Deleted {inv_count} inventory items")
                    
                    # 5. Delete test pharmacies
                    print("\n🗑️  Deleting test pharmacies...")
                    for pharmacy in test_pharmacies:
                        session.delete(pharmacy)
                    print(f"   ✓ Deleted {len(test_pharmacies)} test pharmacies")
                    
                    # Flush to commit pharmacy deletions before user deletions
                    session.flush()
                    
                    # 6. Delete wallets and users
                    print("\n🗑️  Deleting test users and wallets...")
                    user_count = 0
                    for user_id in user_ids:
                        if user_id:
                            # Delete wallet first
                            wallet = session.exec(
                                select(Wallet).where(Wallet.user_id == user_id)
                            ).first()
                            if wallet:
                                session.delete(wallet)
                            
                            # Then delete user
                            user = session.exec(
                                select(User).where(User.id == user_id)
                            ).first()
                            if user:
                                session.delete(user)
                                user_count += 1
                    print(f"   ✓ Deleted {user_count} test users")
                    
                    # 7. Delete test drugs
                    print("\n🗑️  Deleting test drugs...")
                    for drug in test_drugs:
                        session.delete(drug)
                    print(f"   ✓ Deleted {len(test_drugs)} test drugs")
                
                session.commit()
                
                print("\n" + "=" * 80)
                print("✅ TEST DATA CLEARED")
                print("=" * 80)
                
            except Exception as e:
                session.rollback()
                print(f"\n❌ Error clearing data: {str(e)}")
                import traceback
                traceback.print_exc()
                raise


# ============================================================================
# Test Scenarios
# ============================================================================

TEST_SCENARIOS = {
    "health_check": {
        "name": "Health Check",
        "endpoint": "/health",
        "method": "GET",
        "params": {}
    },
    "demand_forecast_per_drug_pharmacy_7d": {
        "name": "Demand Forecast - Per Drug Pharmacy (7 days)",
        "endpoint": "/forecast/demand",
        "method": "POST",
        "params": {
            "granularity": "per_drug_pharmacy",
            "horizon_days": 7,
            "include_confidence_intervals": True
        }
    },
    "demand_forecast_per_drug_pharmacy_30d": {
        "name": "Demand Forecast - Per Drug Pharmacy (30 days)",
        "endpoint": "/forecast/demand",
        "method": "POST",
        "params": {
            "granularity": "per_drug_pharmacy",
            "horizon_days": 30,
            "include_confidence_intervals": True
        }
    },
    "demand_forecast_per_drug_pharmacy_90d": {
        "name": "Demand Forecast - Per Drug Pharmacy (90 days)",
        "endpoint": "/forecast/demand",
        "method": "POST",
        "params": {
            "granularity": "per_drug_pharmacy",
            "horizon_days": 90,
            "include_confidence_intervals": True
        }
    },
    "demand_forecast_per_pharmacy": {
        "name": "Demand Forecast - Per Pharmacy",
        "endpoint": "/forecast/demand",
        "method": "POST",
        "params": {
            "granularity": "per_pharmacy",
            "horizon_days": 30,
            "include_confidence_intervals": True
        }
    },
    "demand_forecast_per_drug": {
        "name": "Demand Forecast - Per Drug",
        "endpoint": "/forecast/demand",
        "method": "POST",
        "params": {
            "granularity": "per_drug",
            "horizon_days": 30,
            "include_confidence_intervals": True
        }
    },
    "demand_forecast_aggregate": {
        "name": "Demand Forecast - Aggregate",
        "endpoint": "/forecast/demand",
        "method": "POST",
        "params": {
            "granularity": "aggregate",
            "horizon_days": 30,
            "include_confidence_intervals": True
        }
    },
    "pharmacy_forecast": {
        "name": "Get Pharmacy Forecast",
        "endpoint": "/forecast/pharmacy/{pharmacy_id}",
        "method": "GET",
        "params": {
            "horizon_days": 30
        }
    },
    "drug_forecast": {
        "name": "Get Drug Forecast",
        "endpoint": "/forecast/drug/{drug_id}",
        "method": "GET",
        "params": {
            "horizon_days": 30
        }
    },
    "expiry_risk_all": {
        "name": "Expiry Risk - All Levels",
        "endpoint": "/analytics/expiry-risk",
        "method": "POST",
        "params": {
            "days_ahead": 90,
            "min_risk_level": "low"
        }
    },
    "expiry_risk_high": {
        "name": "Expiry Risk - High/Critical Only",
        "endpoint": "/analytics/expiry-risk",
        "method": "POST",
        "params": {
            "days_ahead": 90,
            "min_risk_level": "high"
        }
    },
    "expiry_risk_pharmacy": {
        "name": "Expiry Risk - Per Pharmacy",
        "endpoint": "/analytics/expiry-risk",
        "method": "POST",
        "params": {
            "days_ahead": 90,
            "min_risk_level": "medium"
        }
    },
    "seasonality_antimalarial": {
        "name": "Seasonality - Antimalarial Drug",
        "endpoint": "/analytics/seasonality/{drug_id}",
        "method": "GET",
        "params": {
            "analysis_days": 365
        }
    },
    "seasonality_respiratory": {
        "name": "Seasonality - Respiratory Drug",
        "endpoint": "/analytics/seasonality/{drug_id}",
        "method": "GET",
        "params": {
            "analysis_days": 365
        }
    },
    "anomalies_platform": {
        "name": "Anomaly Detection - Platform Wide",
        "endpoint": "/analytics/anomalies",
        "method": "GET",
        "params": {
            "days_back": 30
        }
    },
    "anomalies_pharmacy": {
        "name": "Anomaly Detection - Per Pharmacy",
        "endpoint": "/analytics/anomalies",
        "method": "GET",
        "params": {
            "days_back": 30
        }
    },
    "anomalies_drug": {
        "name": "Anomaly Detection - Per Drug",
        "endpoint": "/analytics/anomalies",
        "method": "GET",
        "params": {
            "days_back": 30
        }
    },
    "reorder_standard": {
        "name": "Reorder Recommendations - Standard",
        "endpoint": "/forecast/reorder-recommendations",
        "method": "POST",
        "params": {
            "forecast_horizon": 30,
            "safety_stock_days": 7,
            "lead_time_days": 3
        }
    },
    "reorder_conservative": {
        "name": "Reorder Recommendations - Conservative",
        "endpoint": "/forecast/reorder-recommendations",
        "method": "POST",
        "params": {
            "forecast_horizon": 30,
            "safety_stock_days": 14,
            "lead_time_days": 7
        }
    },
    "reorder_aggressive": {
        "name": "Reorder Recommendations - Aggressive",
        "endpoint": "/forecast/reorder-recommendations",
        "method": "POST",
        "params": {
            "forecast_horizon": 30,
            "safety_stock_days": 3,
            "lead_time_days": 2
        }
    },
    "invalid_missing_ids": {
        "name": "Invalid Request - Missing Required IDs",
        "endpoint": "/forecast/demand",
        "method": "POST",
        "params": {
            "granularity": "per_drug_pharmacy",
            "horizon_days": 30
        },
        "expect_error": True
    },
    "edge_nonexistent_pharmacy": {
        "name": "Edge Case - Non-existent Pharmacy",
        "endpoint": "/forecast/pharmacy/{pharmacy_id}",
        "method": "GET",
        "params": {},
        "use_fake_id": True,
        "expect_error": True
    },
    "edge_nonexistent_drug": {
        "name": "Edge Case - Non-existent Drug",
        "endpoint": "/forecast/drug/{drug_id}",
        "method": "GET",
        "params": {},
        "use_fake_id": True,
        "expect_error": True
    }
}


# ============================================================================
# Test Runner
# ============================================================================

class ClinicalPredictionTester:
    """Runs tests against the clinical prediction API."""
    
    def __init__(self, test_data: Dict[str, Any]):
        self.test_data = test_data
        self.results: List[Dict[str, Any]] = []
        self.pharmacy_ids = test_data.get("pharmacy_ids", [])
        self.drug_ids = test_data.get("drug_ids", [])
        
    async def run_all_tests(self):
        """Run all test scenarios."""
        print_header("RUNNING CLINICAL PREDICTION TESTS")
        print(f"\nBase URL: {BASE_URL}")
        print(f"Test Pharmacies: {len(self.pharmacy_ids)}")
        print(f"Test Drugs: {len(self.drug_ids)}")
        print(f"Total Scenarios: {len(TEST_SCENARIOS)}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Health check first
            print_subheader("Phase 1: Health Check")
            await self._run_test(client, "health_check")
            
            # Demand forecasting tests
            print_subheader("Phase 2: Demand Forecasting Tests")
            await self._run_test(client, "demand_forecast_per_drug_pharmacy_7d")
            await self._run_test(client, "demand_forecast_per_drug_pharmacy_30d")
            await self._run_test(client, "demand_forecast_per_drug_pharmacy_90d")
            await self._run_test(client, "demand_forecast_per_pharmacy")
            await self._run_test(client, "demand_forecast_per_drug")
            await self._run_test(client, "demand_forecast_aggregate")
            
            # Pharmacy and drug forecast GET endpoints
            print_subheader("Phase 3: Pharmacy & Drug Forecast Endpoints")
            await self._run_test(client, "pharmacy_forecast")
            await self._run_test(client, "drug_forecast")
            
            # Analytics tests
            print_subheader("Phase 4: Analytics Tests")
            await self._run_test(client, "expiry_risk_all")
            await self._run_test(client, "expiry_risk_high")
            await self._run_test(client, "expiry_risk_pharmacy")
            await self._run_test(client, "seasonality_antimalarial")
            await self._run_test(client, "seasonality_respiratory")
            await self._run_test(client, "anomalies_platform")
            await self._run_test(client, "anomalies_pharmacy")
            await self._run_test(client, "anomalies_drug")
            
            # Reorder recommendations
            print_subheader("Phase 5: Reorder Recommendations Tests")
            await self._run_test(client, "reorder_standard")
            await self._run_test(client, "reorder_conservative")
            await self._run_test(client, "reorder_aggressive")
            
            # Edge cases and error handling
            print_subheader("Phase 6: Edge Cases & Error Handling")
            await self._run_test(client, "invalid_missing_ids")
            await self._run_test(client, "edge_nonexistent_pharmacy")
            await self._run_test(client, "edge_nonexistent_drug")
        
        # Generate summary
        self._print_summary()
    
    async def _run_test(self, client: httpx.AsyncClient, test_key: str):
        """Run a single test scenario."""
        scenario = TEST_SCENARIOS[test_key]
        start_time = datetime.now()
        
        try:
            # Build endpoint URL
            endpoint = scenario["endpoint"]
            
            # Replace path parameters
            if "{pharmacy_id}" in endpoint:
                if scenario.get("use_fake_id"):
                    endpoint = endpoint.replace("{pharmacy_id}", str(uuid4()))
                elif self.pharmacy_ids:
                    endpoint = endpoint.replace("{pharmacy_id}", self.pharmacy_ids[0])
                else:
                    print_test_result(scenario["name"], False, "No pharmacy IDs available")
                    return
            
            if "{drug_id}" in endpoint:
                if scenario.get("use_fake_id"):
                    endpoint = endpoint.replace("{drug_id}", str(uuid4()))
                elif self.drug_ids:
                    # Use appropriate drug for seasonality tests
                    if "antimalarial" in test_key:
                        # Find antimalarial drug (first 3 in our list)
                        drug_id = self.drug_ids[0] if self.drug_ids else str(uuid4())
                    elif "respiratory" in test_key:
                        # Find respiratory drug (index 3-5 in our list)
                        drug_id = self.drug_ids[3] if len(self.drug_ids) > 3 else self.drug_ids[0]
                    else:
                        drug_id = self.drug_ids[0]
                    endpoint = endpoint.replace("{drug_id}", drug_id)
                else:
                    print_test_result(scenario["name"], False, "No drug IDs available")
                    return
            
            url = f"{BASE_URL}{API_PREFIX}{endpoint}"
            
            # Build request params
            params = scenario["params"].copy()
            
            # Skip auto-adding IDs for tests that expect errors (testing validation)
            if not scenario.get("expect_error"):
                # Add IDs for POST requests that need them
                if scenario["method"] == "POST":
                    if "per_drug_pharmacy" in params.get("granularity", ""):
                        if self.pharmacy_ids and self.drug_ids:
                            params["pharmacy_id"] = self.pharmacy_ids[0]
                            params["drug_id"] = self.drug_ids[0]
                    elif "per_pharmacy" in params.get("granularity", ""):
                        if self.pharmacy_ids:
                            params["pharmacy_id"] = self.pharmacy_ids[0]
                    elif "per_drug" in params.get("granularity", ""):
                        if self.drug_ids:
                            params["drug_id"] = self.drug_ids[0]
                    
                    # Reorder recommendations need pharmacy_id
                    if "reorder" in test_key:
                        if self.pharmacy_ids:
                            params["pharmacy_id"] = self.pharmacy_ids[0]
                    
                    # Expiry risk pharmacy filter
                    if test_key == "expiry_risk_pharmacy" and self.pharmacy_ids:
                        params["pharmacy_id"] = self.pharmacy_ids[0]
            
            # Handle GET request query params
            if scenario["method"] == "GET" and "anomalies" in test_key:
                if "pharmacy" in test_key and self.pharmacy_ids:
                    params["pharmacy_id"] = self.pharmacy_ids[0]
                elif "drug" in test_key and self.drug_ids:
                    params["drug_id"] = self.drug_ids[0]
            
            # Make request
            if scenario["method"] == "POST":
                response = await client.post(url, json=params)
            else:
                response = await client.get(url, params=params)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Evaluate result
            expect_error = scenario.get("expect_error", False)
            
            if expect_error:
                success = response.status_code in [400, 404, 422]
                message = f"Status: {response.status_code} (expected error)"
            else:
                success = response.status_code == 200
                if success:
                    data = response.json()
                    message = self._summarize_response(test_key, data)
                else:
                    message = f"Status: {response.status_code} - {response.text[:100]}"
            
            print_test_result(scenario["name"], success, message, duration)
            
            self.results.append({
                "test": test_key,
                "name": scenario["name"],
                "success": success,
                "duration": duration,
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None
            })
            
        except httpx.ConnectError:
            print_test_result(scenario["name"], False, "Connection refused - is the server running?")
            self.results.append({
                "test": test_key,
                "name": scenario["name"],
                "success": False,
                "error": "Connection refused"
            })
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print_test_result(scenario["name"], False, f"Error: {str(e)}", duration)
            self.results.append({
                "test": test_key,
                "name": scenario["name"],
                "success": False,
                "error": str(e),
                "duration": duration
            })
    
    def _summarize_response(self, test_key: str, data: Dict[str, Any]) -> str:
        """Generate a summary message from response data."""
        if "health" in test_key:
            return f"Status: {data.get('status', 'unknown')}, Features: {len(data.get('features', []))}"
        
        if "forecast" in test_key and "demand" in test_key:
            points = data.get("data_points_used", 0)
            processing = data.get("processing_time_seconds", 0)
            return f"Data points: {points}, Processing: {processing:.2f}s"
        
        if "pharmacy_forecast" in test_key or "drug_forecast" in test_key:
            points = data.get("data_points_used", 0)
            if data.get("pharmacy_forecasts"):
                num_drugs = sum(len(pf.get("drug_forecasts", [])) for pf in data.get("pharmacy_forecasts", []))
                return f"Drugs forecast: {num_drugs}, Data points: {points}"
            elif data.get("drug_forecasts"):
                return f"Drug forecasts: {len(data.get('drug_forecasts', []))}"
            return f"Data points: {points}"
        
        if "expiry" in test_key:
            total = data.get("total_items_at_risk", 0)
            loss = data.get("total_potential_loss", 0)
            return f"Items at risk: {total}, Potential loss: ${float(loss):,.2f}"
        
        if "seasonality" in test_key:
            patterns = len(data.get("patterns_detected", []))
            has_strong = data.get("has_strong_seasonality", False)
            return f"Patterns: {patterns}, Strong seasonality: {'Yes' if has_strong else 'No'}"
        
        if "anomal" in test_key:
            total = data.get("total_anomalies_detected", 0)
            summary = data.get("summary_by_type", {})
            spikes = summary.get("spike", 0)
            drops = summary.get("drop", 0)
            return f"Anomalies: {total} (Spikes: {spikes}, Drops: {drops})"
        
        if "reorder" in test_key:
            immediate = len(data.get("immediate_reorders", []))
            upcoming = len(data.get("upcoming_reorders", []))
            total_value = data.get("total_reorder_value", 0)
            return f"Immediate: {immediate}, Upcoming: {upcoming}, Value: ${float(total_value):,.2f}"
        
        return "OK"
    
    def _print_summary(self):
        """Print test summary."""
        print_header("TEST SUMMARY")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("success", False))
        failed = total - passed
        
        print(f"\n  Total Tests: {total}")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  Success Rate: {(passed/total)*100:.1f}%")
        
        # Performance metrics
        durations = [r.get("duration", 0) for r in self.results if r.get("duration")]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            print(f"\n  Performance Metrics:")
            print(f"    Average Response Time: {avg_duration:.2f}s")
            print(f"    Fastest: {min_duration:.2f}s")
            print(f"    Slowest: {max_duration:.2f}s")
        
        # Failed tests
        if failed > 0:
            print(f"\n  Failed Tests:")
            for r in self.results:
                if not r.get("success", False):
                    error = r.get("error", "Unknown error")
                    print(f"    - {r.get('name', r.get('test'))}: {error}")
        
        # Data quality insights
        print_subheader("Data Quality Insights")
        
        # Analyze forecast results
        forecast_results = [r for r in self.results if "forecast" in r.get("test", "") and r.get("response")]
        if forecast_results:
            total_data_points = sum(r.get("response", {}).get("data_points_used", 0) for r in forecast_results)
            print(f"  Total historical data points used: {total_data_points:,}")
        
        # Analyze expiry results
        expiry_results = [r for r in self.results if "expiry" in r.get("test", "") and r.get("response")]
        if expiry_results:
            for r in expiry_results:
                resp = r.get("response", {})
                summary = resp.get("summary_by_risk_level", {})
                print(f"  Expiry Risk ({r.get('name')}):")
                for level, count in summary.items():
                    print(f"    - {level}: {count} items")
        
        # Analyze anomaly results
        anomaly_results = [r for r in self.results if "anomal" in r.get("test", "") and r.get("response")]
        if anomaly_results:
            total_anomalies = sum(r.get("response", {}).get("total_anomalies_detected", 0) for r in anomaly_results)
            print(f"  Total anomalies detected: {total_anomalies}")
        
        print(f"\n  End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Save detailed report to file
        self._save_report()
    
    def _save_report(self):
        """Save detailed test report to a file."""
        report_file = "test_files/clinical_prediction_test_report.txt"
        
        with open(report_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("  CLINICAL DATA PREDICTION - COMPREHENSIVE TEST REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Base URL: {BASE_URL}\n")
            f.write(f"Test Pharmacies: {len(self.pharmacy_ids)}\n")
            f.write(f"Test Drugs: {len(self.drug_ids)}\n\n")
            
            # Summary
            total = len(self.results)
            passed = sum(1 for r in self.results if r.get("success", False))
            failed = total - passed
            
            f.write("-" * 80 + "\n")
            f.write("  SUMMARY\n")
            f.write("-" * 80 + "\n\n")
            f.write(f"  Total Tests: {total}\n")
            f.write(f"  Passed: {passed}\n")
            f.write(f"  Failed: {failed}\n")
            f.write(f"  Success Rate: {(passed/total)*100:.1f}%\n\n")
            
            # Performance
            durations = [r.get("duration", 0) for r in self.results if r.get("duration")]
            if durations:
                f.write(f"  Performance:\n")
                f.write(f"    Average Response Time: {sum(durations)/len(durations):.2f}s\n")
                f.write(f"    Fastest: {min(durations):.2f}s\n")
                f.write(f"    Slowest: {max(durations):.2f}s\n\n")
            
            # Detailed test results
            f.write("-" * 80 + "\n")
            f.write("  DETAILED TEST RESULTS\n")
            f.write("-" * 80 + "\n\n")
            
            for result in self.results:
                status = "PASS" if result.get("success") else "FAIL"
                duration = result.get("duration", 0)
                f.write(f"[{status}] {result.get('name', result.get('test'))}\n")
                f.write(f"       Duration: {duration:.2f}s\n")
                
                if result.get("error"):
                    f.write(f"       Error: {result.get('error')}\n")
                
                # Write response details for successful tests
                response = result.get("response")
                if response:
                    test_key = result.get("test", "")
                    
                    if "expiry" in test_key:
                        f.write(f"       Items at Risk: {response.get('total_items_at_risk', 0)}\n")
                        f.write(f"       Potential Loss: ${float(response.get('total_potential_loss', 0)):,.2f}\n")
                        summary = response.get("summary_by_risk_level", {})
                        f.write(f"       By Risk Level:\n")
                        for level, count in summary.items():
                            f.write(f"         - {level}: {count}\n")
                        
                        # List individual risk items
                        risk_items = response.get("risk_items", [])
                        if risk_items:
                            f.write(f"       Top Risk Items:\n")
                            for item in risk_items[:5]:  # Top 5
                                f.write(f"         - {item.get('drug_name')} at {item.get('pharmacy_name')}\n")
                                f.write(f"           Qty: {item.get('current_quantity')}, Expires: {item.get('expiry_date')}\n")
                                f.write(f"           Risk: {item.get('risk_level')}, Loss: ${float(item.get('potential_loss_value', 0)):,.2f}\n")
                                f.write(f"           Action: {item.get('recommended_action', 'N/A')[:80]}...\n")
                    
                    elif "seasonality" in test_key:
                        f.write(f"       Drug: {response.get('drug_name', 'N/A')}\n")
                        f.write(f"       Strong Seasonality: {'Yes' if response.get('has_strong_seasonality') else 'No'}\n")
                        patterns = response.get("patterns_detected", [])
                        f.write(f"       Patterns Detected: {len(patterns)}\n")
                        for pattern in patterns:
                            f.write(f"         - Type: {pattern.get('pattern_type')}\n")
                            f.write(f"           Strength: {pattern.get('strength'):.2%}\n")
                            f.write(f"           Peak: {', '.join(pattern.get('peak_periods', [])[:3])}\n")
                            f.write(f"           Description: {pattern.get('description', 'N/A')[:60]}...\n")
                        recommendations = response.get("recommendations", [])
                        if recommendations:
                            f.write(f"       Recommendations:\n")
                            for rec in recommendations[:3]:
                                f.write(f"         - {rec[:70]}...\n")
                    
                    elif "anomal" in test_key:
                        f.write(f"       Total Anomalies: {response.get('total_anomalies_detected', 0)}\n")
                        summary = response.get("summary_by_type", {})
                        f.write(f"       By Type: Spikes={summary.get('spike', 0)}, Drops={summary.get('drop', 0)}\n")
                        anomalies = response.get("anomalies", [])
                        if anomalies:
                            f.write(f"       Recent Anomalies:\n")
                            for anomaly in anomalies[:5]:
                                f.write(f"         - {anomaly.get('drug_name', 'Unknown')} on {anomaly.get('anomaly_date')}\n")
                                f.write(f"           Type: {anomaly.get('anomaly_type')}, Severity: {anomaly.get('severity')}\n")
                                f.write(f"           Expected: {anomaly.get('expected_demand'):.1f}, Actual: {anomaly.get('actual_demand'):.1f}\n")
                                f.write(f"           Deviation: {anomaly.get('deviation_percentage'):.1f}%\n")
                    
                    elif "reorder" in test_key:
                        f.write(f"       Pharmacy: {response.get('pharmacy_name', 'N/A')}\n")
                        immediate = response.get("immediate_reorders", [])
                        upcoming = response.get("upcoming_reorders", [])
                        f.write(f"       Immediate Reorders: {len(immediate)}\n")
                        f.write(f"       Upcoming Reorders: {len(upcoming)}\n")
                        f.write(f"       Total Value: ${float(response.get('total_reorder_value', 0)):,.2f}\n")
                        f.write(f"       Summary: {response.get('summary', 'N/A')}\n")
                        if immediate:
                            f.write(f"       Immediate Items:\n")
                            for item in immediate[:5]:
                                f.write(f"         - {item.get('drug_name')}: Order {item.get('reorder_quantity')} units\n")
                                f.write(f"           Current: {item.get('current_stock')}, Predicted Demand: {item.get('predicted_demand'):.0f}\n")
                    
                    elif "forecast" in test_key:
                        f.write(f"       Data Points Used: {response.get('data_points_used', 0)}\n")
                        f.write(f"       Processing Time: {response.get('processing_time_seconds', 0):.2f}s\n")
                        f.write(f"       Forecast Period: {response.get('forecast_start_date')} to {response.get('forecast_end_date')}\n")
                        
                        # Show drug forecasts if available
                        drug_forecasts = response.get("drug_forecasts") or []
                        if not drug_forecasts and response.get("pharmacy_forecasts"):
                            drug_forecasts = []
                            for pf in (response.get("pharmacy_forecasts") or []):
                                drug_forecasts.extend(pf.get("drug_forecasts") or [])
                        
                        if drug_forecasts:
                            f.write(f"       Drug Forecasts ({len(drug_forecasts)}):\n")
                            for df in drug_forecasts[:5]:
                                f.write(f"         - {df.get('drug_name')}\n")
                                f.write(f"           Total Demand: {df.get('total_predicted_demand'):.0f}\n")
                                f.write(f"           Daily Avg: {df.get('average_daily_demand'):.1f}\n")
                                f.write(f"           Trend: {df.get('trend_direction')}\n")
                                f.write(f"           Confidence: {df.get('confidence_score'):.2%}\n")
                
                f.write("\n")
            
            # Data quality insights
            f.write("-" * 80 + "\n")
            f.write("  DATA QUALITY INSIGHTS\n")
            f.write("-" * 80 + "\n\n")
            
            forecast_results = [r for r in self.results if "forecast" in r.get("test", "") and r.get("response")]
            if forecast_results:
                total_data_points = sum(r.get("response", {}).get("data_points_used", 0) for r in forecast_results)
                f.write(f"  Total Historical Data Points: {total_data_points:,}\n\n")
            
            expiry_results = [r for r in self.results if "expiry" in r.get("test", "") and r.get("response")]
            if expiry_results:
                for r in expiry_results:
                    resp = r.get("response", {})
                    f.write(f"  {r.get('name')}:\n")
                    f.write(f"    Items at Risk: {resp.get('total_items_at_risk', 0)}\n")
                    f.write(f"    Potential Loss: ${float(resp.get('total_potential_loss', 0)):,.2f}\n")
                    summary = resp.get("summary_by_risk_level", {})
                    for level, count in summary.items():
                        f.write(f"    - {level}: {count} items\n")
                    f.write("\n")
            
            anomaly_results = [r for r in self.results if "anomal" in r.get("test", "") and r.get("response")]
            if anomaly_results:
                total_anomalies = sum(r.get("response", {}).get("total_anomalies_detected", 0) for r in anomaly_results)
                f.write(f"  Total Anomalies Detected: {total_anomalies}\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("  END OF REPORT\n")
            f.write("=" * 80 + "\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")


# ============================================================================
# Main Entry Point
# ============================================================================

def load_test_ids() -> Dict[str, Any]:
    """Load test IDs from database."""
    from sqlmodel import Session, select
    from src.database import engine
    from src.models.pharmacy import Pharmacy
    from src.models.reference import PharmacyCode
    
    with Session(engine) as session:
        # Get test pharmacies
        pharmacies = session.exec(
            select(Pharmacy).where(
                Pharmacy.license_number.like(f"{TEST_PHARMACY_LICENSE_PREFIX}%")
            )
        ).all()
        
        # Get test drugs
        drugs = session.exec(
            select(PharmacyCode).where(
                PharmacyCode.drug_code.like(f"{TEST_PREFIX}%")
            )
        ).all()
        
        return {
            "pharmacy_ids": [str(p.id) for p in pharmacies],
            "drug_ids": [str(d.id) for d in drugs]
        }


async def run_tests_only():
    """Run tests assuming data already exists."""
    test_data = load_test_ids()
    
    if not test_data.get("pharmacy_ids") or not test_data.get("drug_ids"):
        print("❌ Error: No test data found. Run with --seed first.")
        return False
    
    tester = ClinicalPredictionTester(test_data)
    await tester.run_all_tests()
    
    # Return success/failure
    passed = sum(1 for r in tester.results if r.get("success", False))
    return passed == len(tester.results)


async def run_full_test():
    """Seed data, run tests, then clear data."""
    seeder = ClinicalPredictionTestDataSeeder()
    
    try:
        # Seed data
        test_data = seeder.seed_all()
        
        # Run tests
        tester = ClinicalPredictionTester(test_data)
        await tester.run_all_tests()
        
        # Return success/failure
        passed = sum(1 for r in tester.results if r.get("success", False))
        return passed == len(tester.results)
        
    finally:
        # Clear data
        seeder.clear_test_data()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test suite for Clinical Data Prediction feature"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed test data only"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run tests only (assumes data exists)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear test data only"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Seed, test, then clear (default)"
    )
    
    args = parser.parse_args()
    
    # Default to --all if no arguments
    if not any([args.seed, args.test, args.clear, args.all]):
        args.all = True
    
    print("\n🧪 Clinical Data Prediction Test Suite")
    print("=" * 80)
    
    try:
        if args.clear:
            seeder = ClinicalPredictionTestDataSeeder()
            seeder.clear_test_data()
        elif args.seed:
            seeder = ClinicalPredictionTestDataSeeder()
            seeder.seed_all()
        elif args.test:
            success = asyncio.run(run_tests_only())
            sys.exit(0 if success else 1)
        elif args.all:
            success = asyncio.run(run_full_test())
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

