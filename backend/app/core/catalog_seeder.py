import json
import logging
import os
from sqlalchemy.orm import Session
from app.models.catalog_sku import CatalogSKU
from app.core.config import settings

logger = logging.getLogger(__name__)

# Demo API key that gets injected into tenants for demo mode
DEMO_API_KEY = "demo-api-key-for-sample-skus"


def seed_demo_api_customer(services_db: Session):
    """
    Seed a demo ApiCustomer for the demo API key.
    This allows demo instances to access the Global Catalog.
    Only runs in CENTRAL_CATALOG mode (services.rackplane.com).
    """
    from app.models.api_customer import ApiCustomer
    from app.core.api_key_auth import hash_api_key
    
    demo_key_hash = hash_api_key(DEMO_API_KEY)
    
    # Check if demo customer already exists
    existing = services_db.query(ApiCustomer).filter(
        ApiCustomer.api_key_hash == demo_key_hash
    ).first()
    
    if not existing:
        logger.info("Creating demo API customer for Global Catalog access...")
        demo_customer = ApiCustomer(
            api_key_hash=demo_key_hash,
            customer_name="Demo User",
            email="demo@rackplane.com",
            company="RackPlane Demo",
            tier="demo",
            is_active=True,
            rate_limit_hour=100,  # Limited rate for demo
            customer_metadata={"is_demo": True}
        )
        services_db.add(demo_customer)
        services_db.commit()
        logger.info("Demo API customer created successfully")
    else:
        logger.info("Demo API customer already exists")


def seed_catalog(db: Session, services_db: Session):
    """
    Seed the global catalog with sample data.
    Runs when DEMO_MODE=True or CENTRAL_CATALOG=True.
    
    Args:
        db: Tenant database session (for injecting API key into tenant)
        services_db: Services database session (for creating CatalogSKUs)
    """
    import os
    # Case-sensitive match for consistency with other env var checks
    is_central = os.environ.get('CENTRAL_CATALOG', 'false') == 'true'
    
    if not settings.DEMO_MODE and not is_central:
        return
    
    # For CENTRAL_CATALOG mode (services.rackplane.com), seed the demo API customer
    if is_central:
        seed_demo_api_customer(services_db)

    # Load fixture data
    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "fixtures", 
        "catalog_seed.json"
    )
    
    if not os.path.exists(fixture_path):
        logger.warning(f"Catalog seed fixture not found at {fixture_path}")
        return

    try:
        with open(fixture_path, 'r') as f:
            data = json.load(f)
            
        logger.info(f"Checking catalog against {len(data)} SKUs from fixture...")
        
        added_count = 0
        for item in data:
            # Check if SKU exists in Services DB
            exists = services_db.query(CatalogSKU).filter(
                CatalogSKU.vendor == item['vendor'],
                CatalogSKU.sku == item['sku']
            ).first()
            
            if not exists:
                sku = CatalogSKU(**item)
                # Ensure is_active is set
                if 'is_active' not in item:
                    sku.is_active = True
                services_db.add(sku)
                added_count += 1
        
        if added_count > 0:
            services_db.commit()
            logger.info(f"Catalog seeding complete. Added {added_count} new SKUs.")
            
            # Inject Demo API Key into Main Tenant if needed (Tenant DB)
            # In the demo environment, we assume the user is using the primary tenant.
            from app.models.tenant import Tenant
            tenant = db.query(Tenant).order_by(Tenant.id).first()
            if tenant and not tenant.rackplane_api_key:
                logger.info(f"Injecting demo API key for tenant {tenant.name}...")
                tenant.rackplane_api_key = DEMO_API_KEY
                db.add(tenant)
                db.commit()
        else:
            logger.info("Catalog up to date. No new SKUs added.")
        
    except Exception as e:
        logger.error(f"Failed to seed catalog: {e}")
        services_db.rollback()
        db.rollback()
