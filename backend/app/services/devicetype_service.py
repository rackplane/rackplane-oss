"""
Service for fetching NetBox Community devicetype-library data from GitHub.

This service provides methods to browse and fetch device type definitions
from the netbox-community/devicetype-library repository on GitHub.
"""

import os
import json
import time
import yaml
from yaml import SafeLoader
import requests
import hashlib
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from urllib.parse import quote
from app.core.config import settings

logger = logging.getLogger(__name__)

# YAML security limits to prevent YAML bombs (exponentially expanding structures)
YAML_MAX_MAPPING_KEYS = 1000  # Maximum number of keys in a single mapping
YAML_MAX_DEPTH = 50  # Maximum nesting depth


class LimitedSafeLoader(SafeLoader):
    """
    A YAML SafeLoader with additional limits to prevent YAML bombs.
    
    Limits:
    - Maximum mapping keys per node (prevents billion laughs attack)
    - Maximum nesting depth (prevents stack overflow)
    """
    
    def __init__(self, stream: Any, max_keys: int = YAML_MAX_MAPPING_KEYS, max_depth: int = YAML_MAX_DEPTH):
        super().__init__(stream)
        self.max_keys = max_keys
        self.max_depth = max_depth
        self._depth = 0
    
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> Dict:
        """Construct a mapping with size limits."""
        if len(node.value) > self.max_keys:
            raise yaml.YAMLError(
                f"YAML structure too complex: mapping has {len(node.value)} keys, "
                f"maximum allowed is {self.max_keys}"
            )
        self._depth += 1
        if self._depth > self.max_depth:
            raise yaml.YAMLError(
                f"YAML structure too deeply nested: depth {self._depth}, "
                f"maximum allowed is {self.max_depth}"
            )
        try:
            return super().construct_mapping(node, deep)
        finally:
            self._depth -= 1
    
    def construct_sequence(self, node: yaml.SequenceNode, deep: bool = False) -> List:
        """Construct a sequence with depth limits."""
        self._depth += 1
        if self._depth > self.max_depth:
            raise yaml.YAMLError(
                f"YAML structure too deeply nested: depth {self._depth}, "
                f"maximum allowed is {self.max_depth}"
            )
        try:
            return super().construct_sequence(node, deep)
        finally:
            self._depth -= 1


class DeviceTypeService:
    """Service for interacting with NetBox devicetype-library on GitHub."""

    GITHUB_API_BASE = "https://api.github.com"
    REPO_OWNER = "netbox-community"
    REPO_NAME = "devicetype-library"
    DEVICE_TYPES_PATH = "device-types"

    def __init__(self, cache_dir: Optional[str] = None, cache_ttl: int = 3600):
        """
        Initialize the DeviceTypeService.

        Args:
            cache_dir: Directory for caching responses (default: /tmp/devicetype_cache)
            cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.cache_dir = Path(cache_dir or getattr(settings, 'DEVICETYPE_CACHE_DIR', '/tmp/devicetype_cache'))
        self.cache_ttl = cache_ttl or getattr(settings, 'DEVICETYPE_CACHE_TTL', 3600)
        self.github_token = getattr(settings, 'GITHUB_TOKEN', None)
        self.max_file_size = getattr(settings, 'NETBOX_LIBRARY_MAX_FILE_SIZE', 5 * 1024 * 1024)

        # Create cache directory if it doesn't exist.
        # Note: This service may create/modify filesystem paths. Operators should ensure
        # the cache directory location aligns with their deployment's /tmp management.
        # We use exist_ok=True to handle concurrent creation without race conditions.
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate cache directory permissions.
        # We do NOT mutate permissions on existing directories to avoid surprising changes
        # in shared/NFS/container deployments. Instead, we log a warning if the directory
        # is too permissive so operators can adjust it explicitly.
        try:
            st_mode = self.cache_dir.stat().st_mode
            # Check if group or other has any access (0o077 mask)
            if st_mode & 0o077:
                logger.warning(
                    f"Cache directory '{self.cache_dir}' has permissive permissions "
                    f"({oct(st_mode & 0o777)}); consider chmod to 0o700 for security."
                )
        except OSError as e:
            logger.warning(f"Could not check cache directory permissions: {e}")

        # Setup headers for GitHub API
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'RackPlane-DeviceType-Integration'
        }
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'

    def _get_cache_path(self, key: str) -> Path:
        """
        Generate cache file path for a given key.

        Uses SHA-256 hash to ensure safe filesystem names and prevent
        path traversal attacks.
        """
        # Use hash for guaranteed safe filesystem names
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"

    def _read_cache(self, key: str) -> Optional[Union[Dict, List]]:
        """
        Read data from cache if it exists and is not expired.

        Args:
            key: Cache key

        Returns:
            Cached data if valid, None otherwise
        """
        cache_path = self._get_cache_path(key)

        try:
            # Check if cache is expired
            cache_age = time.time() - cache_path.stat().st_mtime
            if cache_age > self.cache_ttl:
                # Cache expired, remove it (missing_ok=True prevents race condition)
                cache_path.unlink(missing_ok=True)
                return None

            # Read cache file
            with open(cache_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Cache doesn't exist
            return None
        except (json.JSONDecodeError, IOError, OSError) as e:
            # Corrupted or inaccessible cache file, try to remove it
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                # Ignore errors during cleanup
                pass
            return None

    def _write_cache(self, key: str, data: Union[Dict, List]) -> None:
        """
        Write data to cache.

        Args:
            key: Cache key
            data: Data to cache (can be dict or list)
        """
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except IOError as e:
            # Cache write failed, log but don't fail the operation
            logger.warning(f"Failed to write cache for {key}: {e}")

    def _make_github_request(self, endpoint: str) -> Dict:
        """
        Make a request to GitHub API with error handling.

        Args:
            endpoint: API endpoint (without base URL)

        Returns:
            JSON response from GitHub

        Raises:
            requests.HTTPError: If request fails
        """
        url = f"{self.GITHUB_API_BASE}{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Check if it's specifically a rate limit issue based on headers
                try:
                    rate_limit_remaining = int(e.response.headers.get('X-RateLimit-Remaining', -1))
                    if rate_limit_remaining == 0:
                        reset_time = e.response.headers.get('X-RateLimit-Reset', 'unknown')
                        raise Exception(f"GitHub API rate limit exceeded. Resets at {reset_time}")
                except (ValueError, TypeError):
                    # Header was malformed, re-raise original error instead of mislabeling
                    pass
                # Not a rate limit issue - could be auth, scope, or other 403
                # Re-raise the original error with status info
            raise

    def list_manufacturers(self, use_cache: bool = True) -> List[str]:
        """
        List all available manufacturers from the devicetype-library.

        Args:
            use_cache: Whether to use cached data (default: True)

        Returns:
            List of manufacturer names (directory names)
        """
        cache_key = "manufacturers"

        # Check cache first
        if use_cache:
            cached_data = self._read_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Fetch from GitHub
        endpoint = f"/repos/{self.REPO_OWNER}/{self.REPO_NAME}/contents/{self.DEVICE_TYPES_PATH}"
        data = self._make_github_request(endpoint)

        # Extract directory names
        manufacturers = [
            item['name'] for item in data
            if item['type'] == 'dir'
        ]
        manufacturers.sort()

        # Cache the result
        self._write_cache(cache_key, manufacturers)

        return manufacturers

    def list_device_types(
        self,
        manufacturer: str,
        use_cache: bool = True
    ) -> List[Dict[str, str]]:
        """
        List all device types for a given manufacturer.

        Args:
            manufacturer: Manufacturer name (directory name)
            use_cache: Whether to use cached data (default: True)

        Returns:
            List of dicts with 'slug' and 'name' keys
            Example: [{'slug': 'c9300-48uxm', 'name': 'Catalyst 9300-48UXM'}, ...]
        """
        cache_key = f"devices_{manufacturer}"

        # Check cache first
        if use_cache:
            cached_data = self._read_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Fetch from GitHub - URL-encode manufacturer to prevent injection
        endpoint = f"/repos/{self.REPO_OWNER}/{self.REPO_NAME}/contents/{self.DEVICE_TYPES_PATH}/{quote(manufacturer, safe='')}"
        data = self._make_github_request(endpoint)

        # Extract YAML files
        device_types = []
        for item in data:
            if item['type'] == 'file' and item['name'].endswith(('.yaml', '.yml')):
                slug = item['name'].replace('.yaml', '').replace('.yml', '')
                device_types.append({
                    'slug': slug,
                    'name': slug.replace('-', ' ').replace('_', ' ').title(),
                    'download_url': item['download_url']
                })

        device_types.sort(key=lambda x: x['slug'])

        # Cache the result
        self._write_cache(cache_key, device_types)

        return device_types

    def fetch_device_type(
        self,
        manufacturer: str,
        slug: str,
        use_cache: bool = True
    ) -> Dict:
        """
        Fetch and parse a specific device type YAML file.

        Args:
            manufacturer: Manufacturer name
            slug: Device type slug (filename without .yaml extension)
            use_cache: Whether to use cached data (default: True)

        Returns:
            Parsed YAML data as dictionary

        Raises:
            Exception: If device type not found or YAML parsing fails
        """
        cache_key = f"devicetype_{manufacturer}_{slug}"

        # Check cache first
        if use_cache:
            cached_data = self._read_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Get device list to find download URL
        device_types = self.list_device_types(manufacturer, use_cache=use_cache)
        device_info = next((d for d in device_types if d['slug'] == slug), None)

        if not device_info:
            raise Exception(f"Device type '{slug}' not found for manufacturer '{manufacturer}'")

        # Download YAML content with size limit
        try:
            response = requests.get(device_info['download_url'], timeout=30, stream=True)
            response.raise_for_status()

            # Check content length to prevent DoS
            content_length = response.headers.get('content-length')
            if content_length:
                try:
                    parsed_content_length = int(content_length)
                except (TypeError, ValueError):
                    # Malformed content-length header; fall back to streaming size check only
                    parsed_content_length = None

                if parsed_content_length is not None and parsed_content_length > self.max_file_size:
                    raise Exception(
                        f"YAML file too large: {parsed_content_length} bytes (max {self.max_file_size})"
                    )

            # Read with size limit (streaming check as backup)
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.max_file_size:
                    raise Exception(f"YAML file exceeds size limit of {self.max_file_size} bytes")

            # SECURITY: Parse YAML with LimitedSafeLoader (subclass of yaml.SafeLoader)
            # which adds depth/complexity limits to prevent YAML bombs (billion laughs).
            # Using yaml.load() with explicit Loader parameter is safe when Loader
            # inherits from SafeLoader - this prevents arbitrary code execution.
            device_data = yaml.load(content.decode('utf-8'), Loader=LimitedSafeLoader)

            # Add metadata
            device_data['_metadata'] = {
                'manufacturer': manufacturer,
                'slug': slug,
                'source': 'netbox-community/devicetype-library'
            }

            # Cache the result
            self._write_cache(cache_key, device_data)

            return device_data

        except yaml.YAMLError as e:
            logger.error(f"YAML parse error for {manufacturer}/{slug}: {e}")
            raise Exception(f"Failed to parse device type definition for {manufacturer}/{slug}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Download error for {manufacturer}/{slug}: {e}")
            raise Exception(f"Failed to download device type for {manufacturer}/{slug}")

    def search_device_types(
        self,
        query: str,
        manufacturer: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, str]]:
        """
        Search for device types across all or specific manufacturer(s).

        Args:
            query: Search query (case-insensitive, matches slug or name)
            manufacturer: Optional manufacturer to restrict search to
            limit: Maximum number of results (default: 50)

        Returns:
            List of matching device types with manufacturer info
            Example: [{'manufacturer': 'Cisco', 'slug': 'c9300-48uxm', 'name': '...'}, ...]
        """
        query_lower = query.lower()
        results = []

        # Determine which manufacturers to search
        manufacturers_to_search = [manufacturer] if manufacturer else self.list_manufacturers()

        for mfr in manufacturers_to_search:
            # Stop early if we've already collected enough results
            if len(results) >= limit:
                break

            try:
                # Use cache to avoid repeated GitHub API calls
                devices = self.list_device_types(mfr, use_cache=True)
                for device in devices:
                    # Check if query matches slug or name
                    if (query_lower in device['slug'].lower() or
                        query_lower in device['name'].lower()):
                        results.append({
                            'manufacturer': mfr,
                            'slug': device['slug'],
                            'name': device['name']
                        })

                        # Stop if we've reached the limit
                        if len(results) >= limit:
                            return results
            except Exception as e:
                # Log error but continue searching other manufacturers
                logger.warning(f"Failed to search manufacturer {mfr}: {e}")
                continue

        return results

    def clear_cache(self) -> int:
        """
        Clear all cached data.

        Returns:
            Number of cache files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError as exc:
                # Best-effort cache clearing: log and continue on failure
                logger.warning(f"Failed to delete cache file {cache_file}: {exc}")
        return count
