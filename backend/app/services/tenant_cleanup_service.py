from sqlalchemy.orm import Session
from sqlalchemy import text, MetaData, Table
from sqlalchemy.schema import CreateTable
from sqlalchemy.exc import NoSuchTableError
from app.api.v1.tenants import tenant_tables
import logging

logger = logging.getLogger(__name__)

def delete_tenant_scoped_data(db: Session, tenant_id: int, tenant_uuid: str = None):
    """
    Shared helper to delete all tenant-scoped data in the correct order.
    Handles complicated dependencies like api_usage_logs (via api_customers)
    and api_customers type mismatches.
    
    Uses SQLAlchemy introspection (Table reflection) to prevent SQL injection.
    """
    metadata = MetaData()
    
    # 1. Handle api_usage_logs explicitly first (indirect dependency)
    # They are linked to api_customers, not directly to tenant in some schemas.
    # We use explicit parameterized SQL here because the query structure is complex
    # involving subqueries, which is cleaner in SQL than ORM given we want bulk delete.
    try:
        # Construct parameters ensuring we handle UUID if provided
        params = {"tenant_id_str": str(tenant_id)}
        
        delete_query = """
            DELETE FROM api_usage_logs 
            WHERE customer_id IN (
                SELECT id FROM api_customers 
                WHERE CAST(tenant_id AS VARCHAR) = :tenant_id_str
        """
        
        if tenant_uuid:
            delete_query += " OR tenant_id = :tenant_uuid"
            params["tenant_uuid"] = tenant_uuid
            
        delete_query += "\n)"
        
        db.execute(text(delete_query), params)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting api_usage_logs: {e}")

    # 2. Iterate through all tables in the defined order
    for table_name in tenant_tables:
        if table_name == 'api_usage_logs':
            continue

        try:
            # Load table definition from database to ensure it exists and we use safe object
            try:
                table = Table(table_name, metadata, autoload_with=db.bind)
            except NoSuchTableError:
                logger.warning(f"Table {table_name} not found in database, skipping.")
                continue

            # Special handling for api_customers type mismatch (varchar vs int)
            # The column might be defined as VARCHAR but contains "123"
            if table_name == 'api_customers':
                # For this specific edge case, we revert to text() but with strict parameterization
                # because SQLAlchemy Table delete() with cast() is verbose.
                
                params = {"tenant_id_str": str(tenant_id)}
                query_str = f"DELETE FROM {table_name} WHERE CAST(tenant_id AS VARCHAR) = :tenant_id_str"
                if tenant_uuid:
                    query_str += " OR tenant_id = :tenant_uuid"
                    params["tenant_uuid"] = tenant_uuid
                    
                db.execute(text(query_str), params)
            
            else:
                # Standard deletion using SQLAlchemy Table object
                # This constructs: DELETE FROM table WHERE tenant_id = :tenant_id
                stmt = table.delete().where(table.c.tenant_id == tenant_id)
                db.execute(stmt)

            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting from {table_name}: {e}")
            
            # Critical tables should stop the process if deletion fails
            critical_tables = ['storage_containers', 'assets', 'racks', 'rooms', 'datacenters']
            if table_name in critical_tables:
                raise Exception(f"CRITICAL: Failed to clean up {table_name} for tenant {tenant_id}. Aborting.") from e
