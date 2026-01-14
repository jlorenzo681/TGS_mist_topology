#!/usr/bin/env python3

import argparse
import json
import sys
import os
import time
from pathlib import Path
from .client import MistBulkTopologyClient, MistConfig, load_config_from_env, load_config_from_file


def safe_get(obj, key, default="N/A"):
    """
    Safely get a value from a dictionary-like object.
    Returns 'N/A' if obj is a string or doesn't have the get method.
    """
    if isinstance(obj, str) or not hasattr(obj, 'get'):
        return default
    return obj.get(key, default)


def safe_contains(obj, key):
    """
    Safely check if a key exists in a dictionary-like object.
    Returns False if obj is a string or doesn't support 'in' operator.
    """
    if isinstance(obj, str) or not isinstance(obj, dict):
        return False
    return key in obj


def safe_access(obj, key, default="N/A"):
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


def create_sample_config():
    """Create a sample .env configuration file"""
    sample_env = '''# Mist Systems API Configuration
# Copy your values from the existing .env or Mist portal

# API Host Configuration (use your regional endpoint)
HOST=api.eu.mist.com
# HOST=api.mist.com          # For US region
# HOST=api.ac2.mist.com      # For APAC region

# Authentication (get from Mist portal > Account Settings > API Token)
API_TOKEN=your-api-token-here

# Organization Configuration (get from Mist portal URL)
ORG_ID=your-org-id-here

# Optional: Site and Device IDs for specific operations
# SITE_ID=your-site-id-here
# DEVICE_ID=your-device-id-here

# API Rate Limiting (calls per second)
API_RATE_LIMIT=5
'''
    
    config_file = ".env.template"
    with open(config_file, 'w') as f:
        f.write(sample_env)
    
    print(f"Sample configuration created: {config_file}")
    print("Copy this to .env and edit with your actual values:")
    print(f"cp {config_file} .env")
    print("")
    print("Required values:")
    print("- API_TOKEN: Get from Mist portal > Account Settings > API Token")
    print("- ORG_ID: Copy from your Mist portal URL")
    print("- HOST: Use your regional API endpoint (api.mist.com, api.eu.mist.com, etc.)")


def create_topology_hierarchy(topology: dict) -> dict:
    """Create a hierarchical representation of the network topology"""
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
        
        # Process topology links for this site
        for link in topology_links:
            source_mac = safe_access(link, 'source_mac', '')
            target_mac = safe_get(link, 'target_mac', '')
            
            # Check if this link involves devices from this site
            source_in_site = any(safe_get(dev, 'mac') == source_mac for dev in devices)
            target_in_site = any(safe_get(dev, 'mac') == target_mac for dev in devices)
            
            if source_in_site or target_in_site:
                link_info = {
                    "source_device": safe_get(link, 'source_name', 'Unknown'),
                    "source_mac": source_mac,
                    "source_port": safe_access(link, 'source_port', 'Unknown'),
                    "target_mac": target_mac,
                    "target_port": safe_get(link, 'target_port', 'Unknown'),
                    "status": safe_get(link, 'link_status', 'unknown'),
                    "speed_mbps": safe_get(link, 'speed_mbps', 'Unknown'),
                    "protocol": safe_get(link, 'protocol', 'Unknown')
                }
                
                # Determine if it's an internal or external link
                if source_in_site and target_in_site:
                    site_hierarchy["connections"]["internal_links"].append(link_info)
                else:
                    site_hierarchy["connections"]["external_links"].append(link_info)
        
        hierarchy["organization"]["sites"].append(site_hierarchy)
    
    return hierarchy


def save_topology_hierarchy(topology: dict, filename: str = "mist_topology_hierarchy.json"):
    """Save the topology hierarchy to a JSON file"""
    hierarchy = create_topology_hierarchy(topology)
    
    with open(filename, 'w') as f:
        json.dump(hierarchy, f, indent=2)
    
    print(f"Topology hierarchy saved to: {filename}")
    return filename


def create_topology_summary(topology: dict) -> dict:
    """Create a structured summary of the topology data"""
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
    
    return summary


def save_topology_summary(topology: dict, filename: str = "mist_topology_summary.json"):
    """Save the topology summary to a JSON file"""
    summary = create_topology_summary(topology)
    
    with open(filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Topology summary saved to: {filename}")
    return filename


def display_topology_summary(topology: dict, save_to_file: bool = True, filename: str = "mist_topology_summary.json", 
                           save_hierarchy: bool = True, hierarchy_filename: str = "mist_topology_hierarchy.json"):
    """Display a summary of the retrieved topology and optionally save to JSON"""
    stats = safe_get(topology, 'statistics', {})
    
    print(f"\n{'='*50}")
    print(f"MIST TOPOLOGY SUMMARY")
    print(f"{'='*50}")
    print(f"Organization ID: {safe_get(topology, 'organization_id', 'Unknown')}")
    print(f"API Calls Used: {safe_get(topology, 'api_calls_used', 0)}")
    print(f"Timestamp: {safe_get(topology, 'timestamp', 'Unknown')}")
    print(f"\nINFRASTRUCTURE:")
    print(f"  Sites: {safe_get(stats, 'total_sites', 0)}")
    print(f"  Total Devices: {safe_get(stats, 'total_devices', 0)}")
    print(f"  - Switches: {safe_get(stats, 'total_switches', 0)}")
    print(f"  - Access Points: {safe_get(stats, 'total_aps', 0)}")
    print(f"  - Gateways: {safe_get(stats, 'total_gateways', 0)}")
    print(f"\nCONNECTIVITY:")
    print(f"  Total Connections: {safe_get(stats, 'total_connections', 0)}")
    print(f"  Unique Links: {safe_get(stats, 'unique_links', 0)}")
    print(f"  Devices with Connections: {safe_get(stats, 'devices_with_connections', 0)}")
    
    # Save to JSON files
    if save_to_file:
        save_topology_summary(topology, filename)
    
    if save_hierarchy:
        save_topology_hierarchy(topology, hierarchy_filename)


def display_site_details(topology: dict):
    """Display detailed site information"""
    print(f"\n{'='*50}")
    print(f"SITE DETAILS")
    print(f"{'='*50}")
    
    for site_id, site_info in safe_get(topology, 'sites', {}).items():
        print(f"\nSite: {safe_get(site_info, 'site_name', 'Unknown')} ({site_id})")
        print(f"  Device Count: {safe_get(site_info, 'device_count', 0)}")
        
        for device in safe_get(site_info, 'devices', []):
            status = safe_get(device, 'status', 'unknown')
            print(f"    - {safe_get(device, 'name', 'Unknown')} ({safe_get(device, 'type', 'unknown')}) - {status}")


def export_topology(topology: dict, output_format: str, filename: str):
    """Export topology in various formats"""
    if output_format.lower() == 'json':
        with open(filename, 'w') as f:
            json.dump(topology, f, indent=2)
        print(f"Topology exported to {filename} (JSON format)")
    
    elif output_format.lower() == 'csv':
        import csv
        
        # Export devices to CSV
        devices_file = filename.replace('.csv', '_devices.csv')
        with open(devices_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Site', 'Device Name', 'MAC', 'Type', 'Model', 'Status'])
            
            for site_info in safe_get(topology, 'sites', {}).values():
                for device in safe_get(site_info, 'devices', []):
                    writer.writerow([
                        safe_get(site_info, 'site_name', ''),
                        safe_get(device, 'name', ''),
                        safe_get(device, 'mac', ''),
                        safe_get(device, 'type', ''),
                        safe_get(device, 'model', ''),
                        safe_get(device, 'status', '')
                    ])
        
        # Export links to CSV
        links_file = filename.replace('.csv', '_links.csv')
        with open(links_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Source Device', 'Source Port', 'Target MAC', 'Target Port', 'Status', 'Speed'])
            
            for link in safe_get(topology, 'topology_links', []):
                writer.writerow([
                    safe_get(link, 'source_name', ''),
                    safe_get(link, 'source_port', ''),
                    safe_get(link, 'target_mac', ''),
                    safe_get(link, 'target_port', ''),
                    safe_get(link, 'link_status', ''),
                    safe_get(link, 'speed_mbps', '')
                ])
        
        print(f"Topology exported to {devices_file} and {links_file} (CSV format)")


def search_devices(client: MistBulkTopologyClient, device_type: str = None):
    """Search for specific devices"""
    print(f"Searching for devices{f' of type {device_type}' if device_type else ''}...")
    
    devices = client.get_device_search(device_type=device_type)
    
    print(f"\nFound {len(devices)} devices:")
    for device in devices:
        print(f"  - {safe_get(device, 'name', 'Unknown')} ({safe_get(device, 'type', 'unknown')}) - {safe_get(device, 'mac', 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(
        description="Mist Network Topology Discovery Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --get-topology --summary
  %(prog)s --get-topology --export json --output topology.json
  %(prog)s --get-topology --site-details
  %(prog)s --get-topology --summary --summary-file my_summary.json
  %(prog)s --get-topology --summary --hierarchy-file my_hierarchy.json
  %(prog)s --get-topology --summary --no-save-summary --no-save-hierarchy
  %(prog)s --search-devices --type switch
  %(prog)s --create-config
  %(prog)s --config-file custom.json --get-topology
        """
    )
    
    # Configuration options
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument('--config-file', default='mist_config.json',
                             help='JSON configuration file path (default: mist_config.json)')
    config_group.add_argument('--env-file', default='.env',
                             help='.env file path (default: .env)')
    config_group.add_argument('--create-config', action='store_true',
                             help='Create sample configuration file (.env format)')
    
    # Main operations
    operation_group = parser.add_argument_group('Operations')
    operation_group.add_argument('--get-topology', action='store_true',
                                help='Retrieve complete network topology')
    operation_group.add_argument('--search-devices', action='store_true',
                                help='Search for devices')
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--summary', action='store_true',
                             help='Display topology summary')
    output_group.add_argument('--site-details', action='store_true',
                             help='Display detailed site information')
    output_group.add_argument('--export', choices=['json', 'csv'],
                             help='Export format (json, csv)')
    output_group.add_argument('--output', default='topology',
                             help='Output filename (default: topology)')
    output_group.add_argument('--save-summary', action='store_true', default=True,
                             help='Save topology summary to JSON file (default: enabled)')
    output_group.add_argument('--no-save-summary', action='store_false', dest='save_summary',
                             help='Disable saving topology summary to JSON file')
    output_group.add_argument('--summary-file', default='mist_topology_summary.json',
                             help='JSON summary filename (default: mist_topology_summary.json)')
    output_group.add_argument('--save-hierarchy', action='store_true', default=True,
                             help='Save topology hierarchy to JSON file (default: enabled)')
    output_group.add_argument('--no-save-hierarchy', action='store_false', dest='save_hierarchy',
                             help='Disable saving topology hierarchy to JSON file')
    output_group.add_argument('--hierarchy-file', default='mist_topology_hierarchy.json',
                             help='JSON hierarchy filename (default: mist_topology_hierarchy.json)')
    
    # Search options
    search_group = parser.add_argument_group('Search Options')
    search_group.add_argument('--type', choices=['switch', 'ap', 'gateway'],
                             help='Device type to search for')
    
    args = parser.parse_args()
    
    # Create sample config if requested
    if args.create_config:
        create_sample_config()
        return
    
    # Validate that at least one operation is specified
    if not any([args.get_topology, args.search_devices]):
        parser.error("At least one operation must be specified (--get-topology or --search-devices)")
    
    try:
        # Load configuration with priority: .env -> JSON config -> environment variables
        config = None
        
        # Try .env file first
        if os.path.exists('.env'):
            try:
                config = load_config_from_env('.env')
            except ValueError:
                pass
        
        # Try JSON config file if specified and .env didn't work
        if not config and os.path.exists(args.config_file):
            try:
                config = load_config_from_file(args.config_file)
                print(f"Using configuration from {args.config_file}")
            except (FileNotFoundError, ValueError):
                pass
        
        # Try environment variables as fallback
        if not config:
            try:
                config = load_config_from_env(env_file='nonexistent')
                print("Using configuration from environment variables")
            except ValueError:
                pass
        
        # If nothing worked, show error
        if not config:
            print("Error: No valid configuration found")
            print("Please ensure you have one of the following:")
            print("1. A .env file with API_TOKEN, ORG_ID, and HOST variables")
            print("2. A JSON config file (create with --create-config)")
            print("3. Environment variables: MIST_API_TOKEN, MIST_ORG_ID, MIST_API_HOST")
            sys.exit(1)
        
        # Initialize client
        client = MistBulkTopologyClient(config)
        
        # Execute operations
        if args.get_topology:
            topology = client.get_complete_topology()
            
            # Display options
            if args.summary or (not args.site_details and not args.export):
                display_topology_summary(topology, save_to_file=args.save_summary, filename=args.summary_file,
                                        save_hierarchy=args.save_hierarchy, hierarchy_filename=args.hierarchy_file)
            
            if args.site_details:
                display_site_details(topology)
            
            # Export options
            if args.export:
                if args.export == 'json':
                    filename = f"{args.output}.json"
                elif args.export == 'csv':
                    filename = f"{args.output}.csv"
                
                export_topology(topology, args.export, filename)
        
        if args.search_devices:
            search_devices(client, args.type)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()