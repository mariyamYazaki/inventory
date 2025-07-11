# services/OEM_project.py
import pandas as pd
import os
from typing import List, Dict, Optional

# services/OEM_project.py - Final Production-Grade Solution

class OEMMapper:
    # Plant to Business Unit mapping
    _PLANT_TO_BU = {
        'YMO': 'MA10',
        'YMM': 'MA13',
        'YMM2': 'MA15',
        'YMK': 'MA11',
        'YMOK': 'MA14'
    }

    @classmethod
    def _explode_combined_plants(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Handle plants separated by / (creates multiple rows)"""
        if 'Plants' not in df.columns:
            return df
            
        # Split and explode plants
        df['Plants'] = df['Plants'].str.split('/')
        df = df.explode('Plants')
        
        # Clean plant codes
        df['Plants'] = (
            df['Plants']
            .str.strip()
            .str.upper()
            .replace(['', 'NAN', 'NONE'], pd.NA)
        )
        
        return df.dropna(subset=['Plants'])

    @classmethod
    def _explode_projects(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Handle projects separated by ; (creates multiple rows)"""
        if 'Project' not in df.columns:
            return df
            
        # Split and clean projects
        df['Project'] = (
            df['Project']
            .str.split(';')
            .apply(lambda x: [p.strip() for p in x if p.strip()] if isinstance(x, list) else x)
        )
        
        # Explode into multiple rows
        df = df.explode('Project')
        return df.dropna(subset=['Project'])

    @classmethod
    def load_project_oem_mappings(cls) -> pd.DataFrame:
        """Production-grade loading with complete handling of combined plants/projects"""
        try:
            # Load All PNs file
            all_pns = pd.read_excel(
                "data/project_mapping/All PNs with project & OEM.xlsx",
                dtype={'Material': str}
            ).rename(columns=lambda x: 'Project' if 'project' in str(x).lower() else x)
            
            # Handle combined plants
            all_pns = cls._explode_combined_plants(all_pns)
            
            # Add BU mapping
            all_pns['BusinessUnit'] = all_pns['Plants'].map(cls._PLANT_TO_BU)
            
            # Load detailed OEM file
            oem_details = pd.read_excel(
                "data/project_mapping/PN with Project & OEM.xlsx",
                dtype={'Material': str}
            ).rename(columns={
                'Plant': 'Plants',
                'Material Number': 'Material'
            })
            
            oem_details = cls._explode_combined_plants(oem_details)
            oem_details['BusinessUnit'] = oem_details['Plants'].map(cls._PLANT_TO_BU)
            
            # Merge datasets
            merged = pd.merge(
                all_pns,
                oem_details,
                on=['Material', 'BusinessUnit'],
                how='left',
                suffixes=('', '_detail')
            )
            
            # Handle combined projects
            merged = cls._explode_projects(merged)
            
            # Final cleaning
            merged = merged[~merged['Project'].str.startswith('UNKNOWN', na=False)]
            merged['Material'] = merged['Material'].str.strip().str.upper()
            
            return merged.drop_duplicates().reset_index(drop=True)
            
        except Exception as e:
            error_msg = f"""
            Failed to load OEM mappings:
            - File paths: {os.listdir('data/project_mapping')}
            - Error: {str(e)}
            """
            raise ValueError(error_msg)

    @classmethod
    def get_plant_bu_mapping(cls, plant_code: str) -> str:
        """Safe lookup with combined plant handling"""
        if pd.isna(plant_code) or not isinstance(plant_code, str):
            return plant_code
            
        plant_code = plant_code.strip().upper()
        
        # Handle combined plants
        if '/' in plant_code:
            plants = [p.strip() for p in plant_code.split('/')]
            return '/'.join(cls._PLANT_TO_BU.get(p, p) for p in plants)
            
        return cls._PLANT_TO_BU.get(plant_code, plant_code)