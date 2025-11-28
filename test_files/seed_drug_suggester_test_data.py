"""
Seed test data for Drug Suggester feature testing.

Creates:
1. New test patient with medical history
2. Current medications (active prescriptions)
3. Pharmacy inventory with common drugs
4. Test allergies
"""

import asyncio
from datetime import datetime, date, timedelta
from uuid import uuid4, UUID
from decimal import Decimal
import hashlib

from sqlmodel import Session, select
from src.database import engine
from src.models.core import User
from src.models.patients import Patient, PatientCondition, PatientVital
from src.models.doctors import Doctor
from src.models.prescriptions import Prescription, PrescriptionItem
from src.models.pharmacy import Pharmacy, PharmacyInventory
from src.models.reference import PharmacyCode, MedicalCode
from src.models.drug_suggester import PatientAllergy


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_step(text: str):
    """Print step"""
    print(f"\n✓ {text}")


def get_or_create_user(session: Session, email: str, user_type: str) -> User:
    """Get or create a user"""
    stmt = select(User).where(User.email == email)
    user = session.exec(stmt).first()
    
    if not user:
        # Create a simple password hash for test users
        password = "Test123!"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = User(
            email=email,
            password_hash=password_hash,
            phone_number="+233244123456",
            user_type=user_type,
            is_verified=True,
            is_active=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"   Created user: {email} (password: {password})")
    else:
        print(f"   Found existing user: {email}")
    
    return user


def get_or_create_doctor(session: Session) -> Doctor:
    """Get or create a test doctor"""
    # Get or create doctor user
    doctor_user = get_or_create_user(session, "test.doctor@hue.ai", "DOCTOR")
    
    # Check if doctor exists
    stmt = select(Doctor).where(Doctor.user_id == doctor_user.id)
    doctor = session.exec(stmt).first()
    
    if not doctor:
        doctor = Doctor(
            user_id=doctor_user.id,
            legal_name="Dr. Sarah Osei",
            date_of_birth=date(1985, 5, 15),
            license_number="GH-DOC-2025-001",
            specializations=["General Medicine", "Internal Medicine"],
            years_of_practice=10,
            medical_school="University of Ghana Medical School",
            consultation_fee=Decimal("150.00"),
            available_for_consultation=True
        )
        session.add(doctor)
        session.commit()
        session.refresh(doctor)
        print(f"   Created doctor: {doctor.legal_name}")
    else:
        print(f"   Found existing doctor: {doctor.legal_name}")
    
    return doctor


def create_test_patient(session: Session) -> Patient:
    """Create a new test patient with medical history"""
    # Create patient user
    patient_email = f"test.patient.{uuid4().hex[:8]}@hue.ai"
    patient_user = get_or_create_user(session, patient_email, "PATIENT")
    
    # Create patient profile
    patient = Patient(
        user_id=patient_user.id,
        legal_name="Kwame Asante",
        date_of_birth=date(1975, 3, 20),  # 49 years old
        biological_sex="MALE",
        national_id="GH-1234567890",
        emergency_contact_name="Abena Asante",
        emergency_contact_phone="+233244987654",
        address={
            "street": "123 Independence Avenue",
            "city": "Accra",
            "region": "Greater Accra",
            "country": "Ghana"
        }
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    print(f"   Created patient: {patient.legal_name} (ID: {patient.id})")
    
    # Add recent vitals
    vital = PatientVital(
        patient_id=patient.id,
        recorded_at=datetime.utcnow() - timedelta(days=2),
        blood_pressure_systolic=145,
        blood_pressure_diastolic=92,
        heart_rate_bpm=78,
        temperature_celsius=Decimal("36.8"),
        weight_kg=Decimal("82.5"),
        height_cm=Decimal("175.0"),
        bmi=Decimal("26.9"),
        notes="Routine checkup",
        recorded_by_type="DOCTOR"
    )
    session.add(vital)
    print(f"   Added vitals: BP 145/92, Weight 82.5kg, BMI 26.9")
    
    # Add medical conditions
    conditions_data = [
        ("Type 2 Diabetes Mellitus", "E11.9", "CHRONIC", "MODERATE"),
        ("Essential Hypertension", "I10", "CHRONIC", "MODERATE"),
        ("Hyperlipidemia", "E78.5", "CHRONIC", "MILD")
    ]
    
    for condition_name, code, status, severity in conditions_data:
        # Get or create medical code
        stmt = select(MedicalCode).where(MedicalCode.code == code)
        medical_code = session.exec(stmt).first()
        
        if not medical_code:
            medical_code = MedicalCode(
                code=code,
                code_type="ICD10",
                condition_name=condition_name,
                description=f"{condition_name} condition",
                is_active=True
            )
            session.add(medical_code)
            session.commit()
            session.refresh(medical_code)
        
        # Add patient condition
        patient_condition = PatientCondition(
            patient_id=patient.id,
            medical_code_id=medical_code.id,
            diagnosed_date=date.today() - timedelta(days=365),  # Diagnosed 1 year ago
            status=status,
            severity=severity
        )
        session.add(patient_condition)
        print(f"   Added condition: {condition_name} ({severity})")
    
    # Add allergies
    allergies_data = [
        ("Penicillin", "DRUG", "SEVERE", "Anaphylaxis"),
        ("Sulfonamides", "DRUG", "MODERATE", "Rash and itching")
    ]
    
    for allergen_name, allergen_type, severity, reaction in allergies_data:
        allergy = PatientAllergy(
            patient_id=patient.id,
            allergen_name=allergen_name,
            allergen_type=allergen_type,
            severity=severity,
            reaction_type=reaction,
            is_active=True,
            diagnosed_date=date.today() - timedelta(days=730)  # Diagnosed 2 years ago
        )
        session.add(allergy)
        print(f"   Added allergy: {allergen_name} ({severity} - {reaction})")
    
    session.commit()
    return patient


def add_current_medications(session: Session, patient: Patient, doctor: Doctor):
    """Add current medications to patient"""
    # Create active prescription
    prescription = Prescription(
        patient_id=patient.id,
        doctor_id=doctor.id,
        prescription_number=f"RX-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}",
        prescribed_date=date.today() - timedelta(days=30),  # Prescribed 30 days ago
        status="ACTIVE",
        notes="Chronic disease management"
    )
    session.add(prescription)
    session.commit()
    session.refresh(prescription)
    print(f"   Created prescription: {prescription.prescription_number}")
    
    # Define current medications
    medications_data = [
        ("Metformin", "Metformin Hydrochloride", "500mg", "twice daily"),
        ("Lisinopril", "Lisinopril", "10mg", "once daily"),
        ("Atorvastatin", "Atorvastatin", "20mg", "once daily at bedtime")
    ]
    
    for drug_name, generic_name, dosage, frequency in medications_data:
        # Get or create pharmacy code
        stmt = select(PharmacyCode).where(
            PharmacyCode.drug_name.ilike(f"%{drug_name}%")
        )
        pharmacy_code = session.exec(stmt).first()
        
        if not pharmacy_code:
            pharmacy_code = PharmacyCode(
                drug_code=f"NDC-{uuid4().hex[:10].upper()}",
                drug_name=drug_name,
                generic_name=generic_name,
                dosage_form="tablet",
                strength=dosage,
                prescription_required=True,
                is_active=True
            )
            session.add(pharmacy_code)
            session.commit()
            session.refresh(pharmacy_code)
        
        # Add prescription item
        prescription_item = PrescriptionItem(
            prescription_id=prescription.id,
            pharmacy_code_id=pharmacy_code.id,
            quantity=30,
            dosage=dosage,
            frequency=frequency,
            duration="30 days",
            instructions=f"Take {dosage} {frequency} with food",
            substitution_allowed=True
        )
        session.add(prescription_item)
        print(f"   Added medication: {drug_name} {dosage} {frequency}")
    
    session.commit()


def seed_pharmacy_inventory(session: Session):
    """Seed pharmacy inventory with common drugs"""
    # Get or create a pharmacy
    stmt = select(Pharmacy).limit(1)
    pharmacy = session.exec(stmt).first()
    
    if not pharmacy:
        # Create pharmacy user
        pharmacy_user = get_or_create_user(session, "main.pharmacy@hue.ai", "PHARMACY")
        
        pharmacy = Pharmacy(
            user_id=pharmacy_user.id,
            name="Main Hospital Pharmacy",
            license_number="GH-PHARM-001",
            address={
                "street": "Hospital Road",
                "city": "Accra",
                "region": "Greater Accra",
                "country": "Ghana"
            },
            phone_number="+233302123456",
            email="pharmacy@hospital.gh",
            delivery_available=True,
            is_active=True
        )
        session.add(pharmacy)
        session.commit()
        session.refresh(pharmacy)
        print(f"   Created pharmacy: {pharmacy.name}")
    else:
        print(f"   Found existing pharmacy: {pharmacy.name}")
    
    # Common drugs to stock
    drugs_data = [
        # Diabetes medications
        ("Metformin", "Metformin Hydrochloride", "tablet", "500mg", 250, 2.50),
        ("Metformin", "Metformin Hydrochloride", "tablet", "850mg", 200, 3.50),
        ("Glibenclamide", "Glibenclamide", "tablet", "5mg", 150, 1.50),
        ("Insulin", "Human Insulin", "injection", "100IU/ml", 50, 45.00),
        
        # Hypertension medications
        ("Amlodipine", "Amlodipine", "tablet", "5mg", 300, 1.80),
        ("Amlodipine", "Amlodipine", "tablet", "10mg", 250, 2.50),
        ("Lisinopril", "Lisinopril", "tablet", "10mg", 200, 3.20),
        ("Losartan", "Losartan Potassium", "tablet", "50mg", 180, 4.50),
        ("Hydrochlorothiazide", "Hydrochlorothiazide", "tablet", "25mg", 200, 1.20),
        
        # Lipid-lowering medications
        ("Atorvastatin", "Atorvastatin", "tablet", "20mg", 150, 5.50),
        ("Simvastatin", "Simvastatin", "tablet", "40mg", 120, 4.80),
        
        # Antibiotics
        ("Amoxicillin", "Amoxicillin", "capsule", "500mg", 500, 0.80),
        ("Ciprofloxacin", "Ciprofloxacin", "tablet", "500mg", 300, 2.20),
        ("Azithromycin", "Azithromycin", "tablet", "500mg", 200, 3.50),
        ("Cefuroxime", "Cefuroxime", "tablet", "500mg", 150, 4.20),
        
        # Antimalarials
        ("Artemether-Lumefantrine", "Artemether-Lumefantrine", "tablet", "20mg/120mg", 400, 3.00),
        ("Artesunate", "Artesunate", "injection", "60mg", 100, 8.50),
        
        # Pain relievers
        ("Paracetamol", "Paracetamol", "tablet", "500mg", 1000, 0.30),
        ("Ibuprofen", "Ibuprofen", "tablet", "400mg", 500, 0.50),
        ("Diclofenac", "Diclofenac Sodium", "tablet", "50mg", 300, 0.80),
        
        # Asthma medications
        ("Salbutamol Inhaler", "Salbutamol", "inhaler", "100mcg", 80, 12.00),
        ("Beclomethasone Inhaler", "Beclometasone", "inhaler", "100mcg", 60, 18.00),
        
        # Other common drugs
        ("Omeprazole", "Omeprazole", "capsule", "20mg", 250, 1.80),
        ("Cetirizine", "Cetirizine", "tablet", "10mg", 300, 0.60),
        ("Vitamin B Complex", "Vitamin B Complex", "tablet", "N/A", 500, 0.40)
    ]
    
    added_count = 0
    for drug_name, generic_name, dosage_form, strength, quantity, price in drugs_data:
        # Get or create pharmacy code
        stmt = select(PharmacyCode).where(
            PharmacyCode.drug_name == drug_name,
            PharmacyCode.strength == strength
        )
        pharmacy_code = session.exec(stmt).first()
        
        if not pharmacy_code:
            pharmacy_code = PharmacyCode(
                drug_code=f"NDC-{uuid4().hex[:10].upper()}",
                drug_name=drug_name,
                generic_name=generic_name,
                dosage_form=dosage_form,
                strength=strength,
                prescription_required=True if drug_name not in ["Paracetamol", "Cetirizine", "Vitamin B Complex"] else False,
                is_active=True
            )
            session.add(pharmacy_code)
            session.commit()
            session.refresh(pharmacy_code)
        
        # Check if inventory exists
        stmt = select(PharmacyInventory).where(
            PharmacyInventory.pharmacy_id == pharmacy.id,
            PharmacyInventory.pharmacy_code_id == pharmacy_code.id
        )
        existing = session.exec(stmt).first()
        
        if not existing:
            # Add to inventory
            inventory = PharmacyInventory(
                pharmacy_id=pharmacy.id,
                pharmacy_code_id=pharmacy_code.id,
                quantity_available=quantity,
                unit_price=Decimal(str(price)),
                expiry_date=date.today() + timedelta(days=365 * 2),  # 2 years
                is_insurance_covered=True
            )
            session.add(inventory)
            added_count += 1
    
    session.commit()
    print(f"   Added {added_count} drugs to inventory")


async def main():
    """Main seed function"""
    print_header("DRUG SUGGESTER TEST DATA SEEDING")
    
    with Session(engine) as session:
        # Step 1: Create test doctor
        print_step("Step 1: Creating/Finding Test Doctor")
        doctor = get_or_create_doctor(session)
        
        # Step 2: Create test patient
        print_step("Step 2: Creating New Test Patient")
        patient = create_test_patient(session)
        
        # Step 3: Add current medications
        print_step("Step 3: Adding Current Medications to Patient")
        add_current_medications(session, patient, doctor)
        
        # Step 4: Seed pharmacy inventory
        print_step("Step 4: Seeding Pharmacy Inventory")
        seed_pharmacy_inventory(session)
        
        print_header("SEEDING COMPLETE!")
        print(f"\n✅ Test Patient Created:")
        print(f"   Name: {patient.legal_name}")
        print(f"   Patient ID: {patient.id}")
        print(f"   Email: {session.get(User, patient.user_id).email}")
        print(f"   Age: 49 years")
        print(f"   Conditions: Type 2 Diabetes, Hypertension, Hyperlipidemia")
        print(f"   Allergies: Penicillin (SEVERE), Sulfonamides (MODERATE)")
        print(f"   Current Medications: Metformin, Lisinopril, Atorvastatin")
        
        print(f"\n✅ Test Doctor:")
        print(f"   Name: {doctor.legal_name}")
        print(f"   Doctor ID: {doctor.id}")
        
        print(f"\n✅ Pharmacy Inventory:")
        stmt = select(PharmacyInventory)
        inventory_count = len(session.exec(stmt).all())
        print(f"   Total drugs in stock: {inventory_count}")
        
        print("\n" + "=" * 80)
        print("\n📝 Use these IDs for testing:")
        print(f"   PATIENT_ID={patient.id}")
        print(f"   DOCTOR_ID={doctor.id}")
        print("\n🧪 Now run the comprehensive test again to see:")
        print("   • RxNav = True (has current medications)")
        print("   • PRIMARY suggestions (drugs in stock)")
        print("   • Interaction warnings (drug-drug interactions)")
        print("   • Allergy alerts (Penicillin contraindicated)")
        print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

