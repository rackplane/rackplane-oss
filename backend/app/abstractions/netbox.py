"""
Abstract NetBox Sync Service Interface
Defines the contract for NetBox integration (read-only OSS, bidirectional Premium)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class NetBoxSyncInterface(ABC):
    """Abstract interface for NetBox sync (read-only OSS, bidirectional Premium)"""

    @abstractmethod
    async def pull_devices(self) -> List[Dict[str, Any]]:
        """
        Pull devices from NetBox to RackPlane (OSS: supported)

        Returns:
            List of device dictionaries:
                - name: Device name
                - device_type: Device type
                - serial: Serial number
                - asset_tag: Asset tag
                - rack: Rack information
                - position: U position
                - status: Device status
        """
        pass

    @abstractmethod
    async def push_devices(self, devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Push devices from RackPlane to NetBox (Premium only)

        Args:
            devices: List of device dictionaries to push

        Returns:
            Dict containing:
                - success: Number of devices successfully pushed
                - failed: Number of failed pushes
                - errors: List of error messages

        Raises:
            NotImplementedError: In OSS builds
        """
        pass

    @abstractmethod
    def supports_bidirectional_sync(self) -> bool:
        """
        Check if bidirectional sync is supported

        Returns:
            True for Premium (push supported), False for OSS (read-only)
        """
        pass

    def get_service_name(self) -> str:
        """
        Get the name of the NetBox service implementation

        Returns:
            Service name
        """
        return self.__class__.__name__
