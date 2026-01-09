from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.core.database import Base

class GlobalProductCatalog(Base):
    """
    Global catalog of products from all supported external vendors.
    Shared across all tenants to minimize API calls and storage.
    Supports FS.com, NVIDIA, DigiKey, QSFPTEK, etc.
    """
    __tablename__ = "global_product_catalog"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Vendor Identification
    vendor = Column(String(50), nullable=False, index=True)  # Distributor/Source: FS.com, DigiKey
    vendor_product_id = Column(String(100), nullable=False, index=True) # Distributor SKU: "11552", "4429-O-100N-O-DR8-ND"
    
    # Core Standardized Info
    name = Column(String(500), nullable=False)
    manufacturer = Column(String(100), nullable=True, index=True) # Maker: "Infraeo Inc.", "FS.com", "NVIDIA"
    part_number = Column(String(200), nullable=True, index=True)  # Manufacturer Part Number
    
    # Searchable Attributes (extracted/parsed or provided)
    category = Column(String(100), nullable=True, index=True)    # optical_transceiver, cable, switch
    form_factor = Column(String(50), nullable=True, index=True)  # QSFP28, SFP+, 1U
    speed = Column(String(50), nullable=True)                    # 100G, 400G
    interface = Column(String(100), nullable=True)               # SR4, LR4, Copper
    
    # Raw Data Storage
    specs = Column(JSON, nullable=True)       # Normalized key-value specifications
    raw_data = Column(JSON, nullable=True)    # Full original API response
    
    # Pricing & Metadata (Snapshot)
    price_usd = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    datasheet_url = Column(String(500), nullable=True)
    product_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # Cache management
    fetched_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    last_updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        # Validate uniqueness of Vendor + Vendor SKU
        Index('ix_global_catalog_vendor_id', 'vendor', 'vendor_product_id', unique=True),
        # Optimize composite search
        Index('ix_global_catalog_search', 'name', 'part_number', 'manufacturer'),
    )
