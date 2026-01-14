import json
import requests
import time
from typing import Dict, List, Optional, Any, Union
import os
from dataclasses import dataclass
from dotenv import load_dotenv


def safe_get(obj: Any, key: str, default: Any = "N/A") -> Any:
    """
    Safely get a value from a dictionary-like object.
    Returns 'N/A' if obj is a string or doesn't have the get method.
    """
    if isinstance(obj, str) or not hasattr(obj, 'get'):
        return default
    return obj.get(key, default)


def safe_contains(obj: Any, key: str) -> bool:
    """
    Safely check if a key exists in a dictionary-like object.
    Returns False if obj is a string or doesn't support 'in' operator.
    """
    if isinstance(obj, str) or not isinstance(obj, dict):
        return False
    return key in obj


def safe_access(obj: Any, key: str, default: Any = "N/A") -> Any:
    """
    Safely access a dictionary value using bracket notation.
    Returns default if obj is a string or doesn't support bracket access.
    """
    if isinstance(obj, str) or not hasattr(obj, '__getitem__'):
        return default
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


@dataclass
class MistConfig:
    """Configuration for Mist API client"""
    token: str
    org_id: str
    host: str = "api.mist.com"
    timeout: int = 30
    max_retries: int = 3


class MistBulkTopologyClient:
    """
    Mist REST API client for efficient bulk topology retrieval in non-EVPN environments.
    Uses organization-level endpoints to minimize API calls and rate limiting impact.
    """
    
    def __init__(self, config: MistConfig):
        self.config = config
        self.base_url = f"https://{config.host}/api/v1"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {config.token}'
        }
        self.topology_cache = {}
        self.api_call_count = 0
    
    def get_complete_topology(self) -> Dict:
        """
        Retrieve complete non-EVPN topology for entire organization
        using site-level stats to get LLDP and port information
        """
        print("Fetching complete organization topology...")
        self.api_call_count = 0
        
        # Step 1: Single call for ALL devices across ALL sites
        all_devices = self._get_organization_inventory()
        
        # Step 2: Get sites list for site-level stats calls
        sites = self._get_sites_from_devices(all_devices)
        
        # Step 3: Get site information (names, addresses, etc.)
        sites_info = self._get_sites_info(sites)
        
        # Step 4: Get detailed stats from each site (includes LLDP data)
        all_stats = self._get_sites_stats(sites)
        
        # Step 5: Build complete topology map locally
        topology = self._build_topology_map(all_devices, all_stats, sites_info)
        
        # Optional Step 6: Get discovered switches (requires site iteration)
        if self._needs_discovered_switches():
            topology['discovered_switches'] = self._get_discovered_switches_bulk(topology['sites'])
        
        topology['api_calls_used'] = self.api_call_count
        return topology
    
    def _get_organization_inventory(self) -> List[Dict]:
        """Get all devices across organization in single API call"""
        url = f"{self.base_url}/orgs/{self.config.org_id}/inventory"
        print(f"API Call {self.api_call_count + 1}: Getting organization inventory...")
        result = self._make_request(url)
        return result if isinstance(result, list) else []
    
    def _get_sites_from_devices(self, devices: List[Dict]) -> List[str]:
        """Extract unique site IDs from device inventory"""
        sites = set()
        for device in devices:
            site_id = safe_get(device, 'site_id')
            if site_id and site_id != 'unassigned':
                sites.add(site_id)
        return list(sites)
    
    def _get_sites_info(self, site_ids: List[str]) -> Dict[str, Dict]:
        """Get site information including names for the given site IDs"""
        sites_info = {}
        
        # Get organization sites
        url = f"{self.base_url}/orgs/{self.config.org_id}/sites"
        print(f"API Call {self.api_call_count + 1}: Getting organization sites...")
        org_sites = self._make_request(url)
        
        if org_sites:
            for site in org_sites:
                site_id = safe_get(site, 'id')
                if site_id in site_ids:
                    sites_info[site_id] = {
                        'site_id': site_id,
                        'site_name': safe_get(site, 'name', f'Site-{site_id[:8]}'),
                        'address': safe_get(site, 'address', 'Unknown'),
                        'timezone': safe_get(site, 'timezone', 'Unknown'),
                        'country_code': safe_get(site, 'country_code', 'Unknown')
                    }
        
        # Fill in any missing sites with default info
        for site_id in site_ids:
            if site_id not in sites_info:
                sites_info[site_id] = {
                    'site_id': site_id,
                    'site_name': f'Site-{site_id[:8]}',
                    'address': 'Unknown',
                    'timezone': 'Unknown',
                    'country_code': 'Unknown'
                }
        
        return sites_info
    
    def _get_sites_stats(self, sites: List[str]) -> List[Dict]:
        """Get device statistics from all sites (includes LLDP and port data)"""
        all_stats = []
        for site_id in sites:
            url = f"{self.base_url}/sites/{site_id}/stats/devices"
            print(f"API Call {self.api_call_count + 1}: Getting device statistics for site {site_id[:8]}...")
            site_stats = self._make_request(url)
            if site_stats:
                all_stats.extend(site_stats)
        return all_stats
    
    def _build_topology_map(self, devices: List[Dict], stats: List[Dict], sites_info: Dict[str, Dict]) -> Dict:
        """
        Process bulk data locally to build complete topology map
        without additional API calls
        """
        # Create lookup tables for efficient processing
        stats_by_mac = {}
        for stat in stats:
            if isinstance(stat, dict) and 'mac' in stat:
                stats_by_mac[safe_access(stat, 'mac')] = stat
        
        topology = {
            'organization_id': self.config.org_id,
            'total_devices': len(devices),
            'sites': {},
            'devices_by_type': {'switch': [], 'ap': [], 'gateway': []},
            'topology_links': [],
            'device_connections': {},
            'timestamp': int(time.time())
        }
        
        # Process each device from inventory
        for device in devices:
            site_id = safe_get(device, 'site_id', 'unassigned')
            device_type = safe_get(device, 'type', 'unknown')
            device_mac = safe_get(device, 'mac')
            
            # Initialize site if not exists
            if site_id not in topology['sites']:
                site_info = sites_info.get(site_id, {})
                topology['sites'][site_id] = {
                    'site_id': site_id,
                    'site_name': safe_get(site_info, 'site_name', f'Site-{site_id[:8]}'),
                    'address': safe_get(site_info, 'address', 'Unknown'),
                    'timezone': safe_get(site_info, 'timezone', 'Unknown'),
                    'country_code': safe_get(site_info, 'country_code', 'Unknown'),
                    'devices': [],
                    'device_count': 0
                }
            
            # Build device entry with stats if available
            device_entry = {
                'name': safe_get(device, 'name'),
                'mac': device_mac,
                'serial': safe_get(device, 'serial'),
                'model': safe_get(device, 'model'),
                'type': device_type,
                'site_id': site_id
            }
            
            # Merge statistics if available
            if device_mac in stats_by_mac:
                device_stats = stats_by_mac[device_mac]
                device_entry['status'] = safe_get(device_stats, 'status', 'unknown')
                device_entry['uptime'] = safe_get(device_stats, 'uptime')
                device_entry['version'] = safe_get(device_stats, 'version')
                
                # Extract connectivity information
                connections = self._extract_connections_from_stats(device_stats)
                if connections:
                    device_entry['connections'] = connections
                    topology['device_connections'][device_mac] = connections
                    
                    # Build topology links
                    for conn in connections:
                        topology['topology_links'].append({
                            'source_mac': device_mac,
                            'source_port': safe_access(conn, 'port'),
                            'source_name': safe_get(device, 'name'),
                            'target_mac': safe_get(conn, 'neighbor_mac'),
                            'target_port': safe_get(conn, 'neighbor_port'),
                            'link_status': safe_get(conn, 'status', 'up'),
                            'speed_mbps': safe_get(conn, 'speed'),
                            'protocol': safe_get(conn, 'protocol', 'LLDP')
                        })
            
            # Add to appropriate collections
            topology['sites'][site_id]['devices'].append(device_entry)
            topology['sites'][site_id]['device_count'] += 1
            
            if device_type in topology['devices_by_type']:
                topology['devices_by_type'][device_type].append(device_entry)
        
        # Calculate topology statistics
        topology['statistics'] = self._calculate_topology_stats(topology)
        
        return topology
    
    def _extract_connections_from_stats(self, device_stats: Dict) -> List[Dict]:
        """Extract all connectivity information from device statistics"""
        connections = []
        
        # Process port statistics
        if safe_contains(device_stats, 'port_stat'):
            for port in safe_access(device_stats, 'port_stat', []):
                if safe_get(port, 'up'):
                    connection = {
                        'port': safe_get(port, 'port_id'),
                        'status': 'up',
                        'speed': safe_get(port, 'speed'),
                        'rx_bytes': safe_get(port, 'rx_bytes', 0),
                        'tx_bytes': safe_get(port, 'tx_bytes', 0)
                    }
                    
                    # Add neighbor information if available
                    if safe_get(port, 'neighbor_mac'):
                        connection.update({
                            'neighbor_mac': safe_access(port, 'neighbor_mac'),
                            'neighbor_port': safe_get(port, 'neighbor_port'),
                            'neighbor_system': safe_get(port, 'neighbor_system_name')
                        })
                    
                    connections.append(connection)
        
        # Process LLDP information (primary source for topology connections)
        if safe_contains(device_stats, 'lldp_stat'):
            for lldp in safe_access(device_stats, 'lldp_stat', []):
                connection = {
                    'port': safe_get(lldp, 'local_port_id') or safe_get(lldp, 'port_id'),
                    'neighbor_mac': safe_get(lldp, 'chassis_id'),
                    'neighbor_port': safe_get(lldp, 'port_id'),
                    'neighbor_system': safe_get(lldp, 'system_name'),
                    'neighbor_description': safe_get(lldp, 'port_desc'),
                    'protocol': 'LLDP',
                    'status': 'discovered'
                }
                connections.append(connection)
        
        return connections
    
    def _calculate_topology_stats(self, topology: Dict) -> Dict:
        """Calculate topology statistics from processed data"""
        total_links = len(topology['topology_links'])
        unique_links = len(set(
            (min(safe_access(link, 'source_mac', ''), safe_get(link, 'target_mac', '')),
             max(safe_access(link, 'source_mac', ''), safe_get(link, 'target_mac', '')))
            for link in topology['topology_links']
            if safe_get(link, 'target_mac')
        ))
        
        return {
            'total_sites': len(topology['sites']),
            'total_devices': topology['total_devices'],
            'total_switches': len(topology['devices_by_type']['switch']),
            'total_aps': len(topology['devices_by_type']['ap']),
            'total_gateways': len(topology['devices_by_type']['gateway']),
            'total_connections': total_links,
            'unique_links': unique_links,
            'devices_with_connections': len(topology['device_connections'])
        }
    
    def _needs_discovered_switches(self) -> bool:
        """Determine if discovered switches retrieval is needed"""
        return False
    
    def _get_discovered_switches_bulk(self, sites: Dict) -> Dict:
        """
        Get discovered switches for all sites (requires site-level calls)
        Only use when unmanaged device discovery is essential
        """
        discovered = {}
        for site_id in sites.keys():
            url = f"{self.base_url}/sites/{site_id}/discovered_switches"
            print(f"Additional API Call: Getting discovered switches for site {site_id}")
            result = self._make_request(url)
            if result:
                discovered[site_id] = result
        return discovered
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """Make API request with error handling and rate limiting"""
        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=self.config.timeout)
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limit reached, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                self.api_call_count += 1
                return response.json()
                
            except requests.exceptions.Timeout:
                if attempt == self.config.max_retries - 1:
                    print(f"Timeout error after {self.config.max_retries} attempts: {url}")
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    print(f"Error making request to {url}: {e}")
                    return None
                time.sleep(2 ** attempt)
        
        return None
    
    def export_topology_to_file(self, topology: Dict, filename: str = "topology.json"):
        """Export topology to JSON file"""
        with open(filename, 'w') as f:
            json.dump(topology, f, indent=2)
        print(f"Topology exported to {filename}")
    
    def export_topology_summary(self, topology: Dict, filename: str = "mist_topology_summary.json"):
        """Export topology summary to JSON file"""
        stats = safe_get(topology, 'statistics', {})
        
        summary = {
            "summary_info": {
                "organization_id": safe_get(topology, 'organization_id', 'Unknown'),
                "api_calls_used": safe_get(topology, 'api_calls_used', 0),
                "timestamp": safe_get(topology, 'timestamp', 'Unknown'),
                "discovery_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(safe_get(topology, 'timestamp', time.time())))
            },
            "infrastructure": {
                "sites": safe_get(stats, 'total_sites', 0),
                "total_devices": safe_get(stats, 'total_devices', 0),
                "switches": safe_get(stats, 'total_switches', 0),
                "access_points": safe_get(stats, 'total_aps', 0),
                "gateways": safe_get(stats, 'total_gateways', 0)
            },
            "connectivity": {
                "total_connections": safe_get(stats, 'total_connections', 0),
                "unique_links": safe_get(stats, 'unique_links', 0),
                "devices_with_connections": safe_get(stats, 'devices_with_connections', 0)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Topology summary exported to {filename}")
        return filename
    
    def export_topology_hierarchy(self, topology: Dict, filename: str = "mist_topology_hierarchy.json"):
        """Export detailed topology hierarchy to JSON file"""
        hierarchy = {
            "organization": {
                "organization_id": safe_get(topology, 'organization_id', 'Unknown'),
                "discovery_info": {
                    "timestamp": safe_get(topology, 'timestamp', 'Unknown'),
                    "discovery_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(safe_get(topology, 'timestamp', time.time()))),
                    "api_calls_used": safe_get(topology, 'api_calls_used', 0)
                },
                "sites": []
            }
        }
        
        # Process each site
        sites_data = safe_get(topology, 'sites', {})
        topology_links = safe_get(topology, 'topology_links', [])
        device_connections = safe_get(topology, 'device_connections', {})
        
        for site_id, site_info in sites_data.items():
            site_hierarchy = {
                "site_id": site_id,
                "site_name": safe_get(site_info, 'site_name', 'Unknown'),
                "device_count": safe_get(site_info, 'device_count', 0),
                "device_types": {
                    "switches": [],
                    "access_points": [],
                    "gateways": [],
                    "other": []
                },
                "connections": {
                    "internal_links": [],
                    "external_links": [],
                    "unconnected_devices": []
                }
            }
            
            # Process devices in this site
            devices = safe_get(site_info, 'devices', [])
            for device in devices:
                device_mac = safe_get(device, 'mac')
                device_type = safe_get(device, 'type', 'unknown')
                
                device_info = {
                    "name": safe_get(device, 'name', 'Unknown'),
                    "mac": device_mac,
                    "model": safe_get(device, 'model', 'Unknown'),
                    "type": device_type,
                    "status": safe_get(device, 'status', 'unknown'),
                    "serial": safe_get(device, 'serial', 'Unknown'),
                    "connections": []
                }
                
                # Add device connections if available
                if device_mac in device_connections:
                    device_connections_list = device_connections[device_mac]
                    for conn in device_connections_list:
                        connection_info = {
                            "local_port": safe_access(conn, 'port', 'Unknown'),
                            "neighbor_mac": safe_get(conn, 'neighbor_mac', 'Unknown'),
                            "neighbor_port": safe_get(conn, 'neighbor_port', 'Unknown'),
                            "neighbor_system": safe_get(conn, 'neighbor_system', 'Unknown'),
                            "status": safe_get(conn, 'status', 'unknown'),
                            "protocol": safe_get(conn, 'protocol', 'Unknown')
                        }
                        device_info["connections"].append(connection_info)
                
                # Categorize device by type
                if device_type == 'switch':
                    site_hierarchy["device_types"]["switches"].append(device_info)
                elif device_type == 'ap':
                    site_hierarchy["device_types"]["access_points"].append(device_info)
                elif device_type == 'gateway':
                    site_hierarchy["device_types"]["gateways"].append(device_info)
                else:
                    site_hierarchy["device_types"]["other"].append(device_info)
                
                # Check if device has connections
                if not device_info["connections"]:
                    site_hierarchy["connections"]["unconnected_devices"].append({
                        "name": device_info["name"],
                        "mac": device_info["mac"],
                        "type": device_info["type"]
                    })
            
            hierarchy["organization"]["sites"].append(site_hierarchy)
        
        with open(filename, 'w') as f:
            json.dump(hierarchy, f, indent=2)
        print(f"Topology hierarchy exported to {filename}")
        return filename
    
    def get_device_search(self, device_type: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """Search for specific device types across organization"""
        url = f"{self.base_url}/orgs/{self.config.org_id}/devices/search"
        params: Dict[str, str] = {'limit': str(limit)}
        if device_type:
            params['type'] = device_type
            
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            self.api_call_count += 1
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching devices: {e}")
            return []


def load_config_from_env(env_file: str = '.env') -> MistConfig:
    """Load configuration from environment variables, optionally from .env file"""
    # Load .env file if it exists
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded configuration from {env_file}")
    
    # Try multiple environment variable naming conventions
    token = (os.getenv('API_TOKEN') or 
             os.getenv('MIST_API_TOKEN'))
    
    org_id = (os.getenv('ORG_ID') or 
              os.getenv('MIST_ORG_ID'))
    
    base_url = os.getenv('BASE_URL', '')
    host = (os.getenv('HOST') or 
            base_url.replace('https://', '') if base_url else '' or
            os.getenv('MIST_API_HOST', 'api.mist.com'))
    
    # Clean up host if it includes protocol
    if host.startswith('https://'):
        host = host.replace('https://', '')
    
    if not token or not org_id:
        raise ValueError("API_TOKEN/MIST_API_TOKEN and ORG_ID/MIST_ORG_ID environment variables must be set")
    
    return MistConfig(token=token, org_id=org_id, host=host)


def load_config_from_file(config_file: str = "mist_config.json") -> MistConfig:
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        return MistConfig(**config_data)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file {config_file} not found")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in configuration file {config_file}")


if __name__ == "__main__":
    # Example usage
    try:
        # Try to load from .env file first, then environment, then JSON file
        try:
            config = load_config_from_env()
        except ValueError:
            try:
                config = load_config_from_file()
                print("Using configuration from mist_config.json")
            except FileNotFoundError:
                print("No configuration found. Please create a .env file or mist_config.json")
                print("Required variables: API_TOKEN, ORG_ID, HOST (optional)")
                raise
        
        # Initialize client
        client = MistBulkTopologyClient(config)
        
        # Get complete topology with minimal API calls
        topology = client.get_complete_topology()
        
        # Display statistics
        stats = safe_get(topology, 'statistics', {})
        print(f"\n=== Topology Discovery Complete ===")
        print(f"Total API Calls Made: {safe_get(topology, 'api_calls_used', 0)}")
        print(f"Sites: {safe_get(stats, 'total_sites', 0)}")
        print(f"Devices: {safe_get(stats, 'total_devices', 0)}")
        print(f"Switches: {safe_get(stats, 'total_switches', 0)}")
        print(f"Access Points: {safe_get(stats, 'total_aps', 0)}")
        print(f"Gateways: {safe_get(stats, 'total_gateways', 0)}")
        print(f"Unique Network Links: {safe_get(stats, 'unique_links', 0)}")
        
        # Export to file
        client.export_topology_to_file(topology)
        
        # Export summary to JSON
        client.export_topology_summary(topology)
        
        # Export hierarchy to JSON  
        client.export_topology_hierarchy(topology)
        
    except Exception as e:
        print(f"Error: {e}")