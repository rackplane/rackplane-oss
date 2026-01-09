#!/usr/bin/env python3
"""
Restore catalog_skus from a JSON backup file.

Usage:
    python scripts/restore_from_backup.py scripts/backups/services_catalog_skus_backup_YYYYMMDD_HHMMSS.json
    
    # Dry run first:
    python scripts/restore_from_backup.py --dry-run scripts/backups/services_catalog_skus_backup_YYYYMMDD_HHMMSS.json
"""

import os
import sys
import json
import argparse
import psycopg2
import psycopg2.extras
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def restore_from_backup(services_url: str, backup_file: str, dry_run: bool = False):
    """Restore catalog_skus from backup JSON file."""
    
    logger.info(f"Loading backup from: {backup_file}")
    with open(backup_file, 'r') as f:
        skus = json.load(f)
    
    logger.info(f"Loaded {len(skus)} SKUs from backup")
    
    if dry_run:
        logger.info("[DRY RUN] Would restore SKUs (no changes made)")
        return len(skus), 0
    
    conn = psycopg2.connect(services_url)
    cur = conn.cursor()
    
    restored = 0
    errors = 0
    
    for sku in skus:
        try:
            cur.execute("""
                INSERT INTO catalog_skus (
                    id, vendor, sku, part_number, name, manufacturer, asset_type,
                    price_usd, specifications, datasheet_url, vendor_url,
                    description, currency, compatibility, is_active,
                    created_at, updated_at
                ) VALUES (
                    %(id)s, %(vendor)s, %(sku)s, %(part_number)s, %(name)s, %(manufacturer)s,
                    %(asset_type)s, %(price_usd)s, %(specifications)s, %(datasheet_url)s,
                    %(vendor_url)s, %(description)s, %(currency)s, %(compatibility)s,
                    %(is_active)s, %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (vendor, sku) DO UPDATE SET
                    part_number = EXCLUDED.part_number,
                    name = EXCLUDED.name,
                    manufacturer = EXCLUDED.manufacturer,
                    asset_type = EXCLUDED.asset_type,
                    price_usd = EXCLUDED.price_usd,
                    specifications = EXCLUDED.specifications,
                    datasheet_url = EXCLUDED.datasheet_url,
                    vendor_url = EXCLUDED.vendor_url,
                    description = EXCLUDED.description,
                    currency = EXCLUDED.currency,
                    compatibility = EXCLUDED.compatibility,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
            """, {
                'id': sku.get('id'),
                'vendor': sku['vendor'],
                'sku': sku['sku'],
                'part_number': sku.get('part_number'),
                'name': sku['name'],
                'manufacturer': sku.get('manufacturer'),
                'asset_type': sku.get('asset_type'),
                'price_usd': sku.get('price_usd'),
                'specifications': psycopg2.extras.Json(sku.get('specifications')) if sku.get('specifications') else None,
                'datasheet_url': sku.get('datasheet_url'),
                'vendor_url': sku.get('vendor_url'),
                'description': sku.get('description'),
                'currency': sku.get('currency', 'USD'),
                'compatibility': psycopg2.extras.Json(sku.get('compatibility')) if sku.get('compatibility') else None,
                'is_active': sku.get('is_active', True),
                'created_at': sku.get('created_at'),
                'updated_at': sku.get('updated_at')
            })
            restored += 1
        except Exception as e:
            logger.error(f"Error restoring {sku.get('vendor')}:{sku.get('sku')}: {e}")
            errors += 1
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    return restored, errors


def main():
    parser = argparse.ArgumentParser(description='Restore catalog_skus from JSON backup')
    parser.add_argument('backup_file', help='Path to backup JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--services-url', help='Services DB URL (or set DATABASE_URL env var)')
    args = parser.parse_args()
    
    services_url = args.services_url or os.environ.get('DATABASE_URL')
    
    if not services_url:
        logger.error("DATABASE_URL not set. Use --services-url or set environment variable.")
        sys.exit(1)
    
    if not os.path.exists(args.backup_file):
        logger.error(f"Backup file not found: {args.backup_file}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Restore Catalog SKUs from Backup")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("*** DRY RUN MODE - No changes will be made ***")
    
    restored, errors = restore_from_backup(services_url, args.backup_file, args.dry_run)
    
    logger.info("\n" + "=" * 60)
    if args.dry_run:
        logger.info(f"DRY RUN: Would restore {restored} SKUs")
    else:
        logger.info(f"RESTORE COMPLETE:")
        logger.info(f"  Restored: {restored}")
        logger.info(f"  Errors: {errors}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
