#!/usr/bin/env python3
"""
Simple usage example for Mist Topology Client
Demonstrates the efficient bulk topology retrieval approach
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mist_topology_client import MistBulkTopologyClient, MistConfig, load_config_from_env


def main():
    # Load configuration from .env file
    try:
        # This will automatically load from .env if it exists
        config = load_config_from_env()
        print(f"Using Mist API at: {config.host}")
        print(f"Organization ID: {config.org_id}")
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please ensure your .env file has API_TOKEN, ORG_ID, and HOST variables")
        return
    
    # Initialize client
    client = MistBulkTopologyClient(config)
    
    print("Starting topology discovery...")
    
    # Get complete topology with just 2 API calls
    topology = client.get_complete_topology()
    
    # Display basic statistics
    stats = topology.get('statistics', {})
    print(f"\n=== Topology Discovery Results ===")
    print(f"API Calls Used: {topology.get('api_calls_used', 0)}")
    print(f"Total Sites: {stats.get('total_sites', 0)}")
    print(f"Total Devices: {stats.get('total_devices', 0)}")
    print(f"- Switches: {stats.get('total_switches', 0)}")
    print(f"- Access Points: {stats.get('total_aps', 0)}")
    print(f"- Gateways: {stats.get('total_gateways', 0)}")
    print(f"Network Links: {stats.get('unique_links', 0)}")
    
    # Show site breakdown
    print(f"\n=== Site Breakdown ===")
    for site_id, site_info in topology.get('sites', {}).items():
        print(f"Site: {site_info.get('site_name', 'Unknown')}")
        print(f"  Devices: {site_info.get('device_count', 0)}")
    
    # Export to file
    client.export_topology_to_file(topology, "simple_topology.json")
    print(f"\nTopology data exported to: simple_topology.json")
    
    # Example: Search for specific device types
    print(f"\n=== Device Search Example ===")
    switches = client.get_device_search(device_type="switch")
    print(f"Found {len(switches)} switches in organization")


if __name__ == "__main__":
    main()