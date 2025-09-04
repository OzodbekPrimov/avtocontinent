import csv
import os
from django.conf import settings
from pathlib import Path

CSV_FILE = Path(__file__).parent.parent.parent / 'manzillar.csv'

def load_delivery_data():
    """Load delivery data from CSV file"""
    if not CSV_FILE.exists():
        return {}, {}
    
    regions = {}  # region_name -> list of branches
    branches = {}  # branch_id -> branch_data
    
    with open(CSV_FILE, 'r', encoding='utf-8') as file:
        # Skip the header row
        next(file)
        reader = csv.reader(file, delimiter=';')
        
        for row in reader:
            if len(row) < 7:  # Skip incomplete rows
                continue
            
            try:
                # Extract data from CSV
                branch_id = row[0].strip()  # №
                region_name = row[1].strip()  # Область
                branch_name = row[2].strip()  # ФИЛИАЛ
                address = row[3].strip()  # АДРЕС
                phone = row[4].strip()  # ТЕЛЕФОН
                landmark = row[5].strip()  # ОРИЕНТИР
                city_district = row[6].strip()  # Город / Район
                
                # Delivery time (only office delivery time needed since home delivery removed)
                delivery_time = row[8].strip() if len(row) > 8 else ''  # Срок доставки до офиса
                
                # Create branch data
                branch_data = {
                    'id': branch_id,
                    'region': region_name,
                    'name': branch_name,
                    'address': address,
                    'phone': phone,
                    'landmark': landmark,
                    'city_district': city_district,
                    'office_delivery_time': delivery_time,
                }
                
                # Add to regions dict
                if region_name not in regions:
                    regions[region_name] = []
                regions[region_name].append(branch_data)
                
                # Add to branches dict
                branches[branch_id] = branch_data
                
            except Exception as e:
                # Skip problematic rows
                continue
    
    return regions, branches


def get_regions():
    """Get all unique regions"""
    regions, _ = load_delivery_data()
    return [{'id': i+1, 'name': region} for i, region in enumerate(sorted(regions.keys()))]


def get_branches(region=None):
    """Get branches, optionally filtered by region - kept for backward compatibility"""
    if region:
        return get_branches_by_region(region)
    
    # Return all branches
    _, branches = load_delivery_data()
    return list(branches.values())


def get_branches_by_region(region_name):
    """Get all branches for a specific region"""
    regions, _ = load_delivery_data()
    return regions.get(region_name, [])


def get_branch_by_id(branch_id):
    """Get branch details by ID"""
    _, branches = load_delivery_data()
    return branches.get(str(branch_id))
