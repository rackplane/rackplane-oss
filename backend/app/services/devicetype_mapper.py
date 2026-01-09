"""
Mapper for transforming NetBox devicetype-library YAML data to VendorSKU format.

This service provides methods to convert NetBox device type definitions
into RackPlane VendorSKU format for auto-populating asset fields.
"""

from typing import Dict, Optional, List, Tuple
from app.core.config import settings


class DeviceTypeMapper:
    """Maps NetBox device type data to RackPlane VendorSKU format."""

    # GitHub repository configuration
    GITHUB_REPO_BASE = "https://github.com/netbox-community/devicetype-library/tree/master/device-types"

    # Asset type inference thresholds
    MAX_RACK_UNITS = 100  # Standard rack is 42U, but allow headroom for validation
    MIN_SWITCH_PORTS = 24  # Minimum interface count to classify as network switch
    MIN_PDU_POWER_PORTS = 4  # Minimum power ports to classify as PDU
    MIN_CONSOLE_SERVER_PORTS = 4  # Minimum console ports to classify as console server
    MIN_SERVER_RACK_UNITS = 4  # Rack units threshold for server classification (vs appliance)

    @staticmethod
    def get_vendor_name() -> str:
        """Get configured vendor name for NetBox Library imports."""
        return getattr(settings, 'NETBOX_LIBRARY_VENDOR_NAME', 'NetBox Library')

    @staticmethod
    def to_vendor_sku(device_type: Dict, manufacturer: str) -> Dict:
        """
        Transform NetBox device type YAML to VendorSKU format.

        Args:
            device_type: Parsed NetBox YAML data
            manufacturer: Manufacturer name from directory structure

        Returns:
            Dictionary with VendorSKU fields
        """
        # Extract metadata
        metadata = device_type.get('_metadata', {})
        slug = metadata.get('slug', '')
        model = device_type.get('model', slug)

        # Generate unique SKU identifier
        sku = DeviceTypeMapper._generate_sku(manufacturer, slug)

        # Infer asset type
        asset_type = DeviceTypeMapper.infer_asset_type(device_type, model)

        # Build specifications from NetBox fields
        specifications = DeviceTypeMapper.build_specifications(device_type)

        # Build VendorSKU data structure
        vendor_sku_data = {
            'vendor': DeviceTypeMapper.get_vendor_name(),
            'sku': sku,
            'part_number': model,
            'name': model,
            'manufacturer': manufacturer,
            'asset_type': asset_type,
            'specifications': specifications,
            'description': device_type.get('comments', ''),
            'datasheet_url': None,
            'vendor_url': f"{DeviceTypeMapper.GITHUB_REPO_BASE}/{manufacturer}/{slug}.yaml",
            'is_active': True,
        }

        return vendor_sku_data

    @staticmethod
    def _generate_sku(manufacturer: str, slug: str) -> str:
        """
        Generate a unique SKU identifier for NetBox device types.

        Format: netbox_{manufacturer}_{slug}

        Args:
            manufacturer: Manufacturer name
            slug: Device type slug

        Returns:
            Unique SKU string
        """
        # Normalize to lowercase and replace spaces with underscores
        mfr_normalized = manufacturer.lower().replace(' ', '_').replace('-', '_')
        slug_normalized = slug.lower().replace(' ', '_')

        return f"netbox_{mfr_normalized}_{slug_normalized}"

    @staticmethod
    def build_specifications(device_type: Dict) -> Dict:
        """
        Build specifications JSON from NetBox device type fields.

        Args:
            device_type: NetBox device type data

        Returns:
            Specifications dictionary
        """
        # Validate input is a dictionary
        if not isinstance(device_type, dict):
            return {}

        specs = {}

        # Physical dimensions - with type checking and range validation
        u_height = device_type.get('u_height')
        if u_height is not None and isinstance(u_height, (int, float)) and 0 < u_height <= DeviceTypeMapper.MAX_RACK_UNITS:
            specs['u_height'] = u_height

        weight = device_type.get('weight')
        if weight is not None and isinstance(weight, (int, float)) and weight > 0:
            specs['weight_kg'] = weight

        is_full_depth = device_type.get('is_full_depth')
        if isinstance(is_full_depth, bool):
            specs['is_full_depth'] = is_full_depth

        # Interface counts
        if 'interfaces' in device_type:
            interfaces = device_type['interfaces']
            if isinstance(interfaces, list):
                specs['network_ports'] = len(interfaces)
                specs['interface_details'] = DeviceTypeMapper._summarize_interfaces(interfaces)

        # Console ports
        if 'console-ports' in device_type:
            console_ports = device_type['console-ports']
            if isinstance(console_ports, list):
                specs['console_ports'] = len(console_ports)

        # Power ports
        if 'power-ports' in device_type:
            power_ports = device_type['power-ports']
            if isinstance(power_ports, list):
                specs['power_ports'] = len(power_ports)
                specs['power_port_details'] = DeviceTypeMapper._summarize_power_ports(power_ports)

        # Module bays
        if 'module-bays' in device_type:
            module_bays = device_type['module-bays']
            if isinstance(module_bays, list):
                specs['module_bays'] = len(module_bays)

        # Device bays
        if 'device-bays' in device_type:
            device_bays = device_type['device-bays']
            if isinstance(device_bays, list):
                specs['device_bays'] = len(device_bays)

        # Front/rear image
        if 'front_image' in device_type:
            specs['front_image'] = device_type['front_image']

        if 'rear_image' in device_type:
            specs['rear_image'] = device_type['rear_image']

        # Airflow
        if 'airflow' in device_type:
            specs['airflow'] = device_type['airflow']

        # Subdevice role
        if 'subdevice_role' in device_type:
            specs['subdevice_role'] = device_type['subdevice_role']

        return specs

    @staticmethod
    def _summarize_interfaces(interfaces: List[Dict]) -> Dict:
        """
        Summarize network interfaces by type.

        Args:
            interfaces: List of interface definitions

        Returns:
            Dictionary with interface type counts
        """
        summary = {}

        for iface in interfaces:
            iface_type = iface.get('type', 'unknown')
            summary[iface_type] = summary.get(iface_type, 0) + 1

        return summary

    @staticmethod
    def _summarize_power_ports(power_ports: List[Dict]) -> List[Dict]:
        """
        Summarize power port details.

        Args:
            power_ports: List of power port definitions

        Returns:
            List of power port summaries
        """
        summary = []

        for port in power_ports:
            port_info = {
                'name': port.get('name', ''),
                'type': port.get('type', ''),
            }

            if 'maximum_draw' in port:
                port_info['maximum_draw_watts'] = port['maximum_draw']

            if 'allocated_draw' in port:
                port_info['allocated_draw_watts'] = port['allocated_draw']

            summary.append(port_info)

        return summary

    @staticmethod
    def infer_asset_type(device_type: Dict, model: str) -> str:
        """
        Infer asset type from device characteristics using heuristics.

        Asset types:
        - switch: Network switches
        - router: Network routers
        - server: Servers and compute devices
        - storage: Storage arrays
        - pdu: Power distribution units
        - ups: Uninterruptible power supplies
        - firewall: Security appliances
        - load_balancer: Load balancers
        - console_server: Console/terminal servers
        - other: Unknown/other types

        Args:
            device_type: NetBox device type data
            model: Device model name

        Returns:
            Inferred asset type string
        """
        model_lower = model.lower()

        # Check model name for common patterns
        if any(keyword in model_lower for keyword in ['switch', 'catalyst', 'nexus', 'arista']):
            return 'switch'

        if any(keyword in model_lower for keyword in ['router', 'asr', 'isr', 'mx', 'acx']):
            return 'router'

        if any(keyword in model_lower for keyword in ['server', 'poweredge', 'proliant', 'thinkserver', 'ucs']):
            return 'server'

        if any(keyword in model_lower for keyword in ['storage', 'powerstore', 'unity', 'netapp', 'isilon']):
            return 'storage'

        if any(keyword in model_lower for keyword in ['pdu', 'power distribution']):
            return 'pdu'

        if any(keyword in model_lower for keyword in ['ups', 'uninterruptible']):
            return 'ups'

        if any(keyword in model_lower for keyword in ['firewall', 'asa', 'fortigate', 'palo alto', 'checkpoint']):
            return 'firewall'

        if any(keyword in model_lower for keyword in ['load balancer', 'f5', 'big-ip', 'netscaler']):
            return 'load_balancer'

        if any(keyword in model_lower for keyword in ['console server', 'terminal server', 'avocent']):
            return 'console_server'

        # Check interface characteristics
        interfaces = device_type.get('interfaces', [])
        if isinstance(interfaces, list):
            interface_count = len(interfaces)

            # Many network interfaces suggest a switch
            if interface_count >= DeviceTypeMapper.MIN_SWITCH_PORTS:
                return 'switch'

            # Few interfaces with high speed might be a router or firewall
            if interface_count > 0 and interface_count < DeviceTypeMapper.MIN_SWITCH_PORTS:
                # Check for high-speed interfaces
                has_high_speed = any(
                    iface.get('type', '').lower() in ['100gbase-x-qsfp28', '40gbase-x-qsfp+', '10gbase-x-sfp+']
                    for iface in interfaces
                )
                if has_high_speed:
                    return 'router'

        # Check power ports (suggest PDU or UPS)
        power_ports = device_type.get('power-ports', [])
        if isinstance(power_ports, list) and len(power_ports) > DeviceTypeMapper.MIN_PDU_POWER_PORTS:
            # Many power ports suggest PDU
            return 'pdu'

        # Check for console ports (suggest console server)
        console_ports = device_type.get('console-ports', [])
        if isinstance(console_ports, list) and len(console_ports) > DeviceTypeMapper.MIN_CONSOLE_SERVER_PORTS:
            return 'console_server'

        # Check U height for size-based heuristics
        u_height = device_type.get('u_height')
        if u_height:
            # Large devices (4U+) with no interfaces might be storage or servers
            if u_height >= DeviceTypeMapper.MIN_SERVER_RACK_UNITS and len(interfaces) == 0:
                return 'storage'

        # Default to 'other' if we can't determine
        return 'other'

    @staticmethod
    def validate_device_type(device_type: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate that a device type has required fields.

        Args:
            device_type: NetBox device type data

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for required fields
        if 'model' not in device_type or not device_type['model']:
            return False, "Missing required field: model"

        # Metadata should be added by DeviceTypeService
        if '_metadata' not in device_type:
            return False, "Missing metadata (manufacturer, slug)"

        metadata = device_type['_metadata']
        if 'manufacturer' not in metadata:
            return False, "Missing manufacturer in metadata"

        if 'slug' not in metadata:
            return False, "Missing slug in metadata"

        return True, None
