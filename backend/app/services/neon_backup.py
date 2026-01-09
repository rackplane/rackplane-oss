# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Neon Backup Service

Handles backup writes to Neon PostgreSQL for critical customer data.
"""

import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional
from app.core.config import settings


def get_neon_connection():
    """Get a connection to Neon backup database."""
    if not settings.NEON_DB_URL:
        return None
    try:
        return psycopg2.connect(settings.NEON_DB_URL)
    except Exception as e:
        print(f"Neon connection failed: {e}")
        return None


def backup_api_customer(customer_data: Dict[str, Any]) -> bool:
    """
    Backup an API customer to Neon.
    
    Args:
        customer_data: Dict with customer fields (api_key_hash, customer_name, etc.)
    
    Returns:
        True if backup succeeded, False otherwise
    """
    conn = get_neon_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO api_customers (
                api_key_hash, customer_name, email, company, tier,
                is_active, rate_limit_hour, created_at, expires_at,
                customer_metadata, contribution_count, contributor_since,
                is_lifetime_contributor, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (api_key_hash) DO UPDATE SET
                customer_name = EXCLUDED.customer_name,
                email = EXCLUDED.email,
                company = EXCLUDED.company,
                tier = EXCLUDED.tier,
                is_active = EXCLUDED.is_active,
                rate_limit_hour = EXCLUDED.rate_limit_hour,
                expires_at = EXCLUDED.expires_at,
                customer_metadata = EXCLUDED.customer_metadata,
                contribution_count = EXCLUDED.contribution_count,
                contributor_since = EXCLUDED.contributor_since,
                is_lifetime_contributor = EXCLUDED.is_lifetime_contributor,
                updated_at = NOW()
        """, (
            customer_data.get('api_key_hash'),
            customer_data.get('customer_name'),
            customer_data.get('email'),
            customer_data.get('company'),
            customer_data.get('tier', 'free'),
            customer_data.get('is_active', True),
            customer_data.get('rate_limit_hour', 100),
            customer_data.get('created_at'),
            customer_data.get('expires_at'),
            psycopg2.extras.Json(customer_data.get('customer_metadata', {})),
            customer_data.get('contribution_count', 0),
            customer_data.get('contributor_since'),
            customer_data.get('is_lifetime_contributor', False)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Neon backup_api_customer failed: {e}")
        conn.rollback()
        conn.close()
        return False


def backup_catalog_sku(sku_data: Dict[str, Any]) -> bool:
    """
    Backup a catalog SKU to Neon.
    
    Args:
        sku_data: Dict with SKU fields (vendor, sku, name, vendor_url, etc.)
    
    Returns:
        True if backup succeeded, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    conn = get_neon_connection()
    if not conn:
        logger.warning(f"Neon backup: no connection for {sku_data.get('sku')}")
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO catalog_skus (
                vendor, sku, part_number, name, manufacturer, asset_type,
                price_usd, specifications, vendor_url, datasheet_url,
                description, currency, compatibility, is_active, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (vendor, sku) DO UPDATE SET
                part_number = EXCLUDED.part_number,
                name = EXCLUDED.name,
                manufacturer = EXCLUDED.manufacturer,
                asset_type = EXCLUDED.asset_type,
                price_usd = EXCLUDED.price_usd,
                specifications = EXCLUDED.specifications,
                vendor_url = EXCLUDED.vendor_url,
                datasheet_url = EXCLUDED.datasheet_url,
                description = EXCLUDED.description,
                currency = EXCLUDED.currency,
                compatibility = EXCLUDED.compatibility,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, (
            sku_data.get('vendor'),
            sku_data.get('sku'),
            sku_data.get('part_number'),
            sku_data.get('name'),
            sku_data.get('manufacturer'),
            sku_data.get('asset_type'),
            sku_data.get('price_usd'),
            psycopg2.extras.Json(sku_data.get('specifications', {})) if sku_data.get('specifications') else None,
            sku_data.get('vendor_url'),
            sku_data.get('datasheet_url'),
            sku_data.get('description'),
            sku_data.get('currency', 'USD'),
            psycopg2.extras.Json(sku_data.get('compatibility', {})) if sku_data.get('compatibility') else None,
            sku_data.get('is_active', True)
        ))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Neon backup: wrote {sku_data.get('vendor')}:{sku_data.get('sku')}")
        return True
    except Exception as e:
        logger.warning(f"Neon backup_catalog_sku failed: {e}")
        conn.rollback()
        conn.close()
        return False


def sync_all_customers_to_neon(db_session) -> int:
    """
    Sync all API customers from primary database to Neon.
    
    Args:
        db_session: SQLAlchemy session to primary database
    
    Returns:
        Number of customers synced
    """
    from app.models.api_customer import ApiCustomer
    
    customers = db_session.query(ApiCustomer).all()
    synced = 0
    
    for customer in customers:
        data = {
            'api_key_hash': customer.api_key_hash,
            'customer_name': customer.customer_name,
            'email': customer.email,
            'company': customer.company,
            'tier': customer.tier,
            'is_active': customer.is_active,
            'rate_limit_hour': customer.rate_limit_hour,
            'created_at': customer.created_at,
            'expires_at': customer.expires_at,
            'customer_metadata': customer.customer_metadata,
            'contribution_count': customer.contribution_count,
            'contributor_since': customer.contributor_since,
            'is_lifetime_contributor': customer.is_lifetime_contributor
        }
        if backup_api_customer(data):
            synced += 1
    
    return synced


def sync_all_skus_to_neon(db_session) -> int:
    """
    Sync all catalog SKUs from primary database to Neon.
    
    This is used for bulk backup/disaster recovery sync.
    Individual SKU backups happen via backup_catalog_sku when items are added.
    
    Args:
        db_session: SQLAlchemy session to primary database
    
    Returns:
        Number of SKUs synced
    """
    import logging
    logger = logging.getLogger(__name__)
    from app.models.catalog_sku import CatalogSKU
    
    skus = db_session.query(CatalogSKU).all()
    synced = 0
    errors = 0
    
    logger.info(f"Starting bulk sync of {len(skus)} SKUs to Neon...")
    
    for sku in skus:
        data = {
            'vendor': sku.vendor,
            'sku': sku.sku,
            'part_number': sku.part_number,
            'name': sku.name,
            'manufacturer': sku.manufacturer,
            'asset_type': sku.asset_type,
            'price_usd': float(sku.price_usd) if sku.price_usd else None,
            'specifications': sku.specifications,
            'vendor_url': sku.vendor_url,
            'datasheet_url': sku.datasheet_url,
            'description': sku.description,
            'currency': sku.currency,
            'compatibility': sku.compatibility,
            'is_active': sku.is_active
        }
        if backup_catalog_sku(data):
            synced += 1
        else:
            errors += 1
        
        if synced % 100 == 0 and synced > 0:
            logger.info(f"  Synced {synced} SKUs...")
    
    logger.info(f"Bulk sync complete: {synced} synced, {errors} errors")
    return synced
