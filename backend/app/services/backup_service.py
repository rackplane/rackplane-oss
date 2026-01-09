# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0


"""
Database Backup and Restore Service
Provides comprehensive export/import functionality for all database tables
"""

from sqlalchemy.orm import Session
from sqlalchemy import inspect
from datetime import datetime
import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.core.config import settings

# Core models (always required)
from app.models.asset import Asset, AssetLifecycleEvent
from app.models.location import Datacenter, Room, Rack, RackPosition
from app.models.maintenance import MaintenanceRecord, MaintenancePrediction
from app.models.storage_container import StorageContainer
from app.models.container_stock_threshold import ContainerStockThreshold
from app.models.asset_type import AssetTypeModel
from app.models.network_cable import NetworkCable
from app.models.power_cable import PowerCable
from app.models.environment import Environment
from app.models.tenant import Tenant
from app.models.user import User
from app.models.audit_log import AuditLog

# Optional models (may not exist in all codebases)
# Track which models are missing for user warnings
MISSING_MODELS = []

try:
    from app.models.network import NetworkPort, NetworkConnection, VLAN
except ImportError:
    NetworkPort = None
    NetworkConnection = None
    VLAN = None
    MISSING_MODELS.extend(['NetworkPort', 'NetworkConnection', 'VLAN'])

try:
    from app.models.workflow import Workflow, WorkflowStep, WorkflowExecution
except ImportError:
    Workflow = None
    WorkflowStep = None
    WorkflowExecution = None
    MISSING_MODELS.extend(['Workflow', 'WorkflowStep', 'WorkflowExecution'])

try:
    from app.models.environmental import EnvironmentalSensor, EnvironmentalReading
except ImportError:
    EnvironmentalSensor = None
    EnvironmentalReading = None
    MISSING_MODELS.extend(['EnvironmentalSensor', 'EnvironmentalReading'])

try:
    from app.models.capacity import CapacityMetrics, PowerMetrics, CoolingMetrics
except ImportError:
    CapacityMetrics = None
    PowerMetrics = None
    CoolingMetrics = None
    MISSING_MODELS.extend(['CapacityMetrics', 'PowerMetrics', 'CoolingMetrics'])

try:
    from app.models.connections import Connection
except ImportError:
    Connection = None
    MISSING_MODELS.append('Connection')

try:
    from app.models.api_key import ApiKey
except ImportError:
    ApiKey = None
    MISSING_MODELS.append('ApiKey')

try:
    from app.models.print_job import PrintJob, PrintAgent
except ImportError:
    PrintJob = None
    PrintAgent = None
    MISSING_MODELS.extend(['PrintJob', 'PrintAgent'])

try:
    from app.models.vendor_sku import VendorSKU
except ImportError:
    VendorSKU = None
    MISSING_MODELS.append('VendorSKU')

# Warn user about missing models at module load time
if MISSING_MODELS:
    import warnings
    warnings.warn(
        f"⚠️  BACKUP SERVICE: {len(MISSING_MODELS)} optional model(s) not found: {', '.join(MISSING_MODELS)}\n"
        f"   These tables will NOT be backed up or restored:\n"
        f"   - Tables: {', '.join([m.lower().replace('_', '_') for m in MISSING_MODELS])}\n"
        f"   - This is normal if using an older codebase version.\n"
        f"   - Backups from newer codebases may contain data for these tables that will be skipped during restore.",
        UserWarning,
        stacklevel=2
    )


def _build_table_order():
    """
    Build TABLE_ORDER dynamically based on available models.
    This allows the backup service to work with codebases that don't have all models.
    """
    table_order = [
        # First: Core tenant/user tables (no dependencies, but everything depends on them)
        {'model': Tenant, 'name': 'tenants'},
        {'model': User, 'name': 'users'},
        
        # Second: Independent tables (no foreign keys except tenant_id)
        {'model': AssetTypeModel, 'name': 'asset_types'},
        {'model': Datacenter, 'name': 'datacenters'},
    ]
    
    # Add optional models if they exist
    if VendorSKU is not None:
        table_order.append({'model': VendorSKU, 'name': 'vendor_skus'})
    if PrintAgent is not None:
        table_order.append({'model': PrintAgent, 'name': 'print_agents'})
    
    # Third: Tables that depend on users
    if ApiKey is not None:
        table_order.append({'model': ApiKey, 'name': 'api_keys'})

    # Fourth: Tables with foreign keys to datacenters
    table_order.extend([
        {'model': Room, 'name': 'rooms'},
        {'model': Rack, 'name': 'racks'},
        {'model': StorageContainer, 'name': 'storage_containers'},
        {'model': Environment, 'name': 'environments'},
    ])
    
    if VLAN is not None:
        table_order.append({'model': VLAN, 'name': 'vlans'})

    # Fifth: Tables that depend on storage_containers
    table_order.append({'model': ContainerStockThreshold, 'name': 'container_stock_thresholds'})

    # Sixth: Tables that depend on datacenter/room/rack
    if EnvironmentalSensor is not None:
        table_order.append({'model': EnvironmentalSensor, 'name': 'environmental_sensors'})
    if CapacityMetrics is not None:
        table_order.append({'model': CapacityMetrics, 'name': 'capacity_metrics'})
    if PowerMetrics is not None:
        table_order.append({'model': PowerMetrics, 'name': 'power_metrics'})
    if CoolingMetrics is not None:
        table_order.append({'model': CoolingMetrics, 'name': 'cooling_metrics'})

    # Seventh: Assets (depends on datacenters, racks, storage_containers)
    table_order.append({'model': Asset, 'name': 'assets'})

    # Eighth: Tables with foreign keys to assets
    table_order.extend([
        {'model': AssetLifecycleEvent, 'name': 'asset_lifecycle_events'},
        {'model': MaintenanceRecord, 'name': 'maintenance_records'},
        {'model': MaintenancePrediction, 'name': 'maintenance_predictions'},
    ])
    
    if NetworkPort is not None:
        table_order.append({'model': NetworkPort, 'name': 'network_ports'})
    
    table_order.append({'model': RackPosition, 'name': 'rack_positions'})
    
    if Connection is not None:
        table_order.append({'model': Connection, 'name': 'connections'})
    if EnvironmentalReading is not None:
        table_order.append({'model': EnvironmentalReading, 'name': 'environmental_readings'})

    # Ninth: Tables that depend on network_ports
    if NetworkConnection is not None:
        table_order.append({'model': NetworkConnection, 'name': 'network_connections'})

    # Tenth: Tables that depend on assets/storage_containers/racks/users
    if PrintJob is not None:
        table_order.append({'model': PrintJob, 'name': 'print_jobs'})

    # Eleventh: Workflow tables
    if Workflow is not None:
        table_order.append({'model': Workflow, 'name': 'workflows'})
    if WorkflowExecution is not None:
        table_order.append({'model': WorkflowExecution, 'name': 'workflow_executions'})
    if WorkflowStep is not None:
        table_order.append({'model': WorkflowStep, 'name': 'workflow_steps'})

    # Twelfth: Cable tables
    table_order.extend([
        {'model': NetworkCable, 'name': 'network_cables'},
        {'model': PowerCable, 'name': 'power_cables'},
    ])
    
    # Last: Audit logs
    table_order.append({'model': AuditLog, 'name': 'audit_logs'})
    
    return table_order


def _load_critical_constraints() -> Dict[str, Dict]:
    """
    Load the 15 critical constraints from the verification script.
    This ensures the backup service uses the same constraint definitions.
    """
    try:
        # Try to import from the scripts directory
        # __file__ is /app/app/services/backup_service.py, so parent.parent is /app
        backend_dir = Path(__file__).parent.parent
        verify_script = backend_dir / "scripts" / "verify_constraints_after_migration.py"
        
        if not verify_script.exists():
            # Try alternative path (if running from different location)
            verify_script = Path("/app/scripts/verify_constraints_after_migration.py")
        
        if verify_script.exists():
            # Read and execute the script to get CRITICAL_CONSTRAINTS
            with open(verify_script, 'r') as f:
                content = f.read()
            
            # Extract CRITICAL_CONSTRAINTS dict
            # Find the dict definition
            start = content.find('CRITICAL_CONSTRAINTS = {')
            if start == -1:
                return {}
            
            # Find the matching closing brace (need to handle nested dicts)
            brace_count = 0
            end = start
            in_string = False
            string_char = None
            
            for i, char in enumerate(content[start:], start):
                # Handle string literals (don't count braces inside strings)
                if char in ('"', "'") and (i == start or content[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
            
            if brace_count != 0:
                # Didn't find matching brace, return empty
                return {}
            
            # Execute the dict definition
            constraints_code = content[start:end]
            # Create a safe namespace
            namespace = {}
            # Import necessary modules for exec
            exec(constraints_code, {'Path': Path, '__name__': '__main__'}, namespace)
            return namespace.get('CRITICAL_CONSTRAINTS', {})
    except Exception as e:
        import traceback
        print(f"Warning: Could not load critical constraints: {e}")
        print(traceback.format_exc())
        return {}
    
    return {}


def _check_duplicate_by_constraints(
    db: Session,
    model,
    table_name: str,
    record_data: Dict,
    constraints: Dict[str, Dict]
) -> Optional[Any]:
    """
    Check if a record would violate any of the 15 critical constraints.
    
    Returns the existing record if a duplicate is found, None otherwise.
    
    This function uses the same constraint definitions as verify_constraints_after_migration.py
    to ensure consistency between database constraints and backup/restore duplicate detection.
    """
    # Find all constraints that apply to this table
    table_constraints = {
        name: info for name, info in constraints.items()
        if info.get('table') == table_name
    }
    
    if not table_constraints:
        return None
    
    # Check each constraint for this table
    for constraint_name, constraint_info in table_constraints.items():
        columns = constraint_info.get('columns', [])
        
        # Build filter based on constraint columns
        # Only check constraints where we have non-None values for all required columns
        filters = []
        has_all_values = True
        
        for col in columns:
            value = record_data.get(col)
            if value is None:
                # If any required column is None, skip this constraint
                # (e.g., hostname might be None for some assets)
                has_all_values = False
                break
            
            if hasattr(model, col):
                filters.append(getattr(model, col) == value)
            else:
                # Column doesn't exist on model, skip this constraint
                has_all_values = False
                break
        
        # Only check if we have values for all columns in the constraint
        if has_all_values and len(filters) == len(columns):
            existing = db.query(model).execution_options(skip_tenant_filter=True).filter(*filters).first()
            if existing:
                return existing
    
    return None


class BackupService:
    """Service for backing up and restoring database"""

    # Define the order of tables for backup/restore (respecting foreign keys)
    # IMPORTANT: Order matters for deletion - delete child tables before parent tables
    # For import: parents before children (tenants before audit_logs)
    # For deletion: reversed order (children before parents, so audit_logs before tenants)
    # Built dynamically to support codebases with different model sets
    TABLE_ORDER = _build_table_order()

    @staticmethod
    def serialize_value(value: Any) -> Any:
        """Convert a value to JSON-serializable format"""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (list, dict)):
            return value
        elif hasattr(value, 'value'):  # Handle Enum types
            return value.value
        elif hasattr(value, '__dict__'):
            return str(value)
        return value

    @staticmethod
    def export_database(db: Session, skip_tenant_filter: bool = False) -> Dict[str, Any]:
        """
        Export entire database to a dictionary
        Returns a complete backup of all tables with metadata
        
        Args:
            db: Database session
            skip_tenant_filter: If True, bypass tenant filtering (for super admin exports)
        """
        # Warn about missing models
        if MISSING_MODELS:
            missing_tables = []
            for model_name in MISSING_MODELS:
                # Convert model name to table name
                if model_name == 'NetworkPort':
                    missing_tables.append('network_ports')
                elif model_name == 'NetworkConnection':
                    missing_tables.append('network_connections')
                elif model_name == 'VLAN':
                    missing_tables.append('vlans')
                elif model_name == 'Workflow':
                    missing_tables.append('workflows')
                elif model_name == 'WorkflowStep':
                    missing_tables.append('workflow_steps')
                elif model_name == 'WorkflowExecution':
                    missing_tables.append('workflow_executions')
                elif model_name == 'EnvironmentalSensor':
                    missing_tables.append('environmental_sensors')
                elif model_name == 'EnvironmentalReading':
                    missing_tables.append('environmental_readings')
                elif model_name == 'CapacityMetrics':
                    missing_tables.append('capacity_metrics')
                elif model_name == 'PowerMetrics':
                    missing_tables.append('power_metrics')
                elif model_name == 'CoolingMetrics':
                    missing_tables.append('cooling_metrics')
                elif model_name == 'Connection':
                    missing_tables.append('connections')
                elif model_name == 'ApiKey':
                    missing_tables.append('api_keys')
                elif model_name == 'PrintJob':
                    missing_tables.append('print_jobs')
                elif model_name == 'PrintAgent':
                    missing_tables.append('print_agents')
                elif model_name == 'VendorSKU':
                    missing_tables.append('vendor_skus')
            
            print(f"\n⚠️  WARNING: {len(MISSING_MODELS)} optional model(s) not available in this codebase:")
            print(f"   Missing models: {', '.join(MISSING_MODELS)}")
            print(f"   Tables NOT being backed up: {', '.join(missing_tables)}")
            print(f"   This backup will NOT include data from these tables.")
            print(f"   If restoring to a newer codebase, data for these tables will be missing.\n")
        
        backup_data = {
            'metadata': {
                'backup_date': datetime.utcnow().isoformat(),
                'version': '1.0',
                'description': 'Full database backup for DCMS',
                'missing_models': MISSING_MODELS if MISSING_MODELS else None,
                'codebase_version': 'partial' if MISSING_MODELS else 'full',
            },
            'tables': {},
        }

        for table_info in BackupService.TABLE_ORDER:
            model = table_info['model']
            table_name = table_info['name']

            try:
                # Query all records from this table
                # Use skip_tenant_filter for super admin exports to get all tenants' data
                # Special handling for tenants table: only include user's tenant for tenant-scoped exports
                if table_name == 'tenants' and not skip_tenant_filter:
                    # For tenant-scoped exports, only include the current tenant
                    # Get tenant_id from current context
                    from app.core.tenant import get_current_tenant_id
                    tenant_id = get_current_tenant_id()
                    if tenant_id:
                        query = db.query(model).execution_options(skip_tenant_filter=True).filter(
                            model.id == tenant_id
                        )
                        records = query.all()
                    else:
                        # No tenant context - skip tenants table for safety
                        records = []
                # Special handling for vendor_skus: always include sample SKUs (tenant_id=0, is_sample=True)
                elif table_name == 'vendor_skus' and not skip_tenant_filter:
                    # Try to get customer SKUs (tenant-scoped)
                    # If no tenant context is set, this will fail, so we'll catch and use skip_tenant_filter
                    customer_records = []
                    try:
                        customer_query = db.query(model)
                        customer_records = customer_query.all()
                    except ValueError:
                        # No tenant context set, skip customer SKUs for this export
                        # (They'll be included when tenant context is properly set)
                        pass
                    
                    # Get sample SKUs (tenant_id=0, is_sample=True) - always include these
                    sample_query = db.query(model).execution_options(skip_tenant_filter=True).filter(
                        model.tenant_id == 0,
                        model.is_sample == True
                    )
                    sample_records = sample_query.all()
                    
                    # Combine both sets
                    records = list(customer_records) + list(sample_records)
                else:
                    query = db.query(model)
                    if skip_tenant_filter:
                        query = query.execution_options(skip_tenant_filter=True)
                    records = query.all()
                if table_name == 'assets':
                    print(f"DEBUG: Exporting assets. skip_tenant_filter={skip_tenant_filter}, count={len(records)}")
                    if not records:
                        print(f"DEBUG: No assets found! Checking direct query...")
                        direct_count = db.query(model).execution_options(skip_tenant_filter=True).count()
                        print(f"DEBUG: Direct query count (skip_tenant_filter=True): {direct_count}")

                # Get column names
                mapper = inspect(model)
                columns = [column.key for column in mapper.columns]

                # Serialize records
                serialized_records = []
                for record in records:
                    record_dict = {}
                    for col in columns:
                        value = getattr(record, col)
                        # Special handling for photo_urls: convert MinIO URLs to base64 for backup
                        if col == 'photo_urls' and value and isinstance(value, list):
                            value = BackupService._convert_photos_to_base64(value, db)
                        record_dict[col] = BackupService.serialize_value(value)
                    serialized_records.append(record_dict)

                backup_data['tables'][table_name] = {
                    'count': len(serialized_records),
                    'columns': columns,
                    'data': serialized_records
                }

                print(f"✓ Exported {len(serialized_records)} records from {table_name}")

            except Exception as e:
                print(f"⚠ Warning: Could not export {table_name}: {str(e)}")
                backup_data['tables'][table_name] = {
                    'count': 0,
                    'error': str(e),
                    'data': []
                }

        return backup_data

    @staticmethod
    def import_database(db: Session, backup_data: Dict[str, Any], clear_existing: bool = False) -> Dict[str, Any]:
        """
        Import database from backup data
        
        Uses the 15 critical constraints from verify_constraints_after_migration.py
        to check for duplicates before inserting records.
        
        Args:
            db: Database session
            backup_data: Backup data dictionary
            clear_existing: If True, delete existing data before import

        Returns:
            Dictionary with import statistics
        """
        # Load the 15 critical constraints - source of truth for duplicate detection
        critical_constraints = _load_critical_constraints()
        # Check if backup has tables that aren't available in this codebase
        backup_metadata = backup_data.get('metadata', {})
        backup_tables = set(backup_data.get('tables', {}).keys())
        available_tables = {table_info['name'] for table_info in BackupService.TABLE_ORDER}
        missing_in_codebase = backup_tables - available_tables
        
        if missing_in_codebase:
            print(f"\n⚠️  WARNING: Backup contains {len(missing_in_codebase)} table(s) not available in this codebase:")
            for table in sorted(missing_in_codebase):
                record_count = backup_data.get('tables', {}).get(table, {}).get('count', 0)
                print(f"   - {table}: {record_count} records will be SKIPPED (model not available)")
            print(f"   These tables will NOT be restored.\n")
        
        # Check if backup was made from a codebase with missing models
        backup_missing_models = backup_metadata.get('missing_models', [])
        if backup_missing_models:
            print(f"ℹ️  Note: This backup was created from a codebase missing {len(backup_missing_models)} model(s): {', '.join(backup_missing_models)}")
        
        stats = {
            'started_at': datetime.utcnow().isoformat(),
            'tables_imported': 0,
            'total_records_imported': 0,
            'tables_cleared': 0,
            'errors': [],
            'records_skipped_duplicates': 0,
            'duplicate_skips_by_table': {},
            'tables_skipped_missing_models': list(missing_in_codebase) if missing_in_codebase else [],
            'records_skipped_missing_models': sum(
                backup_data.get('tables', {}).get(table, {}).get('count', 0)
                for table in missing_in_codebase
            ) if missing_in_codebase else 0
        }
        
        # Determine if we should drop IDs (always drop if only clearing test tenants)
        # This prevents ID conflicts with production data when restoring test backups
        # SECURITY: Case-sensitive match for consistency with other security checks
        should_drop_ids = not clear_existing or (clear_existing and not os.getenv('TEST_CLEAR_ALL_DATA', '') == 'true')

        try:
            # Step 1: Clear existing data if requested (in reverse order to respect foreign keys)
            # IMPORTANT: Only clear data for test tenants (those with PYTEST prefix) to protect production data
            # UNLESS TEST_CLEAR_ALL_DATA=true is set, in which case clear ALL data
            if clear_existing:
                from app.models.tenant import Tenant

                # Check if we should clear ALL data (not just test tenants)
                # SECURITY: Case-sensitive match for consistency with other security checks
                clear_all_data = os.getenv('TEST_CLEAR_ALL_DATA', '') == 'true'
                
                if clear_all_data:
                    print("\n🗑️  Clearing ALL existing data (TEST_CLEAR_ALL_DATA=true)...")
                    print("  ⚠⚠️  WARNING: This will delete ALL data in the database! ⚠⚠️")
                else:
                    print("\n🗑️  Clearing existing data (test tenants only)...")
                
                # Find test tenants (those with PYTEST prefix in name)
                test_tenants = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
                    Tenant.name.like('PYTEST-%')
                ).all()
                test_tenant_ids = [t.id for t in test_tenants]
                
                # If clearing all data, proceed regardless of test tenants
                # If only clearing test tenants, check if any exist
                if not clear_all_data:
                    if not test_tenant_ids:
                        print("  ⚠ No test tenants found - skipping clear to protect production data")
                        print("  ⚠ If you need to clear all data, use clear_existing=True with TEST_CLEAR_ALL_DATA=true env var")
                        clear_existing = False
                
                # Track if we're only clearing test tenants (not full system)
                only_clearing_test_tenants = clear_existing and test_tenant_ids and not clear_all_data
                
                # Proceed with clearing if:
                # 1. clear_all_data is true (clear everything)
                # 2. OR test_tenant_ids exist (clear test tenants only)
                if clear_existing and (clear_all_data or test_tenant_ids):
                    if clear_all_data:
                        print(f"  ⚠⚠️  CLEARING ALL DATA - ALL TENANTS WILL BE DELETED ⚠⚠️")
                    elif test_tenant_ids:
                        print(f"  Found {len(test_tenant_ids)} test tenant(s) to clear")
                        if only_clearing_test_tenants:
                            print("  ⚠ Only clearing test tenants - will drop IDs during import to avoid conflicts with production data")
                    
                    # Delete in reverse order to respect foreign keys
                    # IMPORTANT: container_stock_thresholds must be deleted BEFORE storage_containers
                    # because container_stock_thresholds has a foreign key to storage_containers
                    deletion_order = list(reversed(BackupService.TABLE_ORDER))

                    # Ensure correct deletion order for tables with foreign key dependencies
                    # 1. container_stock_thresholds must be deleted BEFORE storage_containers
                    sc_idx = next((i for i, t in enumerate(deletion_order) if t['name'] == 'storage_containers'), None)
                    cst_idx = next((i for i, t in enumerate(deletion_order) if t['name'] == 'container_stock_thresholds'), None)
                    if sc_idx is not None and cst_idx is not None and cst_idx > sc_idx:
                        # Move container_stock_thresholds before storage_containers
                        cst_item = deletion_order.pop(cst_idx)
                        deletion_order.insert(sc_idx, cst_item)

                    # 2. asset_lifecycle_events must be deleted BEFORE assets
                    assets_idx = next((i for i, t in enumerate(deletion_order) if t['name'] == 'assets'), None)
                    lifecycle_idx = next((i for i, t in enumerate(deletion_order) if t['name'] == 'asset_lifecycle_events'), None)
                    if assets_idx is not None and lifecycle_idx is not None and lifecycle_idx > assets_idx:
                        # Move asset_lifecycle_events before assets
                        lifecycle_item = deletion_order.pop(lifecycle_idx)
                        deletion_order.insert(assets_idx, lifecycle_item)
                    
                    for table_info in deletion_order:
                        try:
                            model = table_info['model']
                            # Delete records based on clear mode
                            if hasattr(model, 'tenant_id'):
                                if clear_all_data:
                                    # Clear ALL records (all tenants)
                                    count = db.query(model).execution_options(skip_tenant_filter=True).delete(synchronize_session=False)
                                else:
                                    # Only delete records belonging to test tenants
                                    count = db.query(model).execution_options(skip_tenant_filter=True).filter(
                                        model.tenant_id.in_(test_tenant_ids)
                                    ).delete(synchronize_session=False)
                            else:
                                # For tables without tenant_id, only clear if explicitly enabled
                                if clear_all_data:
                                    count = db.query(model).execution_options(skip_tenant_filter=True).delete()
                                else:
                                    print(f"  ⚠ Skipping {table_info['name']} (no tenant_id, use TEST_CLEAR_ALL_DATA=true to clear)")
                                    count = 0
                            db.commit()
                            if count > 0:
                                stats['tables_cleared'] += 1
                                if clear_all_data:
                                    print(f"  ✓ Cleared {count} records from {table_info['name']} (ALL DATA)")
                                else:
                                    print(f"  ✓ Cleared {count} records from {table_info['name']} (test tenants only)")
                        except Exception as e:
                            db.rollback()
                            # Check if it's a missing table error (table doesn't exist in database)
                            error_str = str(e)
                            if 'UndefinedTable' in error_str or 'relation' in error_str and 'does not exist' in error_str:
                                # Table doesn't exist - this is expected for optional models
                                print(f"  ⚠ Skipping {table_info['name']} (table does not exist in database)")
                            else:
                                # Real error - add to errors list
                                error_msg = f"Error clearing {table_info['name']}: {error_str}"
                                print(f"  ⚠ {error_msg}")
                                stats['errors'].append(error_msg)

            # Step 2: Import data in order
            print("\n📥 Importing backup data...")
            tables_data = backup_data.get('tables', {})
            
            # Get list of available tables in this codebase
            available_tables = {table_info['name'] for table_info in BackupService.TABLE_ORDER}
            
            # Check for tables in backup that aren't in this codebase (before we start importing)
            backup_table_names = set(tables_data.keys())
            missing_tables_in_backup = backup_table_names - available_tables
            if missing_tables_in_backup:
                print(f"\n⚠️  WARNING: Backup contains {len(missing_tables_in_backup)} table(s) not available in this codebase:")
                for table_name in sorted(missing_tables_in_backup):
                    record_count = tables_data.get(table_name, {}).get('count', 0)
                    print(f"   - {table_name}: {record_count} records will be SKIPPED (model not available)")
                    stats['records_skipped_missing_models'] += record_count
                print(f"   These tables will NOT be restored.\n")
                stats['tables_skipped_missing_models'] = list(missing_tables_in_backup)
            
            # Build a set of imported IDs for foreign key validation
            imported_ids = {}  # table_name -> set of imported IDs
            
            # Track ID mappings for foreign key resolution (old_id -> new_id)
            # This is needed when clear_existing=false and IDs are regenerated
            id_mappings = {}  # table_name -> {old_id: new_id}
            
            for table_info in BackupService.TABLE_ORDER:
                model = table_info['model']
                table_name = table_info['name']

                if table_name not in tables_data:
                    print(f"  ⚠ Skipping {table_name} (not in backup)")
                    continue

                table_backup = tables_data[table_name]
                records = table_backup.get('data', [])

                if not records:
                    print(f"  ⚠ No data for {table_name}")
                    continue

                try:
                    # Insert records
                    imported_count = 0
                    for record_data in records:
                        # Convert datetime strings back to datetime objects
                        for key, value in record_data.items():
                            if isinstance(value, str) and 'T' in value:
                                try:
                                    record_data[key] = datetime.fromisoformat(value)
                                except (ValueError, TypeError):
                                    pass

                        # Drop primary key IDs to avoid collisions when:
                        # 1. clear_existing=False (always drop IDs)
                        # 2. clear_existing=True but only test tenants were cleared (production data still exists, IDs might conflict)
                        # Only preserve IDs when clear_existing=True AND all data was cleared (full system restore)
                        old_id = None
                        if should_drop_ids and 'id' in record_data:
                            # Save old ID for mapping before deleting it
                            old_id = record_data['id']
                            # Check if this model has an 'id' primary key
                            # All models in TABLE_ORDER use Integer primary keys that auto-increment
                            del record_data['id']
                            
                            # Check for existing records by unique identifiers to prevent duplicates
                            # CRITICAL: Use the 15 critical constraints as the source of truth
                            existing = _check_duplicate_by_constraints(
                                db, model, table_name, record_data, critical_constraints
                            )
                            
                            # If constraint check found a duplicate, skip this record
                            if existing:
                                # Map old ID to existing ID for foreign key resolution
                                if not clear_existing and old_id is not None:
                                    if table_name not in id_mappings:
                                        id_mappings[table_name] = {}
                                    id_mappings[table_name][old_id] = existing.id
                                
                                # Get constraint info for better logging
                                constraint_info = None
                                for cname, cinfo in critical_constraints.items():
                                    if cinfo.get('table') == table_name:
                                        constraint_info = cinfo
                                        break
                                
                                constraint_desc = constraint_info.get('description', 'constraint') if constraint_info else 'constraint'
                                columns = constraint_info.get('columns', []) if constraint_info else []
                                column_values = ', '.join([f"{col}={record_data.get(col)}" for col in columns if record_data.get(col) is not None])
                                
                                print(f"  ⚠ Skipping {table_name} (duplicate by {constraint_desc}): {column_values} (existing ID: {existing.id})")
                                stats['records_skipped_duplicates'] += 1
                                if table_name not in stats['duplicate_skips_by_table']:
                                    stats['duplicate_skips_by_table'][table_name] = 0
                                stats['duplicate_skips_by_table'][table_name] += 1
                                continue
                            
                            # Legacy hardcoded checks for tables without constraints or for additional validation
                            # (Keep for backward compatibility and tables not covered by constraints)
                            if table_name == 'assets':
                                # Check by asset_tag and serial_number (both are unique per tenant)
                                # Use skip_tenant_filter to find existing records regardless of current tenant context
                                existing = db.query(model).execution_options(skip_tenant_filter=True).filter(
                                    model.asset_tag == record_data.get('asset_tag'),
                                    model.serial_number == record_data.get('serial_number'),
                                    model.tenant_id == record_data.get('tenant_id')
                                ).first()
                                if existing:
                                    # Map old ID to existing ID for foreign key resolution
                                    if not clear_existing and old_id is not None:
                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                    print(f"  ⚠ Skipping {table_name} (duplicate): asset_tag={record_data.get('asset_tag')}, serial={record_data.get('serial_number')} (existing ID: {existing.id})")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                    continue
                            elif table_name == 'datacenters':
                                # Check by name and tenant_id
                                # Use skip_tenant_filter to find existing records regardless of current tenant context
                                existing = db.query(model).execution_options(skip_tenant_filter=True).filter(
                                    model.name == record_data.get('name'),
                                    model.tenant_id == record_data.get('tenant_id')
                                ).first()
                                
                                # Fallback: check by code and tenant_id
                                if not existing and record_data.get('code'):
                                    existing = db.query(model).execution_options(skip_tenant_filter=True).filter(
                                        model.code == record_data.get('code'),
                                        model.tenant_id == record_data.get('tenant_id')
                                    ).first()
                                if existing:
                                    # Reactivate if soft-deleted
                                    if hasattr(existing, 'is_active') and not existing.is_active:
                                        existing.is_active = True
                                        db.add(existing)
                                        db.flush()
                                        print(f"  ✓ Reactivated soft-deleted {table_name}: {record_data.get('name')}")

                                    # Map old ID to existing ID for foreign key resolution
                                    if not clear_existing and old_id is not None:
                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                    print(f"  ⚠ Skipping {table_name} (duplicate): name={record_data.get('name')}, tenant_id={record_data.get('tenant_id')} (existing ID: {existing.id})")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                    continue
                            elif table_name == 'rooms':
                                # Map datacenter_id if needed (works for both clear_existing modes when IDs are dropped)
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif should_drop_ids:
                                        # When IDs are dropped, try to find the datacenter by name/tenant and use its new ID
                                        from app.models.location import Datacenter
                                        
                                        # CRITICAL FIX: First check if the old ID still exists (e.g. partial restore)
                                        # This prevents mapping to the wrong datacenter when multiple exist
                                        dc = db.query(Datacenter).execution_options(skip_tenant_filter=True).filter(
                                            Datacenter.id == old_dc_id
                                        ).first()
                                        
                                        if not dc:
                                            # Only if old ID doesn't exist, try to find by tenant (fallback)
                                            # Note: This is a guess and might pick the wrong one if multiple exist
                                            dc = db.query(Datacenter).execution_options(skip_tenant_filter=True).filter(
                                                Datacenter.tenant_id == record_data.get('tenant_id')
                                            ).order_by(Datacenter.id.desc()).first()  # Get most recently created
                                            
                                        if dc:
                                            # Update mapping for future use
                                            if 'datacenters' not in id_mappings:
                                                id_mappings['datacenters'] = {}
                                            id_mappings['datacenters'][old_dc_id] = dc.id
                                            record_data['datacenter_id'] = dc.id
                                        else:
                                            record_data['datacenter_id'] = None
                                
                                # Check by name, datacenter_id, and tenant_id
                                # Use skip_tenant_filter to find existing records regardless of current tenant context
                                existing = db.query(model).execution_options(skip_tenant_filter=True).filter(
                                    model.name == record_data.get('name'),
                                    model.datacenter_id == record_data.get('datacenter_id'),
                                    model.tenant_id == record_data.get('tenant_id')
                                ).first()
                                if existing:
                                    # Reactivate if soft-deleted
                                    if hasattr(existing, 'is_active') and not existing.is_active:
                                        existing.is_active = True
                                        db.add(existing)
                                        db.flush()
                                        print(f"  ✓ Reactivated soft-deleted {table_name}: {record_data.get('name')}")

                                    # Map old ID to existing ID for foreign key resolution
                                    if not clear_existing and old_id is not None:
                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                    print(f"  ⚠ Skipping {table_name} (duplicate): name={record_data.get('name')}, datacenter_id={record_data.get('datacenter_id')}, tenant_id={record_data.get('tenant_id')} (existing ID: {existing.id})")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                    continue
                            elif table_name == 'racks':
                                # Map datacenter_id first (racks need both datacenter_id and room_id)
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif should_drop_ids:
                                        # When IDs are dropped, first check if the datacenter_id already exists in the database
                                        # (this handles cases where IDs were already remapped before calling import_database)
                                        from app.models.location import Datacenter
                                        existing_dc = db.query(Datacenter).execution_options(skip_tenant_filter=True).filter(
                                            Datacenter.id == old_dc_id,
                                            Datacenter.tenant_id == record_data.get('tenant_id')
                                        ).first()
                                        if existing_dc:
                                            # The datacenter_id is already correct, use it as-is
                                            if 'datacenters' not in id_mappings:
                                                id_mappings['datacenters'] = {}
                                            id_mappings['datacenters'][old_dc_id] = old_dc_id
                                            # Keep the existing datacenter_id
                                        else:
                                            # Fallback: try to find datacenter by name/tenant
                                            dc = db.query(Datacenter).execution_options(skip_tenant_filter=True).filter(
                                                Datacenter.tenant_id == record_data.get('tenant_id')
                                            ).order_by(Datacenter.id.asc()).first()  # Changed to ASC to get the first/lowest ID
                                            if dc:
                                                if 'datacenters' not in id_mappings:
                                                    id_mappings['datacenters'] = {}
                                                id_mappings['datacenters'][old_dc_id] = dc.id
                                                record_data['datacenter_id'] = dc.id
                                            else:
                                                record_data['datacenter_id'] = None
                                
                                # Map room_id if needed (works for both clear_existing modes when IDs are dropped)
                                if 'room_id' in record_data and record_data.get('room_id'):
                                    old_room_id = record_data.get('room_id')
                                    if 'rooms' in id_mappings and old_room_id in id_mappings['rooms']:
                                        record_data['room_id'] = id_mappings['rooms'][old_room_id]
                                    elif should_drop_ids:
                                        # When IDs are dropped, first check if the room_id already exists in the database
                                        # (this handles cases where IDs were already remapped before calling import_database)
                                        from app.models.location import Room
                                        existing_room = db.query(Room).execution_options(skip_tenant_filter=True).filter(
                                            Room.id == old_room_id,
                                            Room.tenant_id == record_data.get('tenant_id')
                                        ).first()
                                        if existing_room:
                                            # The room_id is already correct, use it as-is
                                            if 'rooms' not in id_mappings:
                                                id_mappings['rooms'] = {}
                                            id_mappings['rooms'][old_room_id] = old_room_id
                                            # Keep the existing room_id
                                        else:
                                            # Fallback: try to find room by name/datacenter/tenant
                                            room = db.query(Room).execution_options(skip_tenant_filter=True).filter(
                                                Room.tenant_id == record_data.get('tenant_id'),
                                                Room.datacenter_id == record_data.get('datacenter_id')
                                            ).order_by(Room.id.desc()).first()
                                            if room:
                                                if 'rooms' not in id_mappings:
                                                    id_mappings['rooms'] = {}
                                                id_mappings['rooms'][old_room_id] = room.id
                                                record_data['room_id'] = room.id
                                            else:
                                                record_data['room_id'] = None
                                
                                # Check by name, room_id, and tenant_id
                                # Use skip_tenant_filter to find existing records regardless of current tenant context
                                existing = db.query(model).execution_options(skip_tenant_filter=True).filter(
                                    model.name == record_data.get('name'),
                                    model.room_id == record_data.get('room_id'),
                                    model.tenant_id == record_data.get('tenant_id')
                                ).first()
                                if existing:
                                    # Reactivate if soft-deleted
                                    if hasattr(existing, 'is_active') and not existing.is_active:
                                        existing.is_active = True
                                        db.add(existing)
                                        db.flush()
                                        print(f"  ✓ Reactivated soft-deleted {table_name}: {record_data.get('name')}")

                                    # Map old ID to existing ID for foreign key resolution
                                    if not clear_existing and old_id is not None:
                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                    print(f"  ⚠ Skipping {table_name} (duplicate): name={record_data.get('name')}, room_id={record_data.get('room_id')}, tenant_id={record_data.get('tenant_id')} (existing ID: {existing.id})")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                    continue
                            elif table_name == 'asset_types':
                                # Check by name and tenant_id
                                # Use skip_tenant_filter to find existing records regardless of current tenant context
                                existing = db.query(model).execution_options(skip_tenant_filter=True).filter(
                                    model.name == record_data.get('name'),
                                    model.tenant_id == record_data.get('tenant_id')
                                ).first()
                                if existing:
                                    # Map old ID to existing ID for foreign key resolution
                                    if not clear_existing and old_id is not None:
                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                    print(f"  ⚠ Skipping {table_name} (duplicate): name={record_data.get('name')}, tenant_id={record_data.get('tenant_id')} (existing ID: {existing.id})")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                    continue
                            elif table_name == 'tenants':
                                # Check by name or slug (both are unique)
                                # Use skip_tenant_filter to find existing records regardless of current tenant context
                                from app.models.tenant import Tenant
                                existing = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
                                    (Tenant.name == record_data.get('name')) | (Tenant.slug == record_data.get('slug'))
                                ).first()
                                if existing:
                                    # Map old ID to existing ID for foreign key resolution
                                    if not clear_existing and old_id is not None:
                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                    print(f"  ⚠ Skipping {table_name} (duplicate): name={record_data.get('name')} or slug={record_data.get('slug')} (existing ID: {existing.id})")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                    continue
                            elif table_name == 'storage_containers':
                                # Check by name and tenant_id (unique constraint)
                                # Use skip_tenant_filter to find existing records regardless of current tenant context
                                from app.models.storage_container import StorageContainer
                                existing = db.query(StorageContainer).execution_options(skip_tenant_filter=True).filter(
                                    StorageContainer.name == record_data.get('name'),
                                    StorageContainer.tenant_id == record_data.get('tenant_id')
                                ).first()
                                if existing:
                                    # Map old ID to existing ID for foreign key resolution
                                    if not clear_existing and old_id is not None:
                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                    print(f"  ⚠ Skipping {table_name} (duplicate): name={record_data.get('name')}, tenant_id={record_data.get('tenant_id')} (existing ID: {existing.id})")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                    continue
                            
                            # Validate and clear invalid foreign key references (for both clear_existing modes)
                            # This is needed when locations/assets are deleted but assets still reference them
                            if table_name == 'assets':
                                # Check datacenter_id
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    # First try to map old ID to new ID
                                    if not clear_existing and 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    else:
                                        # Check if it exists in database
                                        # Use the imported Datacenter from top of file to avoid scope issues
                                        from app.models.location import Datacenter as DC
                                        dc_exists = db.query(DC).execution_options(skip_tenant_filter=True).filter(
                                            DC.id == old_dc_id
                                        ).first()
                                        if not dc_exists:
                                            record_data['datacenter_id'] = None
                                
                                # Check room_id
                                if 'room_id' in record_data and record_data.get('room_id'):
                                    old_room_id = record_data.get('room_id')
                                    # First try to map old ID to new ID
                                    if not clear_existing and 'rooms' in id_mappings and old_room_id in id_mappings['rooms']:
                                        record_data['room_id'] = id_mappings['rooms'][old_room_id]
                                    else:
                                        # Check if it exists in database
                                        room_exists = db.query(Room).execution_options(skip_tenant_filter=True).filter(
                                            Room.id == old_room_id
                                        ).first()
                                        if not room_exists:
                                            record_data['room_id'] = None
                                
                                # Check rack_id
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    # First try to map old ID to new ID
                                    if not clear_existing and 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    else:
                                        # Check if it exists in database
                                        rack_exists = db.query(Rack).execution_options(skip_tenant_filter=True).filter(
                                            Rack.id == old_rack_id
                                        ).first()
                                        if not rack_exists:
                                            record_data['rack_id'] = None
                                
                                # Check storage_container_id
                                if 'storage_container_id' in record_data and record_data.get('storage_container_id'):
                                    old_container_id = record_data.get('storage_container_id')
                                    # First try to map old ID to new ID
                                    if not clear_existing and 'storage_containers' in id_mappings and old_container_id in id_mappings['storage_containers']:
                                        record_data['storage_container_id'] = id_mappings['storage_containers'][old_container_id]
                                    else:
                                        # Check if it exists in database
                                        # Import here to avoid scope issues
                                        from app.models.storage_container import StorageContainer as SC
                                        container_exists = db.query(SC).execution_options(skip_tenant_filter=True).filter(
                                            SC.id == old_container_id
                                        ).first()
                                        if not container_exists:
                                            record_data['storage_container_id'] = None
                                
                                # Check container_id (self-referential for storage boxes)
                                if 'container_id' in record_data and record_data.get('container_id'):
                                    old_container_id = record_data.get('container_id')
                                    # First try to map old ID to new ID
                                    if not clear_existing and 'assets' in id_mappings and old_container_id in id_mappings['assets']:
                                        record_data['container_id'] = id_mappings['assets'][old_container_id]
                                    else:
                                        # Check if it exists in database
                                        container_exists = db.query(Asset).execution_options(skip_tenant_filter=True).filter(
                                            Asset.id == old_container_id
                                        ).first()
                                        if not container_exists:
                                            record_data['container_id'] = None
                        
                        # Map foreign key references for dependent tables (when IDs are dropped)
                        if should_drop_ids:
                            # For asset_lifecycle_events, map asset_id from old to new ID
                            if table_name == 'asset_lifecycle_events' and 'asset_id' in record_data:
                                old_asset_id = record_data.get('asset_id')
                                if old_asset_id and 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                    record_data['asset_id'] = id_mappings['assets'][old_asset_id]
                                elif old_asset_id:
                                    # Asset doesn't exist (wasn't imported), skip this event
                                    continue
                            
                            # For maintenance_records, map asset_id from old to new ID
                            if table_name == 'maintenance_records' and 'asset_id' in record_data:
                                old_asset_id = record_data.get('asset_id')
                                if old_asset_id and 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                    record_data['asset_id'] = id_mappings['assets'][old_asset_id]
                                elif old_asset_id:
                                    # Asset doesn't exist in mappings - this can happen if:
                                    # 1. The asset wasn't imported (maybe it was skipped due to duplicate check)
                                    # 2. The asset_id in the maintenance record doesn't match any asset's old_id
                                    # Try to find the asset by tenant_id and use the most recent asset as a fallback
                                    # This is not ideal but better than skipping the maintenance record
                                    asset = db.query(Asset).execution_options(skip_tenant_filter=True).filter(
                                        Asset.tenant_id == record_data.get('tenant_id')
                                    ).order_by(Asset.id.desc()).first()
                                    if asset:
                                        # Use this asset's ID and update the mapping
                                        record_data['asset_id'] = asset.id
                                        if 'assets' not in id_mappings:
                                            id_mappings['assets'] = {}
                                        id_mappings['assets'][old_asset_id] = asset.id
                                        print(f"  ⚠ Warning: Maintenance record asset_id {old_asset_id} mapped to asset {asset.id} (fallback)")
                                    else:
                                        # No asset found, skip this maintenance record
                                        print(f"  ⚠ Warning: Maintenance record references asset_id {old_asset_id} but no asset found. Skipping.")
                                        continue
                            
                            # For workflow_executions, map workflow_id and target_asset_id
                            if table_name == 'workflow_executions' and 'workflow_id' in record_data:
                                old_workflow_id = record_data.get('workflow_id')
                                if old_workflow_id and 'workflows' in id_mappings and old_workflow_id in id_mappings['workflows']:
                                    record_data['workflow_id'] = id_mappings['workflows'][old_workflow_id]
                                elif old_workflow_id:
                                    # Workflow doesn't exist, skip this execution
                                    print(f"  ⚠ Warning: Workflow execution references workflow_id {old_workflow_id} but workflow not found. Skipping.")
                                    continue
                                if 'target_asset_id' in record_data and record_data.get('target_asset_id'):
                                    old_asset_id = record_data.get('target_asset_id')
                                    if old_asset_id and 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['target_asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id:
                                        record_data['target_asset_id'] = None
                            
                            # For workflow_steps, map execution_id
                            if table_name == 'workflow_steps' and 'execution_id' in record_data:
                                old_execution_id = record_data.get('execution_id')
                                if old_execution_id and 'workflow_executions' in id_mappings and old_execution_id in id_mappings['workflow_executions']:
                                    record_data['execution_id'] = id_mappings['workflow_executions'][old_execution_id]
                                elif old_execution_id:
                                    # Execution doesn't exist, skip this step
                                    print(f"  ⚠ Warning: Workflow step references execution_id {old_execution_id} but execution not found. Skipping.")
                                    continue
                            
                            # For environmental_readings, map sensor_id and correlated_asset_id
                            if table_name == 'environmental_readings' and 'sensor_id' in record_data:
                                old_sensor_id = record_data.get('sensor_id')
                                if old_sensor_id and 'environmental_sensors' in id_mappings and old_sensor_id in id_mappings['environmental_sensors']:
                                    record_data['sensor_id'] = id_mappings['environmental_sensors'][old_sensor_id]
                                elif old_sensor_id:
                                    # Sensor doesn't exist, skip this reading
                                    print(f"  ⚠ Warning: Environmental reading references sensor_id {old_sensor_id} but sensor not found. Skipping.")
                                    continue
                                if 'correlated_asset_id' in record_data and record_data.get('correlated_asset_id'):
                                    old_asset_id = record_data.get('correlated_asset_id')
                                    if old_asset_id and 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['correlated_asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id:
                                        record_data['correlated_asset_id'] = None
                            
                            # For environmental_sensors, map datacenter_id, rack_id, room_id
                            if table_name == 'environmental_sensors' and 'datacenter_id' in record_data:
                                old_dc_id = record_data.get('datacenter_id')
                                if old_dc_id and 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                    record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                elif old_dc_id:
                                    # Datacenter doesn't exist, skip this sensor
                                    print(f"  ⚠ Warning: Environmental sensor references datacenter_id {old_dc_id} but datacenter not found. Skipping.")
                                    continue
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if old_rack_id and 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id:
                                        record_data['rack_id'] = None
                                if 'room_id' in record_data and record_data.get('room_id'):
                                    old_room_id = record_data.get('room_id')
                                    if old_room_id and 'rooms' in id_mappings and old_room_id in id_mappings['rooms']:
                                        record_data['room_id'] = id_mappings['rooms'][old_room_id]
                                    elif old_room_id:
                                        record_data['room_id'] = None
                            
                            # For capacity_metrics, map rack_id
                            if table_name == 'capacity_metrics' and 'rack_id' in record_data:
                                old_rack_id = record_data.get('rack_id')
                                if old_rack_id and 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                    record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                elif old_rack_id:
                                    # Rack doesn't exist, skip this metric
                                    print(f"  ⚠ Warning: Capacity metric references rack_id {old_rack_id} but rack not found. Skipping.")
                                    continue
                            
                            # For power_metrics, map rack_id, datacenter_id, asset_id
                            if table_name == 'power_metrics':
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if old_rack_id and 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id:
                                        record_data['rack_id'] = None
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if old_dc_id and 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif old_dc_id:
                                        record_data['datacenter_id'] = None
                                if 'asset_id' in record_data and record_data.get('asset_id'):
                                    old_asset_id = record_data.get('asset_id')
                                    if old_asset_id and 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id:
                                        record_data['asset_id'] = None
                            
                            # For cooling_metrics, map rack_id, datacenter_id, room_id
                            if table_name == 'cooling_metrics':
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if old_rack_id and 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id:
                                        record_data['rack_id'] = None
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if old_dc_id and 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif old_dc_id:
                                        record_data['datacenter_id'] = None
                                if 'room_id' in record_data and record_data.get('room_id'):
                                    old_room_id = record_data.get('room_id')
                                    if old_room_id and 'rooms' in id_mappings and old_room_id in id_mappings['rooms']:
                                        record_data['room_id'] = id_mappings['rooms'][old_room_id]
                                    elif old_room_id:
                                        record_data['room_id'] = None
                            
                            # For network_connections, map source_port_id and destination_port_id
                            if table_name == 'network_connections':
                                if 'source_port_id' in record_data and record_data.get('source_port_id'):
                                    old_port_id = record_data.get('source_port_id')
                                    if old_port_id and 'network_ports' in id_mappings and old_port_id in id_mappings['network_ports']:
                                        record_data['source_port_id'] = id_mappings['network_ports'][old_port_id]
                                    elif old_port_id:
                                        # Port doesn't exist, skip this connection
                                        print(f"  ⚠ Warning: Network connection references source_port_id {old_port_id} but port not found. Skipping.")
                                        continue
                                if 'destination_port_id' in record_data and record_data.get('destination_port_id'):
                                    old_port_id = record_data.get('destination_port_id')
                                    if old_port_id and 'network_ports' in id_mappings and old_port_id in id_mappings['network_ports']:
                                        record_data['destination_port_id'] = id_mappings['network_ports'][old_port_id]
                                    elif old_port_id:
                                        # Port doesn't exist, skip this connection
                                        print(f"  ⚠ Warning: Network connection references destination_port_id {old_port_id} but port not found. Skipping.")
                                        continue
                            
                            # For print_jobs, map asset_id, container_id, rack_id, created_by_user_id
                            if table_name == 'print_jobs':
                                if 'asset_id' in record_data and record_data.get('asset_id'):
                                    old_asset_id = record_data.get('asset_id')
                                    if old_asset_id and 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id:
                                        record_data['asset_id'] = None
                                if 'container_id' in record_data and record_data.get('container_id'):
                                    old_container_id = record_data.get('container_id')
                                    if old_container_id and 'storage_containers' in id_mappings and old_container_id in id_mappings['storage_containers']:
                                        record_data['container_id'] = id_mappings['storage_containers'][old_container_id]
                                    elif old_container_id:
                                        record_data['container_id'] = None
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if old_rack_id and 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id:
                                        record_data['rack_id'] = None
                                if 'created_by_user_id' in record_data and record_data.get('created_by_user_id'):
                                    old_user_id = record_data.get('created_by_user_id')
                                    if old_user_id and 'users' in id_mappings and old_user_id in id_mappings['users']:
                                        record_data['created_by_user_id'] = id_mappings['users'][old_user_id]
                                    elif old_user_id:
                                        record_data['created_by_user_id'] = None
                            
                            # For api_keys, map user_id
                            if table_name == 'api_keys' and 'user_id' in record_data:
                                old_user_id = record_data.get('user_id')
                                if old_user_id and 'users' in id_mappings and old_user_id in id_mappings['users']:
                                    record_data['user_id'] = id_mappings['users'][old_user_id]
                                elif old_user_id:
                                    # User doesn't exist, skip this API key
                                    print(f"  ⚠ Warning: API key references user_id {old_user_id} but user not found. Skipping.")
                                    continue
                            
                            # For vlans, map datacenter_id
                            if table_name == 'vlans' and 'datacenter_id' in record_data:
                                old_dc_id = record_data.get('datacenter_id')
                                if old_dc_id and 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                    record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                elif old_dc_id:
                                    record_data['datacenter_id'] = None
                        
                        # When clear_existing=True, validate and clear invalid foreign key references
                        if clear_existing:
                            # For assets table, check container_id references
                            if table_name == 'assets' and 'container_id' in record_data:
                                container_id = record_data.get('container_id')
                                if container_id and container_id not in imported_ids.get('assets', set()):
                                    # Container doesn't exist, clear the reference
                                    record_data['container_id'] = None
                            
                            # For asset_lifecycle_events, check asset_id references
                            if table_name == 'asset_lifecycle_events' and 'asset_id' in record_data:
                                asset_id = record_data.get('asset_id')
                                if asset_id and asset_id not in imported_ids.get('assets', set()):
                                    # Asset doesn't exist, skip this event
                                    continue
                            
                            # For maintenance_records, check asset_id references
                            if table_name == 'maintenance_records' and 'asset_id' in record_data:
                                asset_id = record_data.get('asset_id')
                                if asset_id:
                                    # First try to map old asset_id to new asset_id (when IDs are preserved)
                                    if not should_drop_ids and 'assets' in id_mappings and asset_id in id_mappings['assets']:
                                        record_data['asset_id'] = id_mappings['assets'][asset_id]
                                    # Check if mapped/new asset_id exists in imported_ids
                                    mapped_asset_id = record_data.get('asset_id')
                                    if mapped_asset_id and mapped_asset_id not in imported_ids.get('assets', set()):
                                        # Asset doesn't exist - try to find it by tenant_id as fallback
                                        from app.models.asset import Asset as AssetModel
                                        fallback_asset = db.query(AssetModel).execution_options(skip_tenant_filter=True).filter(
                                            AssetModel.tenant_id == record_data.get('tenant_id')
                                        ).order_by(AssetModel.id.desc()).first()
                                        if fallback_asset:
                                            record_data['asset_id'] = fallback_asset.id
                                            print(f"  ⚠ Warning: Maintenance record asset_id {asset_id} mapped to asset {fallback_asset.id} (fallback)")
                                        else:
                                            # Asset doesn't exist, set asset_id to None instead of skipping
                                            # This allows maintenance records to be imported even if asset is missing
                                            record_data['asset_id'] = None
                                            print(f"  ⚠ Warning: Maintenance record references asset_id {asset_id} but asset not found. Setting asset_id to None.")
                            
                            # For workflow_executions, map workflow_id and target_asset_id
                            if table_name == 'workflow_executions':
                                if 'workflow_id' in record_data and record_data.get('workflow_id'):
                                    old_workflow_id = record_data.get('workflow_id')
                                    if 'workflows' in id_mappings and old_workflow_id in id_mappings['workflows']:
                                        record_data['workflow_id'] = id_mappings['workflows'][old_workflow_id]
                                    elif old_workflow_id not in imported_ids.get('workflows', set()):
                                        # Workflow doesn't exist, skip this execution
                                        print(f"  ⚠ Warning: Workflow execution references workflow_id {old_workflow_id} but workflow not found. Skipping.")
                                        continue
                                if 'target_asset_id' in record_data and record_data.get('target_asset_id'):
                                    old_asset_id = record_data.get('target_asset_id')
                                    if 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['target_asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id not in imported_ids.get('assets', set()):
                                        record_data['target_asset_id'] = None
                            
                            # For workflow_steps, map execution_id
                            if table_name == 'workflow_steps':
                                if 'execution_id' in record_data and record_data.get('execution_id'):
                                    old_execution_id = record_data.get('execution_id')
                                    if 'workflow_executions' in id_mappings and old_execution_id in id_mappings['workflow_executions']:
                                        record_data['execution_id'] = id_mappings['workflow_executions'][old_execution_id]
                                    elif old_execution_id not in imported_ids.get('workflow_executions', set()):
                                        # Execution doesn't exist, skip this step
                                        print(f"  ⚠ Warning: Workflow step references execution_id {old_execution_id} but execution not found. Skipping.")
                                        continue
                            
                            # For environmental_readings, map sensor_id and correlated_asset_id
                            if table_name == 'environmental_readings':
                                if 'sensor_id' in record_data and record_data.get('sensor_id'):
                                    old_sensor_id = record_data.get('sensor_id')
                                    if 'environmental_sensors' in id_mappings and old_sensor_id in id_mappings['environmental_sensors']:
                                        record_data['sensor_id'] = id_mappings['environmental_sensors'][old_sensor_id]
                                    elif old_sensor_id not in imported_ids.get('environmental_sensors', set()):
                                        # Sensor doesn't exist, skip this reading
                                        print(f"  ⚠ Warning: Environmental reading references sensor_id {old_sensor_id} but sensor not found. Skipping.")
                                        continue
                                if 'correlated_asset_id' in record_data and record_data.get('correlated_asset_id'):
                                    old_asset_id = record_data.get('correlated_asset_id')
                                    if 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['correlated_asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id not in imported_ids.get('assets', set()):
                                        record_data['correlated_asset_id'] = None
                            
                            # For environmental_sensors, map datacenter_id, rack_id, room_id
                            if table_name == 'environmental_sensors':
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif old_dc_id not in imported_ids.get('datacenters', set()):
                                        # Datacenter doesn't exist, skip this sensor
                                        print(f"  ⚠ Warning: Environmental sensor references datacenter_id {old_dc_id} but datacenter not found. Skipping.")
                                        continue
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id not in imported_ids.get('racks', set()):
                                        record_data['rack_id'] = None
                                if 'room_id' in record_data and record_data.get('room_id'):
                                    old_room_id = record_data.get('room_id')
                                    if 'rooms' in id_mappings and old_room_id in id_mappings['rooms']:
                                        record_data['room_id'] = id_mappings['rooms'][old_room_id]
                                    elif old_room_id not in imported_ids.get('rooms', set()):
                                        record_data['room_id'] = None
                            
                            # For capacity_metrics, map rack_id
                            if table_name == 'capacity_metrics':
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id not in imported_ids.get('racks', set()):
                                        # Rack doesn't exist, skip this metric
                                        print(f"  ⚠ Warning: Capacity metric references rack_id {old_rack_id} but rack not found. Skipping.")
                                        continue
                            
                            # For power_metrics, map rack_id, datacenter_id, asset_id
                            if table_name == 'power_metrics':
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id not in imported_ids.get('racks', set()):
                                        record_data['rack_id'] = None
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif old_dc_id not in imported_ids.get('datacenters', set()):
                                        record_data['datacenter_id'] = None
                                if 'asset_id' in record_data and record_data.get('asset_id'):
                                    old_asset_id = record_data.get('asset_id')
                                    if 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id not in imported_ids.get('assets', set()):
                                        record_data['asset_id'] = None
                            
                            # For cooling_metrics, map rack_id, datacenter_id, room_id
                            if table_name == 'cooling_metrics':
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id not in imported_ids.get('racks', set()):
                                        record_data['rack_id'] = None
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif old_dc_id not in imported_ids.get('datacenters', set()):
                                        record_data['datacenter_id'] = None
                                if 'room_id' in record_data and record_data.get('room_id'):
                                    old_room_id = record_data.get('room_id')
                                    if 'rooms' in id_mappings and old_room_id in id_mappings['rooms']:
                                        record_data['room_id'] = id_mappings['rooms'][old_room_id]
                                    elif old_room_id not in imported_ids.get('rooms', set()):
                                        record_data['room_id'] = None
                            
                            # For network_connections, map source_port_id and destination_port_id
                            if table_name == 'network_connections':
                                if 'source_port_id' in record_data and record_data.get('source_port_id'):
                                    old_port_id = record_data.get('source_port_id')
                                    if 'network_ports' in id_mappings and old_port_id in id_mappings['network_ports']:
                                        record_data['source_port_id'] = id_mappings['network_ports'][old_port_id]
                                    elif old_port_id not in imported_ids.get('network_ports', set()):
                                        # Port doesn't exist, skip this connection
                                        print(f"  ⚠ Warning: Network connection references source_port_id {old_port_id} but port not found. Skipping.")
                                        continue
                                if 'destination_port_id' in record_data and record_data.get('destination_port_id'):
                                    old_port_id = record_data.get('destination_port_id')
                                    if 'network_ports' in id_mappings and old_port_id in id_mappings['network_ports']:
                                        record_data['destination_port_id'] = id_mappings['network_ports'][old_port_id]
                                    elif old_port_id not in imported_ids.get('network_ports', set()):
                                        # Port doesn't exist, skip this connection
                                        print(f"  ⚠ Warning: Network connection references destination_port_id {old_port_id} but port not found. Skipping.")
                                        continue
                            
                            # For print_jobs, map asset_id, container_id, rack_id, created_by_user_id
                            if table_name == 'print_jobs':
                                if 'asset_id' in record_data and record_data.get('asset_id'):
                                    old_asset_id = record_data.get('asset_id')
                                    if 'assets' in id_mappings and old_asset_id in id_mappings['assets']:
                                        record_data['asset_id'] = id_mappings['assets'][old_asset_id]
                                    elif old_asset_id not in imported_ids.get('assets', set()):
                                        record_data['asset_id'] = None
                                if 'container_id' in record_data and record_data.get('container_id'):
                                    old_container_id = record_data.get('container_id')
                                    if 'storage_containers' in id_mappings and old_container_id in id_mappings['storage_containers']:
                                        record_data['container_id'] = id_mappings['storage_containers'][old_container_id]
                                    elif old_container_id not in imported_ids.get('storage_containers', set()):
                                        record_data['container_id'] = None
                                if 'rack_id' in record_data and record_data.get('rack_id'):
                                    old_rack_id = record_data.get('rack_id')
                                    if 'racks' in id_mappings and old_rack_id in id_mappings['racks']:
                                        record_data['rack_id'] = id_mappings['racks'][old_rack_id]
                                    elif old_rack_id not in imported_ids.get('racks', set()):
                                        record_data['rack_id'] = None
                                if 'created_by_user_id' in record_data and record_data.get('created_by_user_id'):
                                    old_user_id = record_data.get('created_by_user_id')
                                    if 'users' in id_mappings and old_user_id in id_mappings['users']:
                                        record_data['created_by_user_id'] = id_mappings['users'][old_user_id]
                                    elif old_user_id not in imported_ids.get('users', set()):
                                        record_data['created_by_user_id'] = None
                            
                            # For api_keys, map user_id
                            if table_name == 'api_keys':
                                if 'user_id' in record_data and record_data.get('user_id'):
                                    old_user_id = record_data.get('user_id')
                                    if 'users' in id_mappings and old_user_id in id_mappings['users']:
                                        record_data['user_id'] = id_mappings['users'][old_user_id]
                                    elif old_user_id not in imported_ids.get('users', set()):
                                        # User doesn't exist, skip this API key
                                        print(f"  ⚠ Warning: API key references user_id {old_user_id} but user not found. Skipping.")
                                        continue
                            
                            # For vlans, map datacenter_id
                            if table_name == 'vlans':
                                if 'datacenter_id' in record_data and record_data.get('datacenter_id'):
                                    old_dc_id = record_data.get('datacenter_id')
                                    if 'datacenters' in id_mappings and old_dc_id in id_mappings['datacenters']:
                                        record_data['datacenter_id'] = id_mappings['datacenters'][old_dc_id]
                                    elif old_dc_id not in imported_ids.get('datacenters', set()):
                                        record_data['datacenter_id'] = None

                        # Create new instance
                        try:
                            instance = model(**record_data)
                            db.add(instance)
                            db.flush()  # Flush to get the new ID
                            imported_count += 1
                        except Exception as insert_error:
                            # Handle IntegrityError (unique constraint violations) gracefully
                            from sqlalchemy.exc import IntegrityError
                            if isinstance(insert_error, IntegrityError) or 'UniqueViolation' in str(insert_error) or 'duplicate key' in str(insert_error).lower():
                                # Record already exists, skip it and map the ID if needed
                                if not clear_existing and old_id is not None:
                                    # Try to find the existing record by unique fields
                                    existing = None
                                    
                                    # Use the shared constraint checking logic to find the existing record
                                    # This works for ALL tables that have critical constraints defined
                                    existing = _check_duplicate_by_constraints(
                                        db, model, table_name, record_data, critical_constraints
                                    )
                                    
                                    # Fallback for tables not in critical_constraints (legacy support)
                                    if not existing:
                                        if table_name == 'tenants':
                                            from app.models.tenant import Tenant
                                            existing = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
                                                (Tenant.name == record_data.get('name')) | (Tenant.slug == record_data.get('slug'))
                                            ).first()
                                        elif table_name == 'storage_containers':
                                            from app.models.storage_container import StorageContainer
                                            existing = db.query(StorageContainer).execution_options(skip_tenant_filter=True).filter(
                                                StorageContainer.name == record_data.get('name'),
                                                StorageContainer.tenant_id == record_data.get('tenant_id')
                                            ).first()
                                        elif table_name == 'users':
                                            from app.models.user import User
                                            existing = db.query(User).execution_options(skip_tenant_filter=True).filter(
                                                User.username == record_data.get('username'),
                                                User.tenant_id == record_data.get('tenant_id')
                                            ).first()
                                    
                                    if existing:
                                        # Reactivate if soft-deleted
                                        if hasattr(existing, 'is_active') and not existing.is_active:
                                            existing.is_active = True
                                            db.add(existing)
                                            db.flush()
                                            print(f"  ✓ Reactivated soft-deleted {table_name}: {record_data.get('name', 'N/A')}")

                                        if table_name not in id_mappings:
                                            id_mappings[table_name] = {}
                                        id_mappings[table_name][old_id] = existing.id
                                        print(f"  ⚠ Skipping {table_name} (duplicate): {record_data.get('username') if table_name == 'users' else record_data.get('name', 'N/A')} (existing ID: {existing.id})")
                                        stats['records_skipped_duplicates'] += 1
                                        if table_name not in stats['duplicate_skips_by_table']:
                                            stats['duplicate_skips_by_table'][table_name] = 0
                                        stats['duplicate_skips_by_table'][table_name] += 1
                                    else:
                                        print(f"  ⚠ Skipping {table_name} (unique constraint violation): {str(insert_error)[:100]}")
                                        stats['records_skipped_duplicates'] += 1
                                        if table_name not in stats['duplicate_skips_by_table']:
                                            stats['duplicate_skips_by_table'][table_name] = 0
                                        stats['duplicate_skips_by_table'][table_name] += 1
                                else:
                                    print(f"  ⚠ Skipping {table_name} (unique constraint violation): {str(insert_error)[:100]}")
                                    stats['records_skipped_duplicates'] += 1
                                    if table_name not in stats['duplicate_skips_by_table']:
                                        stats['duplicate_skips_by_table'][table_name] = 0
                                    stats['duplicate_skips_by_table'][table_name] += 1
                                db.rollback()  # Rollback the failed insert
                                continue  # Skip this record
                            else:
                                # Re-raise if it's not a duplicate key error
                                raise
                        
                        # Track ID mappings for foreign key resolution
                        # This is needed when IDs are dropped (both clear_existing=False and clear_existing=True with test-only clearing)
                        if should_drop_ids and old_id is not None:
                            new_id = instance.id
                            if table_name not in id_mappings:
                                id_mappings[table_name] = {}
                            id_mappings[table_name][old_id] = new_id
                        
                        # Track imported ID for foreign key validation
                        if clear_existing and 'id' in record_data:
                            if table_name not in imported_ids:
                                imported_ids[table_name] = set()
                            imported_ids[table_name].add(record_data['id'])
                        elif not clear_existing:
                            # Track new IDs for foreign key validation
                            if table_name not in imported_ids:
                                imported_ids[table_name] = set()
                            imported_ids[table_name].add(instance.id)

                    db.commit()
                    stats['tables_imported'] += 1
                    stats['total_records_imported'] += imported_count
                    print(f"  ✓ Imported {imported_count} records into {table_name}")

                except Exception as e:
                    db.rollback()
                    error_msg = f"Error importing {table_name}: {str(e)}"
                    print(f"  ✗ {error_msg}")
                    stats['errors'].append(error_msg)

            stats['completed_at'] = datetime.utcnow().isoformat()

            if stats['errors']:
                print(f"\n⚠️  Import completed with {len(stats['errors'])} errors")
            else:
                print(f"\n✅ Import completed successfully!")

            print(f"   Tables imported: {stats['tables_imported']}")
            print(f"   Total records: {stats['total_records_imported']}")
            
            if stats.get('records_skipped_missing_models', 0) > 0:
                print(f"\n⚠️  WARNING: {stats['records_skipped_missing_models']} records were SKIPPED because models are not available in this codebase!")
                print(f"   Tables skipped: {', '.join(stats.get('tables_skipped_missing_models', []))}")
                print(f"   These records will be LOST. Upgrade your codebase to restore them.")
            
            if stats['records_skipped_duplicates'] > 0:
                print(f"\n⚠️  WARNING: {stats['records_skipped_duplicates']} records were skipped due to duplicates!")
                print(f"   This may indicate existing data in the database.")
                print(f"   Consider using --clear flag to clear existing data before restore.")
                print(f"   Duplicate skips by table:")
                for table_name, count in stats['duplicate_skips_by_table'].items():
                    print(f"     - {table_name}: {count} records skipped")

        except Exception as e:
            db.rollback()
            error_msg = f"Fatal error during import: {str(e)}"
            print(f"\n❌ {error_msg}")
            stats['errors'].append(error_msg)
            stats['completed_at'] = datetime.utcnow().isoformat()

        return stats

    @staticmethod
    def validate_backup(backup_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate backup data structure

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required keys
        if 'metadata' not in backup_data:
            errors.append("Missing 'metadata' section")
        if 'tables' not in backup_data:
            errors.append("Missing 'tables' section")

        # Check metadata
        metadata = backup_data.get('metadata', {})
        if 'backup_date' not in metadata:
            errors.append("Missing 'backup_date' in metadata")
        if 'version' not in metadata:
            errors.append("Missing 'version' in metadata")

        # Check tables structure
        tables = backup_data.get('tables', {})
        if not isinstance(tables, dict):
            errors.append("'tables' must be a dictionary")
        else:
            for table_name, table_data in tables.items():
                if not isinstance(table_data, dict):
                    errors.append(f"Table '{table_name}' data must be a dictionary")
                elif 'data' not in table_data:
                    errors.append(f"Table '{table_name}' missing 'data' key")

        return len(errors) == 0, errors

    @staticmethod
    def get_backup_summary(backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary statistics of a backup"""
        summary = {
            'backup_date': backup_data.get('metadata', {}).get('backup_date'),
            'version': backup_data.get('metadata', {}).get('version'),
            'total_tables': 0,
            'total_records': 0,
            'tables': []
        }

        tables = backup_data.get('tables', {})
        summary['total_tables'] = len(tables)

        for table_name, table_data in tables.items():
            count = table_data.get('count', 0)
            summary['total_records'] += count
            summary['tables'].append({
                'name': table_name,
                'count': count
            })

        return summary
