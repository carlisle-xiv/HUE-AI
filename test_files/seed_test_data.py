"""
Seed script for creating comprehensive test patient data.
Run this script to populate the database with a test patient and all related medical records.

Usage:
    python seed_test_data.py --seed    # Create test data
    python seed_test_data.py --clear   # Remove test data
    python seed_test_data.py           # Default: seed data
"""

import argparse
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID
import sys

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from src.database import engine
from src.models.core import User, Wallet
from src.models.patients import Patient, PatientVital, PatientHabit, PatientCondition
from src.models.doctors import Doctor, DoctorSchedule
from src.models.reference import MedicalCode, PharmacyCode, MedicalService
from src.models.appointments import Appointment, Consultation
from src.models.prescriptions import Prescription, PrescriptionItem
from src.models.tests import TestOrder, TestResult


# Test data constants
TEST_PATIENT_EMAIL = "test.patient@hue.ai"
TEST_DOCTOR_EMAIL = "test.doctor@hue.ai"
TEST_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEcRGu"  # "TestPassword123!"


def get_or_create_medical_codes(session: Session) -> dict[str, MedicalCode]:
    """Create or get medical condition codes"""
    codes = {
        "HYPERTENSION": {
            "code": "I10",
            "code_type": "ICD10",
            "condition_name": "Essential (primary) hypertension",
            "description": "High blood pressure without known cause",
            "category": "Cardiovascular",
            "severity_level": "MEDIUM"
        },
        "DIABETES": {
            "code": "E11.9",
            "code_type": "ICD10",
            "condition_name": "Type 2 diabetes mellitus",
            "description": "Type 2 diabetes without complications",
            "category": "Endocrine",
            "severity_level": "MEDIUM"
        },
        "ASTHMA": {
            "code": "J45.9",
            "code_type": "ICD10",
            "condition_name": "Asthma, unspecified",
            "description": "Chronic respiratory condition",
            "category": "Respiratory",
            "severity_level": "MEDIUM"
        },
        "OBESITY": {
            "code": "E66.9",
            "code_type": "ICD10",
            "condition_name": "Obesity, unspecified",
            "description": "Excess body weight",
            "category": "Endocrine",
            "severity_level": "LOW"
        },
        "ANXIETY": {
            "code": "F41.9",
            "code_type": "ICD10",
            "condition_name": "Anxiety disorder, unspecified",
            "description": "General anxiety disorder",
            "category": "Mental Health",
            "severity_level": "MEDIUM"
        }
    }
    
    medical_codes = {}
    for key, data in codes.items():
        existing = session.exec(
            select(MedicalCode).where(MedicalCode.code == data["code"])
        ).first()
        
        if existing:
            medical_codes[key] = existing
        else:
            medical_code = MedicalCode(**data)
            session.add(medical_code)
            medical_codes[key] = medical_code
    
    session.commit()
    return medical_codes


def get_or_create_pharmacy_codes(session: Session) -> dict[str, PharmacyCode]:
    """Create or get pharmacy drug codes"""
    drugs = {
        "LISINOPRIL": {
            "drug_code": "NDC-0173-0440",
            "drug_name": "Lisinopril",
            "generic_name": "Lisinopril",
            "brand_names": ["Prinivil", "Zestril"],
            "dosage_form": "Tablet",
            "strength": "10mg",
            "therapeutic_class": "ACE Inhibitor",
            "fda_approved": True,
            "prescription_required": True
        },
        "METFORMIN": {
            "drug_code": "NDC-0378-0321",
            "drug_name": "Metformin",
            "generic_name": "Metformin Hydrochloride",
            "brand_names": ["Glucophage", "Fortamet"],
            "dosage_form": "Tablet",
            "strength": "500mg",
            "therapeutic_class": "Antidiabetic",
            "fda_approved": True,
            "prescription_required": True
        },
        "ALBUTEROL": {
            "drug_code": "NDC-0173-0682",
            "drug_name": "Albuterol",
            "generic_name": "Albuterol Sulfate",
            "brand_names": ["Ventolin", "ProAir"],
            "dosage_form": "Inhaler",
            "strength": "90mcg",
            "therapeutic_class": "Bronchodilator",
            "fda_approved": True,
            "prescription_required": True
        },
        "ATORVASTATIN": {
            "drug_code": "NDC-0071-0155",
            "drug_name": "Atorvastatin",
            "generic_name": "Atorvastatin Calcium",
            "brand_names": ["Lipitor"],
            "dosage_form": "Tablet",
            "strength": "20mg",
            "therapeutic_class": "Statin",
            "fda_approved": True,
            "prescription_required": True
        },
        "SERTRALINE": {
            "drug_code": "NDC-0049-4960",
            "drug_name": "Sertraline",
            "generic_name": "Sertraline Hydrochloride",
            "brand_names": ["Zoloft"],
            "dosage_form": "Tablet",
            "strength": "50mg",
            "therapeutic_class": "SSRI Antidepressant",
            "fda_approved": True,
            "prescription_required": True
        }
    }
    
    pharmacy_codes = {}
    for key, data in drugs.items():
        existing = session.exec(
            select(PharmacyCode).where(PharmacyCode.drug_code == data["drug_code"])
        ).first()
        
        if existing:
            pharmacy_codes[key] = existing
        else:
            pharmacy_code = PharmacyCode(**data)
            session.add(pharmacy_code)
            pharmacy_codes[key] = pharmacy_code
    
    session.commit()
    return pharmacy_codes


def get_or_create_medical_services(session: Session) -> dict[str, MedicalService]:
    """Create or get medical services"""
    services = {
        "CBC": {
            "service_name": "Complete Blood Count (CBC)",
            "service_type": "LAB_TEST",
            "description": "Comprehensive blood test measuring different blood components",
            "base_price": 45.00,
            "sample_required": "Blood",
            "turnaround_time_days": 1,
            "requires_fasting": False
        },
        "LIPID_PANEL": {
            "service_name": "Lipid Panel",
            "service_type": "LAB_TEST",
            "description": "Tests cholesterol and triglyceride levels",
            "base_price": 55.00,
            "sample_required": "Blood",
            "turnaround_time_days": 1,
            "requires_fasting": True
        },
        "HBA1C": {
            "service_name": "HbA1c Test",
            "service_type": "LAB_TEST",
            "description": "Measures average blood sugar levels over 2-3 months",
            "base_price": 60.00,
            "sample_required": "Blood",
            "turnaround_time_days": 2,
            "requires_fasting": False
        }
    }
    
    medical_services = {}
    for key, data in services.items():
        existing = session.exec(
            select(MedicalService).where(MedicalService.service_name == data["service_name"])
        ).first()
        
        if existing:
            medical_services[key] = existing
        else:
            service = MedicalService(**data)
            session.add(service)
            medical_services[key] = service
    
    session.commit()
    return medical_services


def create_test_doctor(session: Session) -> Doctor:
    """Create or get test doctor"""
    # Check if doctor user exists
    existing_user = session.exec(
        select(User).where(User.email == TEST_DOCTOR_EMAIL)
    ).first()
    
    if existing_user:
        doctor = session.exec(
            select(Doctor).where(Doctor.user_id == existing_user.id)
        ).first()
        if doctor:
            return doctor
    
    # Create doctor user
    doctor_user = User(
        email=TEST_DOCTOR_EMAIL,
        password_hash=TEST_PASSWORD_HASH,
        phone_number="+233244567890",
        user_type="DOCTOR",
        country="GH",
        is_active=True,
        email_verified=True,
        phone_verified=True
    )
    session.add(doctor_user)
    session.flush()
    
    # Create doctor profile
    doctor = Doctor(
        user_id=doctor_user.id,
        legal_name="Dr. Sarah Johnson",
        preferred_name="Dr. Sarah",
        date_of_birth=date(1980, 5, 15),
        gender="Female",
        license_number="GH-MED-2010-12345",
        specializations=["General Practice", "Internal Medicine"],
        years_of_practice=14,
        medical_school="University of Ghana Medical School",
        certifications={
            "board_certification": "Ghana Medical & Dental Council",
            "additional": ["ACLS", "BLS"]
        },
        languages=["English", "Twi", "Ga"],
        bio="Experienced general practitioner with focus on preventive care and chronic disease management.",
        consultation_fee=Decimal("150.00"),
        rating_average=Decimal("4.85"),
        total_ratings=127,
        is_active=True,
        available_for_consultation=True
    )
    session.add(doctor)
    
    # Add doctor schedule
    for day in range(1, 6):  # Monday to Friday
        schedule = DoctorSchedule(
            doctor_id=doctor.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_available=True
        )
        session.add(schedule)
    
    session.commit()
    return doctor


def create_test_patient(session: Session) -> tuple[User, Patient]:
    """Create or get test patient"""
    # Check if patient user exists
    existing_user = session.exec(
        select(User).where(User.email == TEST_PATIENT_EMAIL)
    ).first()
    
    if existing_user:
        patient = session.exec(
            select(Patient).where(Patient.user_id == existing_user.id)
        ).first()
        if patient:
            return existing_user, patient
    
    # Create patient user
    patient_user = User(
        email=TEST_PATIENT_EMAIL,
        password_hash=TEST_PASSWORD_HASH,
        phone_number="+233201234567",
        user_type="PATIENT",
        country="GH",
        is_active=True,
        email_verified=True,
        phone_verified=True
    )
    session.add(patient_user)
    session.flush()
    
    # Create patient profile
    patient = Patient(
        user_id=patient_user.id,
        legal_name="John Mensah",
        preferred_name="John",
        date_of_birth=date(1985, 3, 20),
        biological_sex="MALE",
        gender_identity="Male",
        national_id="GHA-1985-03-20-12345",
        emergency_contact_name="Mary Mensah",
        emergency_contact_phone="+233209876543",
        address={
            "street": "123 Independence Avenue",
            "city": "Accra",
            "region": "Greater Accra",
            "country": "Ghana",
            "postal_code": "GA-123-4567"
        }
    )
    session.add(patient)
    session.flush()
    
    # Create wallet
    wallet = Wallet(
        user_id=patient_user.id,
        balance=Decimal("1000.00"),
        eth_wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    )
    session.add(wallet)
    
    session.commit()
    return patient_user, patient


def create_patient_vitals(session: Session, patient: Patient):
    """Create patient vital records"""
    # Recent vitals
    vital1 = PatientVital(
        patient_id=patient.id,
        recorded_at=datetime.utcnow() - timedelta(days=7),
        blood_type="O+",
        blood_pressure_systolic=135,
        blood_pressure_diastolic=88,
        heart_rate_bpm=78,
        temperature_celsius=Decimal("36.8"),
        respiratory_rate=16,
        oxygen_saturation=Decimal("98.0"),
        glucose_level=Decimal("125.5"),
        weight_kg=Decimal("82.5"),
        height_cm=Decimal("175.0"),
        bmi=Decimal("26.9"),
        notes="Patient reports feeling well. Slight elevation in BP.",
        recorded_by_type="DOCTOR"
    )
    
    # Older vitals
    vital2 = PatientVital(
        patient_id=patient.id,
        recorded_at=datetime.utcnow() - timedelta(days=30),
        blood_type="O+",
        blood_pressure_systolic=138,
        blood_pressure_diastolic=90,
        heart_rate_bpm=80,
        temperature_celsius=Decimal("37.0"),
        respiratory_rate=18,
        oxygen_saturation=Decimal("97.5"),
        glucose_level=Decimal("130.0"),
        weight_kg=Decimal("84.0"),
        height_cm=Decimal("175.0"),
        bmi=Decimal("27.4"),
        notes="Follow-up visit. Continue monitoring BP and glucose.",
        recorded_by_type="DOCTOR"
    )
    
    # Latest vitals
    vital3 = PatientVital(
        patient_id=patient.id,
        recorded_at=datetime.utcnow() - timedelta(days=1),
        blood_type="O+",
        blood_pressure_systolic=132,
        blood_pressure_diastolic=85,
        heart_rate_bpm=75,
        temperature_celsius=Decimal("36.7"),
        respiratory_rate=15,
        oxygen_saturation=Decimal("98.5"),
        glucose_level=Decimal("118.0"),
        weight_kg=Decimal("81.0"),
        height_cm=Decimal("175.0"),
        bmi=Decimal("26.4"),
        notes="Improvement noted. Medication adherence good.",
        recorded_by_type="DOCTOR"
    )
    
    session.add_all([vital1, vital2, vital3])
    session.commit()


def create_patient_habits(session: Session, patient: Patient):
    """Create patient habit tracking records"""
    today = date.today()
    
    habits = [
        # Water intake
        PatientHabit(
            patient_id=patient.id,
            habit_type="WATER_INTAKE",
            target_value=Decimal("2.5"),
            target_unit="liters",
            date=today - timedelta(days=1),
            actual_value=Decimal("2.2"),
            notes="Good progress"
        ),
        PatientHabit(
            patient_id=patient.id,
            habit_type="WATER_INTAKE",
            target_value=Decimal("2.5"),
            target_unit="liters",
            date=today,
            actual_value=Decimal("1.8"),
            notes="Need to drink more"
        ),
        # Sleep
        PatientHabit(
            patient_id=patient.id,
            habit_type="SLEEP",
            target_value=Decimal("8.0"),
            target_unit="hours",
            date=today - timedelta(days=1),
            actual_value=Decimal("7.5"),
            notes="Slept well"
        ),
        PatientHabit(
            patient_id=patient.id,
            habit_type="SLEEP",
            target_value=Decimal("8.0"),
            target_unit="hours",
            date=today,
            actual_value=Decimal("6.5"),
            notes="Woke up early"
        ),
        # Exercise
        PatientHabit(
            patient_id=patient.id,
            habit_type="EXERCISE",
            target_value=Decimal("30.0"),
            target_unit="minutes",
            date=today - timedelta(days=1),
            actual_value=Decimal("45.0"),
            notes="Morning jog"
        ),
        PatientHabit(
            patient_id=patient.id,
            habit_type="EXERCISE",
            target_value=Decimal("30.0"),
            target_unit="minutes",
            date=today,
            actual_value=Decimal("20.0"),
            notes="Light walk"
        )
    ]
    
    session.add_all(habits)
    session.commit()


def create_patient_conditions(session: Session, patient: Patient, doctor: Doctor, medical_codes: dict):
    """Create patient medical conditions"""
    conditions = [
        PatientCondition(
            patient_id=patient.id,
            medical_code_id=medical_codes["HYPERTENSION"].id,
            diagnosed_date=date(2020, 6, 15),
            status="CHRONIC",
            severity="MODERATE",
            notes="Well controlled with medication. Regular monitoring required.",
            diagnosed_by_id=doctor.id
        ),
        PatientCondition(
            patient_id=patient.id,
            medical_code_id=medical_codes["DIABETES"].id,
            diagnosed_date=date(2021, 2, 10),
            status="CHRONIC",
            severity="MODERATE",
            notes="Type 2 diabetes. Managing with lifestyle changes and medication.",
            diagnosed_by_id=doctor.id
        ),
        PatientCondition(
            patient_id=patient.id,
            medical_code_id=medical_codes["OBESITY"].id,
            diagnosed_date=date(2020, 6, 15),
            status="ACTIVE",
            severity="MILD",
            notes="Patient on weight loss program. Progress monitored monthly.",
            diagnosed_by_id=doctor.id
        )
    ]
    
    session.add_all(conditions)
    session.commit()


def create_appointments_and_consultations(session: Session, patient: Patient, doctor: Doctor, medical_codes: dict) -> list[Consultation]:
    """Create appointments and consultations"""
    # Completed appointment (30 days ago)
    appointment1 = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_datetime=datetime.utcnow() - timedelta(days=30),
        duration_minutes=30,
        buffer_minutes=15,
        appointment_type="VIDEO",
        status="COMPLETED",
        chief_complaint="Follow-up for hypertension and diabetes management",
        notes="Regular check-up"
    )
    session.add(appointment1)
    session.flush()
    
    # Consultation for completed appointment
    consultation1 = Consultation(
        appointment_id=appointment1.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        consultation_type="VIDEO",
        start_time=appointment1.appointment_datetime,
        end_time=appointment1.appointment_datetime + timedelta(minutes=30),
        chief_complaint="Follow-up for hypertension and diabetes management",
        history_of_present_illness="Patient reports good medication adherence. Occasional headaches. Blood sugar levels improving.",
        assessment="Hypertension and Type 2 Diabetes - both conditions stable with current treatment plan.",
        diagnosis_codes=[medical_codes["HYPERTENSION"].id, medical_codes["DIABETES"].id],
        treatment_plan="Continue current medications. Increase exercise to 30 min daily. Follow up in 1 month.",
        doctor_notes="Patient showing good progress. Weight down 2kg. BP readings improved.",
        patient_feedback="Very helpful consultation. Clear instructions provided.",
        consultation_rating=5,
        is_completed=True
    )
    session.add(consultation1)
    
    # Scheduled appointment (7 days from now)
    appointment2 = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_datetime=datetime.utcnow() + timedelta(days=7),
        duration_minutes=30,
        buffer_minutes=15,
        appointment_type="VIDEO",
        status="SCHEDULED",
        chief_complaint="Routine follow-up and lab results review",
        notes="Review HbA1c results"
    )
    session.add(appointment2)
    
    session.commit()
    return [consultation1]


def create_prescriptions(session: Session, patient: Patient, doctor: Doctor, consultations: list[Consultation], pharmacy_codes: dict):
    """Create prescriptions and prescription items"""
    consultation = consultations[0]
    
    # Prescription 1 - for hypertension and diabetes
    prescription1 = Prescription(
        consultation_id=consultation.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        prescription_number=f"RX-{datetime.utcnow().strftime('%Y%m%d')}-001",
        prescribed_date=consultation.start_time.date(),
        status="ACTIVE",
        notes="Take medications as directed. Monitor blood pressure daily."
    )
    session.add(prescription1)
    session.flush()
    
    # Prescription items
    items = [
        PrescriptionItem(
            prescription_id=prescription1.id,
            pharmacy_code_id=pharmacy_codes["LISINOPRIL"].id,
            quantity=30,
            dosage="10mg",
            frequency="Once daily",
            duration="30 days",
            instructions="Take in the morning with water",
            substitution_allowed=True
        ),
        PrescriptionItem(
            prescription_id=prescription1.id,
            pharmacy_code_id=pharmacy_codes["METFORMIN"].id,
            quantity=60,
            dosage="500mg",
            frequency="Twice daily",
            duration="30 days",
            instructions="Take with meals (breakfast and dinner)",
            substitution_allowed=True
        ),
        PrescriptionItem(
            prescription_id=prescription1.id,
            pharmacy_code_id=pharmacy_codes["ATORVASTATIN"].id,
            quantity=30,
            dosage="20mg",
            frequency="Once daily",
            duration="30 days",
            instructions="Take in the evening",
            substitution_allowed=True
        )
    ]
    
    session.add_all(items)
    session.commit()


def create_test_orders_and_results(session: Session, patient: Patient, doctor: Doctor, medical_services: dict):
    """Create test orders and results"""
    # Completed test order (15 days ago)
    test_order1 = TestOrder(
        patient_id=patient.id,
        doctor_id=doctor.id,
        medical_service_id=medical_services["LIPID_PANEL"].id,
        order_number=f"TEST-{datetime.utcnow().strftime('%Y%m%d')}-001",
        order_type="INDIVIDUAL",
        total_amount=Decimal("55.00"),
        status="COMPLETED",
        scheduled_date=(datetime.utcnow() - timedelta(days=15)).date(),
        sample_collection_method="CLINIC_VISIT",
        billing_entity="PATIENT",
        special_instructions="Fasting required - 12 hours"
    )
    session.add(test_order1)
    session.flush()
    
    # Test result for completed order
    test_result1 = TestResult(
        test_order_id=test_order1.id,
        result_data={
            "total_cholesterol": {"value": 195, "unit": "mg/dL"},
            "ldl_cholesterol": {"value": 120, "unit": "mg/dL"},
            "hdl_cholesterol": {"value": 45, "unit": "mg/dL"},
            "triglycerides": {"value": 150, "unit": "mg/dL"},
            "cholesterol_hdl_ratio": {"value": 4.3, "unit": "ratio"}
        },
        interpretation="Borderline high cholesterol. LDL slightly elevated. Recommend lifestyle modifications and continue statin therapy.",
        normal_ranges={
            "total_cholesterol": "< 200 mg/dL",
            "ldl_cholesterol": "< 100 mg/dL",
            "hdl_cholesterol": "> 40 mg/dL",
            "triglycerides": "< 150 mg/dL"
        },
        abnormal_flags=["LDL elevated"],
        reviewed_by_id=doctor.id,
        reviewed_at=datetime.utcnow() - timedelta(days=14)
    )
    session.add(test_result1)
    
    # Processing test order (scheduled for 2 days ago, results pending)
    test_order2 = TestOrder(
        patient_id=patient.id,
        doctor_id=doctor.id,
        medical_service_id=medical_services["HBA1C"].id,
        order_number=f"TEST-{datetime.utcnow().strftime('%Y%m%d')}-002",
        order_type="INDIVIDUAL",
        total_amount=Decimal("60.00"),
        status="PROCESSING",
        scheduled_date=(datetime.utcnow() - timedelta(days=2)).date(),
        sample_collection_method="CLINIC_VISIT",
        billing_entity="PATIENT",
        special_instructions="No fasting required"
    )
    session.add(test_order2)
    
    session.commit()


def seed_test_data():
    """Main function to seed all test data"""
    print("=" * 60)
    print("SEEDING TEST PATIENT DATA")
    print("=" * 60)
    
    with Session(engine) as session:
        try:
            # 1. Create reference data
            print("\n📋 Creating reference data...")
            medical_codes = get_or_create_medical_codes(session)
            print(f"   ✓ Created/found {len(medical_codes)} medical codes")
            
            pharmacy_codes = get_or_create_pharmacy_codes(session)
            print(f"   ✓ Created/found {len(pharmacy_codes)} pharmacy codes")
            
            medical_services = get_or_create_medical_services(session)
            print(f"   ✓ Created/found {len(medical_services)} medical services")
            
            # 2. Create test doctor
            print("\n👨‍⚕️  Creating test doctor...")
            doctor = create_test_doctor(session)
            print(f"   ✓ Doctor created: {doctor.legal_name}")
            print(f"   ✓ Doctor ID: {doctor.id}")
            
            # 3. Create test patient
            print("\n👤 Creating test patient...")
            patient_user, patient = create_test_patient(session)
            print(f"   ✓ Patient created: {patient.legal_name}")
            print(f"   ✓ Patient ID: {patient.id}")
            print(f"   ✓ User ID: {patient_user.id}")
            
            # 4. Create patient vitals
            print("\n❤️  Creating patient vitals...")
            create_patient_vitals(session, patient)
            print("   ✓ Created 3 vital records")
            
            # 5. Create patient habits
            print("\n📊 Creating patient habits...")
            create_patient_habits(session, patient)
            print("   ✓ Created 6 habit tracking records")
            
            # 6. Create patient conditions
            print("\n🏥 Creating patient conditions...")
            create_patient_conditions(session, patient, doctor, medical_codes)
            print("   ✓ Created 3 medical conditions")
            
            # 7. Create appointments and consultations
            print("\n📅 Creating appointments and consultations...")
            consultations = create_appointments_and_consultations(session, patient, doctor, medical_codes)
            print("   ✓ Created 2 appointments (1 completed, 1 scheduled)")
            print("   ✓ Created 1 consultation record")
            
            # 8. Create prescriptions
            print("\n💊 Creating prescriptions...")
            create_prescriptions(session, patient, doctor, consultations, pharmacy_codes)
            print("   ✓ Created 1 prescription with 3 medication items")
            
            # 9. Create test orders
            print("\n🧪 Creating test orders and results...")
            create_test_orders_and_results(session, patient, doctor, medical_services)
            print("   ✓ Created 2 test orders (1 completed, 1 processing)")
            print("   ✓ Created 1 test result")
            
            # Print summary
            print("\n" + "=" * 60)
            print("✅ TEST DATA SUCCESSFULLY CREATED")
            print("=" * 60)
            print("\n📝 TEST PATIENT INFORMATION:")
            print(f"   Patient ID:  {patient.id}")
            print(f"   Patient Name: {patient.legal_name}")
            print(f"   Email:        {TEST_PATIENT_EMAIL}")
            print(f"   Password:     TestPassword123!")
            print(f"\n   Doctor ID:    {doctor.id}")
            print(f"   Doctor Name:  {doctor.legal_name}")
            print(f"   Doctor Email: {TEST_DOCTOR_EMAIL}")
            print(f"   Password:     TestPassword123!")
            print("=" * 60)
            
            # Save to file
            with open("test_patient_info.txt", "w") as f:
                f.write("TEST PATIENT INFORMATION\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Patient ID:   {patient.id}\n")
                f.write(f"Patient Name: {patient.legal_name}\n")
                f.write(f"Email:        {TEST_PATIENT_EMAIL}\n")
                f.write(f"Password:     TestPassword123!\n\n")
                f.write(f"Doctor ID:    {doctor.id}\n")
                f.write(f"Doctor Name:  {doctor.legal_name}\n")
                f.write(f"Doctor Email: {TEST_DOCTOR_EMAIL}\n")
                f.write(f"Password:     TestPassword123!\n\n")
                f.write(f"Created at:   {datetime.utcnow().isoformat()}\n")
            
            print("\n💾 Test patient info saved to: test_patient_info.txt\n")
            
        except IntegrityError as e:
            session.rollback()
            print(f"\n❌ Error: Data may already exist. {str(e)}")
            print("   Try running with --clear first to remove existing test data.\n")
            sys.exit(1)
        except Exception as e:
            session.rollback()
            print(f"\n❌ Error seeding data: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def clear_test_data():
    """Remove all test data"""
    print("=" * 60)
    print("CLEARING TEST DATA")
    print("=" * 60)
    
    with Session(engine) as session:
        try:
            # Find test users
            test_patient_user = session.exec(
                select(User).where(User.email == TEST_PATIENT_EMAIL)
            ).first()
            
            test_doctor_user = session.exec(
                select(User).where(User.email == TEST_DOCTOR_EMAIL)
            ).first()
            
            if test_patient_user:
                print(f"\n🗑️  Removing test patient: {TEST_PATIENT_EMAIL}")
                # SQLModel will handle cascade deletes based on relationships
                session.delete(test_patient_user)
                print("   ✓ Test patient and related records deleted")
            else:
                print(f"\n⚠️  Test patient not found: {TEST_PATIENT_EMAIL}")
            
            if test_doctor_user:
                print(f"\n🗑️  Removing test doctor: {TEST_DOCTOR_EMAIL}")
                session.delete(test_doctor_user)
                print("   ✓ Test doctor and related records deleted")
            else:
                print(f"\n⚠️  Test doctor not found: {TEST_DOCTOR_EMAIL}")
            
            session.commit()
            
            print("\n" + "=" * 60)
            print("✅ TEST DATA CLEARED")
            print("=" * 60 + "\n")
            
        except Exception as e:
            session.rollback()
            print(f"\n❌ Error clearing data: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Seed or clear test patient data in the HUE database"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed test data (default action)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear test data"
    )
    
    args = parser.parse_args()
    
    # Default to seed if no arguments provided
    if not args.clear and not args.seed:
        args.seed = True
    
    if args.clear:
        clear_test_data()
    elif args.seed:
        seed_test_data()


if __name__ == "__main__":
    main()

