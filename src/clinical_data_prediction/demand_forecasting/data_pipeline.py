import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

import pandas as pd
from sqlmodel import Session, select, func, and_

from src.models.pharmacy import DrugOrder, DrugOrderItem, Pharmacy, PharmacyInventory
from src.models.prescriptions import Prescription, PrescriptionItem
from src.models.reference import PharmacyCode

# Configure logging
logger = logging.getLogger(__name__)


class DemandDataPipeline:
    """
    Pipeline for aggregating and preparing demand data for forecasting.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_demand_data_per_drug_pharmacy(
        self,
        pharmacy_id: UUID,
        drug_id: UUID,
        days_back: int = 365
    ) -> pd.DataFrame:
        """
        Get historical demand data for a specific drug at a specific pharmacy.
        
        Args:
            pharmacy_id: Pharmacy UUID
            drug_id: Drug/pharmacy_code UUID
            days_back: Number of days of historical data
            
        Returns:
            DataFrame with columns: ds (date), y (quantity)
        """
        logger.info(f"Fetching demand data for pharmacy {pharmacy_id}, drug {drug_id}")
        
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Query drug order items for this pharmacy and drug
        stmt = (
            select(
                func.date(DrugOrder.created_at).label('order_date'),
                func.sum(DrugOrderItem.quantity_ordered).label('total_quantity')
            )
            .join(DrugOrderItem, DrugOrder.id == DrugOrderItem.drug_order_id)
            .join(PharmacyInventory, DrugOrderItem.pharmacy_inventory_id == PharmacyInventory.id)
            .where(
                and_(
                    DrugOrder.pharmacy_id == pharmacy_id,
                    PharmacyInventory.pharmacy_code_id == drug_id,
                    DrugOrder.created_at >= start_date,
                    DrugOrder.status.in_(['COMPLETED', 'DELIVERED', 'SHIPPED', 'PREPARED'])
                )
            )
            .group_by(func.date(DrugOrder.created_at))
            .order_by(func.date(DrugOrder.created_at))
        )
        
        results = self.session.exec(stmt).all()
        
        if not results:
            logger.warning(f"No demand data found for pharmacy {pharmacy_id}, drug {drug_id}")
            return self._create_empty_dataframe(start_date)
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {'ds': row.order_date, 'y': float(row.total_quantity)}
            for row in results
        ])
        
        # Fill missing dates with 0
        df = self._fill_missing_dates(df, start_date)
        
        logger.info(f"Retrieved {len(df)} data points for pharmacy {pharmacy_id}, drug {drug_id}")
        
        return df
    
    def get_demand_data_per_pharmacy(
        self,
        pharmacy_id: UUID,
        days_back: int = 365
    ) -> dict[UUID, pd.DataFrame]:
        """
        Get historical demand data for all drugs at a specific pharmacy.
        
        Args:
            pharmacy_id: Pharmacy UUID
            days_back: Number of days of historical data
            
        Returns:
            Dictionary mapping drug_id to DataFrame
        """
        logger.info(f"Fetching demand data for pharmacy {pharmacy_id}")
        
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get all drugs with orders at this pharmacy
        drugs_stmt = (
            select(PharmacyInventory.pharmacy_code_id)
            .join(DrugOrderItem, DrugOrderItem.pharmacy_inventory_id == PharmacyInventory.id)
            .join(DrugOrder, DrugOrder.id == DrugOrderItem.drug_order_id)
            .where(
                and_(
                    DrugOrder.pharmacy_id == pharmacy_id,
                    DrugOrder.created_at >= start_date
                )
            )
            .distinct()
        )
        
        drug_ids = self.session.exec(drugs_stmt).all()
        
        result = {}
        for drug_id in drug_ids:
            result[drug_id] = self.get_demand_data_per_drug_pharmacy(
                pharmacy_id, drug_id, days_back
            )
        
        logger.info(f"Retrieved data for {len(result)} drugs at pharmacy {pharmacy_id}")
        
        return result
    
    def get_demand_data_per_drug(
        self,
        drug_id: UUID,
        days_back: int = 365
    ) -> pd.DataFrame:
        """
        Get platform-wide historical demand data for a specific drug.
        
        Args:
            drug_id: Drug/pharmacy_code UUID
            days_back: Number of days of historical data
            
        Returns:
            DataFrame with columns: ds (date), y (quantity)
        """
        logger.info(f"Fetching platform-wide demand data for drug {drug_id}")
        
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Query drug order items across all pharmacies
        stmt = (
            select(
                func.date(DrugOrder.created_at).label('order_date'),
                func.sum(DrugOrderItem.quantity_ordered).label('total_quantity')
            )
            .join(DrugOrderItem, DrugOrder.id == DrugOrderItem.drug_order_id)
            .join(PharmacyInventory, DrugOrderItem.pharmacy_inventory_id == PharmacyInventory.id)
            .where(
                and_(
                    PharmacyInventory.pharmacy_code_id == drug_id,
                    DrugOrder.created_at >= start_date,
                    DrugOrder.status.in_(['COMPLETED', 'DELIVERED', 'SHIPPED', 'PREPARED'])
                )
            )
            .group_by(func.date(DrugOrder.created_at))
            .order_by(func.date(DrugOrder.created_at))
        )
        
        results = self.session.exec(stmt).all()
        
        if not results:
            logger.warning(f"No demand data found for drug {drug_id}")
            return self._create_empty_dataframe(start_date)
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {'ds': row.order_date, 'y': float(row.total_quantity)}
            for row in results
        ])
        
        # Fill missing dates with 0
        df = self._fill_missing_dates(df, start_date)
        
        logger.info(f"Retrieved {len(df)} data points for drug {drug_id}")
        
        return df
    
    def get_aggregate_demand_data(
        self,
        days_back: int = 365
    ) -> dict[UUID, pd.DataFrame]:
        """
        Get platform-wide aggregate demand data for all drugs.
        
        Args:
            days_back: Number of days of historical data
            
        Returns:
            Dictionary mapping drug_id to DataFrame
        """
        logger.info("Fetching aggregate demand data for all drugs")
        
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get all drugs with orders
        drugs_stmt = (
            select(PharmacyInventory.pharmacy_code_id)
            .join(DrugOrderItem, DrugOrderItem.pharmacy_inventory_id == PharmacyInventory.id)
            .join(DrugOrder, DrugOrder.id == DrugOrderItem.drug_order_id)
            .where(DrugOrder.created_at >= start_date)
            .distinct()
        )
        
        drug_ids = self.session.exec(drugs_stmt).all()
        
        result = {}
        for drug_id in drug_ids:
            result[drug_id] = self.get_demand_data_per_drug(drug_id, days_back)
        
        logger.info(f"Retrieved aggregate data for {len(result)} drugs")
        
        return result
    
    def get_drug_info(self, drug_id: UUID) -> Optional[dict]:
        """
        Get drug information.
        
        Args:
            drug_id: Drug/pharmacy_code UUID
            
        Returns:
            Dictionary with drug information or None
        """
        drug = self.session.get(PharmacyCode, drug_id)
        if not drug:
            return None
        
        return {
            'drug_id': drug.id,
            'drug_name': drug.drug_name,
            'generic_name': drug.generic_name,
            'therapeutic_class': drug.therapeutic_class
        }
    
    def get_pharmacy_info(self, pharmacy_id: UUID) -> Optional[dict]:
        """
        Get pharmacy information.
        
        Args:
            pharmacy_id: Pharmacy UUID
            
        Returns:
            Dictionary with pharmacy information or None
        """
        pharmacy = self.session.get(Pharmacy, pharmacy_id)
        if not pharmacy:
            return None
        
        return {
            'pharmacy_id': pharmacy.id,
            'pharmacy_name': pharmacy.name
        }
    
    def get_current_inventory(
        self,
        pharmacy_id: UUID,
        drug_id: Optional[UUID] = None
    ) -> list[dict]:
        """
        Get current inventory levels.
        
        Args:
            pharmacy_id: Pharmacy UUID
            drug_id: Optional drug UUID to filter
            
        Returns:
            List of inventory items
        """
        stmt = (
            select(PharmacyInventory, PharmacyCode)
            .join(PharmacyCode, PharmacyInventory.pharmacy_code_id == PharmacyCode.id)
            .where(
                and_(
                    PharmacyInventory.pharmacy_id == pharmacy_id,
                    PharmacyInventory.quantity_available > 0
                )
            )
        )
        
        if drug_id:
            stmt = stmt.where(PharmacyInventory.pharmacy_code_id == drug_id)
        
        results = self.session.exec(stmt).all()
        
        return [
            {
                'drug_id': code.id,
                'drug_name': code.drug_name,
                'quantity_available': inv.quantity_available,
                'unit_price': float(inv.unit_price),
                'expiry_date': inv.expiry_date
            }
            for inv, code in results
        ]
    
    def _fill_missing_dates(
        self,
        df: pd.DataFrame,
        start_date: datetime
    ) -> pd.DataFrame:
        """
        Fill missing dates in the DataFrame with 0 demand.
        Prophet requires continuous date series.
        """
        if df.empty:
            return self._create_empty_dataframe(start_date)
        
        # Create date range from start_date to today
        end_date = datetime.utcnow().date()
        date_range = pd.date_range(
            start=start_date.date() if isinstance(start_date, datetime) else start_date,
            end=end_date,
            freq='D'
        )
        
        # Create full date DataFrame
        full_df = pd.DataFrame({'ds': date_range})
        full_df['ds'] = full_df['ds'].dt.date
        
        # Ensure df['ds'] is also date type
        df['ds'] = pd.to_datetime(df['ds']).dt.date
        
        # Merge with original data
        merged = full_df.merge(df, on='ds', how='left')
        merged['y'] = merged['y'].fillna(0)
        
        # Convert ds back to datetime for Prophet
        merged['ds'] = pd.to_datetime(merged['ds'])
        
        return merged
    
    def _create_empty_dataframe(self, start_date: datetime) -> pd.DataFrame:
        """
        Create an empty DataFrame with date range filled with 0s.
        """
        end_date = datetime.utcnow().date()
        date_range = pd.date_range(
            start=start_date.date() if isinstance(start_date, datetime) else start_date,
            end=end_date,
            freq='D'
        )
        
        return pd.DataFrame({
            'ds': date_range,
            'y': [0.0] * len(date_range)
        })
    
    def get_prescription_demand_signal(
        self,
        drug_id: UUID,
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Get prescription data as a leading indicator of demand.
        Prescriptions typically precede orders.
        
        Args:
            drug_id: Drug/pharmacy_code UUID
            days_back: Number of days to look back
            
        Returns:
            DataFrame with prescription counts by date
        """
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        stmt = (
            select(
                func.date(Prescription.prescribed_date).label('prescription_date'),
                func.sum(PrescriptionItem.quantity).label('total_quantity')
            )
            .join(PrescriptionItem, Prescription.id == PrescriptionItem.prescription_id)
            .where(
                and_(
                    PrescriptionItem.pharmacy_code_id == drug_id,
                    Prescription.prescribed_date >= start_date.date(),
                    Prescription.status.in_(['ACTIVE', 'FILLED'])
                )
            )
            .group_by(func.date(Prescription.prescribed_date))
            .order_by(func.date(Prescription.prescribed_date))
        )
        
        results = self.session.exec(stmt).all()
        
        if not results:
            return self._create_empty_dataframe(start_date)
        
        df = pd.DataFrame([
            {'ds': row.prescription_date, 'y': float(row.total_quantity)}
            for row in results
        ])
        
        return self._fill_missing_dates(df, start_date)
    
    def calculate_demand_statistics(self, df: pd.DataFrame) -> dict:
        """
        Calculate basic statistics from demand data.
        
        Args:
            df: DataFrame with demand data
            
        Returns:
            Dictionary with statistics
        """
        if df.empty or df['y'].sum() == 0:
            return {
                'total_demand': 0,
                'average_daily_demand': 0,
                'std_daily_demand': 0,
                'max_daily_demand': 0,
                'min_daily_demand': 0,
                'days_with_demand': 0,
                'data_points': len(df)
            }
        
        return {
            'total_demand': float(df['y'].sum()),
            'average_daily_demand': float(df['y'].mean()),
            'std_daily_demand': float(df['y'].std()),
            'max_daily_demand': float(df['y'].max()),
            'min_daily_demand': float(df['y'].min()),
            'days_with_demand': int((df['y'] > 0).sum()),
            'data_points': len(df)
        }

