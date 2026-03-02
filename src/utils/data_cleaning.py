"""
Utility functions for data cleaning and preprocessing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime


class DataCleaner:
    """
    Data cleaning and preprocessing utilities for real estate data
    """
    
    def __init__(self):
        self.city_mapping = {
            'nicosia': 'Nicosia',
            'lefkosia': 'Nicosia',
            'λευκωσία': 'Nicosia',
            'limassol': 'Limassol',
            'lemesos': 'Limassol',
            'λεμεσός': 'Limassol',
            'larnaca': 'Larnaca',
            'larnaka': 'Larnaca',
            'λάρνακα': 'Larnaca',
            'paphos': 'Paphos',
            'pafos': 'Paphos',
            'πάφος': 'Paphos',
            'famagusta': 'Famagusta',
            'ammochostos': 'Famagusta',
            'αμμόχωστος': 'Famagusta'
        }
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all cleaning operations to a DataFrame
        
        Args:
            df: Raw property data DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        
        # Remove duplicates
        df = self._remove_duplicates(df)
        
        # Standardize columns
        df = self._standardize_cities(df)
        df = self._clean_price(df)
        df = self._clean_numeric_columns(df)
        
        # Handle missing values
        df = self._handle_missing_values(df)
        
        # Remove outliers
        df = self._remove_price_outliers(df)
        df = self._remove_size_outliers(df)
        
        # Add derived features
        df = self._add_derived_features(df)
        
        return df
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate property listings"""
        # First, try exact duplicates based on source and external_id
        df = df.drop_duplicates(subset=['source', 'external_id'], keep='last')
        
        # Then, check for near-duplicates (same property on different sites)
        # based on similar title, price, and location
        print(f"Removed {len(df) - len(df)} duplicates")
        return df
    
    def _standardize_cities(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize city names"""
        if 'city' in df.columns:
            df['city'] = df['city'].str.lower().str.strip()
            df['city'] = df['city'].map(lambda x: self.city_mapping.get(x, x.title() if pd.notna(x) else x))
        return df
    
    def _clean_price(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate price data"""
        if 'price' not in df.columns:
            return df
        
        # Convert to numeric
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        # Remove invalid prices
        df = df[df['price'] > 0]
        
        return df
    
    def _clean_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean numeric columns"""
        numeric_cols = ['size_sqm', 'bedrooms', 'bathrooms', 'year_built', 'floor_level']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Validate ranges
                if col == 'bedrooms':
                    df.loc[df[col] > 20, col] = np.nan
                elif col == 'bathrooms':
                    df.loc[df[col] > 15, col] = np.nan
                elif col == 'year_built':
                    current_year = datetime.now().year
                    df.loc[(df[col] < 1900) | (df[col] > current_year + 2), col] = np.nan
                elif col == 'size_sqm':
                    df.loc[(df[col] < 10) | (df[col] > 10000), col] = np.nan
        
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values appropriately"""
        # For boolean columns, fill with False
        boolean_cols = [col for col in df.columns if col.startswith('has_') or col.startswith('is_')]
        for col in boolean_cols:
            if col in df.columns:
                df[col] = df[col].fillna(False)
        
        # For categorical columns, fill with 'unknown' or mode
        if 'property_type' in df.columns:
            df['property_type'] = df['property_type'].fillna('unknown')
        
        # For numeric columns, decide on strategy
        # - Don't impute price, size_sqm (critical for analysis)
        # - Can impute bedrooms/bathrooms with median by property_type
        
        return df
    
    def _remove_price_outliers(self, df: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
        """
        Remove price outliers using IQR method
        
        Args:
            df: DataFrame
            threshold: IQR multiplier
        """
        if 'price' not in df.columns:
            return df
        
        Q1 = df['price'].quantile(0.25)
        Q3 = df['price'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        before = len(df)
        df = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)]
        after = len(df)
        
        print(f"Removed {before - after} price outliers")
        return df
    
    def _remove_size_outliers(self, df: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
        """Remove size outliers using IQR method"""
        if 'size_sqm' not in df.columns:
            return df
        
        Q1 = df['size_sqm'].quantile(0.25)
        Q3 = df['size_sqm'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        before = len(df)
        df = df[(df['size_sqm'] >= lower_bound) & (df['size_sqm'] <= upper_bound)]
        after = len(df)
        
        print(f"Removed {before - after} size outliers")
        return df
    
    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived features"""
        # Price per square meter
        if 'price' in df.columns and 'size_sqm' in df.columns:
            df['price_per_sqm'] = df['price'] / df['size_sqm']
            df['price_per_sqm'] = df['price_per_sqm'].round(2)
        
        # Property age
        if 'year_built' in df.columns:
            current_year = datetime.now().year
            df['property_age'] = current_year - df['year_built']
        
        # Total rooms
        if 'bedrooms' in df.columns and 'bathrooms' in df.columns:
            df['total_rooms'] = df['bedrooms'] + df['bathrooms']
        
        return df
    
    def get_data_quality_report(self, df: pd.DataFrame) -> Dict:
        """
        Generate data quality report
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with quality metrics
        """
        report = {
            'total_records': len(df),
            'missing_values': {},
            'completeness': {},
            'duplicates': 0,
            'outliers': {}
        }
        
        # Missing values
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_pct = (missing_count / len(df)) * 100
            report['missing_values'][col] = missing_count
            report['completeness'][col] = f"{100 - missing_pct:.1f}%"
        
        # Duplicates
        report['duplicates'] = df.duplicated().sum()
        
        return report
    
    def merge_sources(self, df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        """
        Merge property data from multiple sources
        
        Args:
            df1: First DataFrame
            df2: Second DataFrame
            
        Returns:
            Merged DataFrame with duplicates handled
        """
        # Concatenate
        merged = pd.concat([df1, df2], ignore_index=True)
        
        # Remove exact duplicates
        merged = merged.drop_duplicates(subset=['source', 'external_id'], keep='last')
        
        return merged


def load_json_to_dataframe(json_file: str) -> pd.DataFrame:
    """Load JSON file to DataFrame"""
    import json
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return pd.DataFrame(data)


def save_cleaned_data(df: pd.DataFrame, output_path: str):
    """Save cleaned DataFrame"""
    if output_path.endswith('.csv'):
        df.to_csv(output_path, index=False)
    elif output_path.endswith('.json'):
        df.to_json(output_path, orient='records', indent=2)
    elif output_path.endswith('.parquet'):
        df.to_parquet(output_path, index=False)
    
    print(f"Saved {len(df)} records to {output_path}")


def main():
    """Example usage"""
    # Load data
    bazaraki_df = load_json_to_dataframe('data/raw/bazaraki_properties.json')
    spitogatos_df = load_json_to_dataframe('data/raw/spitogatos_properties.json')
    
    # Initialize cleaner
    cleaner = DataCleaner()
    
    # Clean each dataset
    print("Cleaning Bazaraki data...")
    bazaraki_clean = cleaner.clean_dataframe(bazaraki_df)
    
    print("\nCleaning Spitogatos data...")
    spitogatos_clean = cleaner.clean_dataframe(spitogatos_df)
    
    # Merge
    print("\nMerging datasets...")
    merged = cleaner.merge_sources(bazaraki_clean, spitogatos_clean)
    
    # Generate quality report
    print("\nData Quality Report:")
    report = cleaner.get_data_quality_report(merged)
    print(f"Total records: {report['total_records']}")
    print(f"Duplicates: {report['duplicates']}")
    
    # Save
    save_cleaned_data(merged, 'data/processed/properties_cleaned.csv')
    print("\nData cleaning completed!")


if __name__ == "__main__":
    main()
