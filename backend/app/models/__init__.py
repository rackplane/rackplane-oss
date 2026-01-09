# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0
# OSS Version - Premium models excluded

"""Database Models - OSS Edition"""

from app.models.tenant import Tenant
from app.models.asset import Asset, AssetStatus, AssetLifecycleEvent
from app.models.asset_type import AssetTypeModel
from app.models.location import Datacenter, Room, Rack, RackPosition
from app.models.storage_container import StorageContainer
from app.models.maintenance import MaintenanceRecord, MaintenancePrediction
from app.models.workflow import Workflow, WorkflowStep, WorkflowExecution
from app.models.environmental import EnvironmentalSensor, EnvironmentalReading
from app.models.capacity import CapacityMetrics, PowerMetrics, CoolingMetrics
from app.models.network import NetworkPort, NetworkConnection, VLAN
from app.models.port_template import PortTemplate
from app.models.user import User
from app.models.user_role import UserRole
from app.models.connections import Connection, ConnectionEnd
from app.models.audit_log import AuditLog
from app.models.api_key import ApiKey
from app.models.print_job import PrintJob, PrintAgent, PrintJobStatus, PrintJobType
from app.models.container_stock_threshold import ContainerStockThreshold
from app.models.vendor_sku import VendorSKU
from app.models.api_customer import ApiCustomer, ApiUsageLog
from app.models.customer_quota import CustomerQuota, QuotaTransaction
from app.models.catalog_sku import CatalogSKU

from app.models.catalog_submission import CatalogSubmission
from app.models.cable_assembly import CableAssembly, AssemblyStatus

from app.models.network_cable import NetworkCable
from app.models.power_cable import PowerCable
from app.models.environment import Environment
from app.models.cached_sku import CachedSKU

# Optional models (graceful degradation)
try:
    from app.models.ocr_scan import OcrScan
except ImportError:
    OcrScan = None

try:
    from app.models.shopping_cart import ShoppingCart, CartItem
except ImportError:
    ShoppingCart = None
    CartItem = None

# ServiceContract is EXCLUDED in OSS build
# FSApiUsage, GlobalProductCatalog, FSOrderCache, FSWarrantyCache are premium

__all__ = [
    "Tenant",
    "Asset", "AssetStatus", "AssetLifecycleEvent",
    "AssetTypeModel",
    "Datacenter", "Room", "Rack", "RackPosition",
    "StorageContainer",
    "ContainerStockThreshold",
    "MaintenanceRecord", "MaintenancePrediction",
    "Workflow", "WorkflowStep", "WorkflowExecution",
    "EnvironmentalSensor", "EnvironmentalReading",
    "CapacityMetrics", "PowerMetrics", "CoolingMetrics",
    "NetworkPort", "NetworkConnection", "VLAN", "PortTemplate",
    "User", "UserRole",
    "Connection", "ConnectionEnd",
    "AuditLog",
    "ApiKey",
    "VendorSKU",
    "PrintJob", "PrintAgent", "PrintJobStatus", "PrintJobType",
    "ApiCustomer", "ApiUsageLog",
    "CustomerQuota", "QuotaTransaction",
    "OcrScan",
    "ShoppingCart", "CartItem",
    "CatalogSKU", "CatalogSubmission",
    "CableAssembly", "AssemblyStatus",
    "NetworkCable", "PowerCable", "Environment", "CachedSKU",
]
