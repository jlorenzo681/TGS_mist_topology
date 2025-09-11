#!/usr/bin/env python3
"""
Advanced usage example for Mist Topology Client
Demonstrates topology analysis and connection mapping
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mist_topology_client import MistBulkTopologyClient, MistConfig, load_config_from_env
import json


def analyze_topology_connectivity(topology: dict):
    """Analyze topology connectivity patterns"""
    print("\n=== CONNECTIVITY ANALYSIS ===")
    
    # Analyze device connections
    device_connections = topology.get('device_connections', {})
    connection_counts = {}
    
    for device_mac, connections in device_connections.items():
        connection_counts[device_mac] = len(connections)
    
    # Find most connected devices
    if connection_counts:
        max_connections = max(connection_counts.values())
        most_connected = [mac for mac, count in connection_counts.items() if count == max_connections]
        
        print(f"Most connected device(s): {len(most_connected)} device(s) with {max_connections} connections")
        
        # Find device details for most connected
        for site_info in topology.get('sites', {}).values():
            for device in site_info.get('devices', []):
                if device.get('mac') in most_connected:
                    print(f"  - {device.get('name', 'Unknown')} ({device.get('type', 'unknown')})")


def analyze_site_distribution(topology: dict):
    """Analyze device distribution across sites"""
    print("\n=== SITE DISTRIBUTION ANALYSIS ===")
    
    site_stats = []
    for site_id, site_info in topology.get('sites', {}).items():
        device_types = {}
        for device in site_info.get('devices', []):
            device_type = device.get('type', 'unknown')
            device_types[device_type] = device_types.get(device_type, 0) + 1
        
        site_stats.append({
            'name': site_info.get('site_name', 'Unknown'),
            'total': site_info.get('device_count', 0),
            'types': device_types
        })
    
    # Sort sites by device count
    site_stats.sort(key=lambda x: x['total'], reverse=True)
    
    print(f"{'Site Name':<30} {'Total':<8} {'Switches':<10} {'APs':<8} {'Gateways':<10}")
    print("-" * 76)
    
    for site in site_stats:
        switches = site['types'].get('switch', 0)
        aps = site['types'].get('ap', 0)
        gateways = site['types'].get('gateway', 0)
        print(f"{site['name']:<30} {site['total']:<8} {switches:<10} {aps:<8} {gateways:<10}")


def find_network_issues(topology: dict):
    """Identify potential network issues"""
    print("\n=== POTENTIAL ISSUES ANALYSIS ===")
    
    issues = []
    
    # Check for devices without connections
    devices_without_connections = 0
    for site_info in topology.get('sites', {}).values():
        for device in site_info.get('devices', []):
            if device.get('type') == 'switch' and not device.get('connections'):
                devices_without_connections += 1
    
    if devices_without_connections > 0:
        issues.append(f"Found {devices_without_connections} switches without detected connections")
    
    # Check for offline devices
    offline_devices = 0
    for site_info in topology.get('sites', {}).values():
        for device in site_info.get('devices', []):
            if device.get('status') in ['offline', 'disconnected']:
                offline_devices += 1
    
    if offline_devices > 0:
        issues.append(f"Found {offline_devices} offline/disconnected devices")
    
    # Check for sites without switches
    sites_without_switches = 0
    for site_info in topology.get('sites', {}).values():
        has_switch = any(device.get('type') == 'switch' for device in site_info.get('devices', []))
        if not has_switch and site_info.get('device_count', 0) > 0:
            sites_without_switches += 1
    
    if sites_without_switches > 0:
        issues.append(f"Found {sites_without_switches} sites without switches")
    
    if issues:
        for issue in issues:
            print(f"⚠️  {issue}")
    else:
        print("✅ No obvious issues detected")


def generate_network_report(topology: dict, filename: str = "network_report.json"):
    """Generate comprehensive network report"""
    stats = topology.get('statistics', {})
    
    report = {
        'summary': {
            'organization_id': topology.get('organization_id'),
            'discovery_timestamp': topology.get('timestamp'),
            'api_calls_used': topology.get('api_calls_used', 0),
            'total_sites': stats.get('total_sites', 0),
            'total_devices': stats.get('total_devices', 0),
            'device_breakdown': {
                'switches': stats.get('total_switches', 0),
                'access_points': stats.get('total_aps', 0),
                'gateways': stats.get('total_gateways', 0)
            },
            'connectivity': {
                'total_connections': stats.get('total_connections', 0),
                'unique_links': stats.get('unique_links', 0),
                'connected_devices': stats.get('devices_with_connections', 0)
            }
        },
        'site_details': [],
        'device_inventory': []
    }
    
    # Add site details
    for site_id, site_info in topology.get('sites', {}).items():
        site_detail = {
            'site_id': site_id,
            'site_name': site_info.get('site_name'),
            'device_count': site_info.get('device_count', 0),
            'devices': site_info.get('devices', [])
        }
        report['site_details'].append(site_detail)
        report['device_inventory'].extend(site_info.get('devices', []))
    
    # Export report
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Comprehensive network report generated: {filename}")


def main():
    # Load configuration from .env file
    try:
        config = load_config_from_env()
        print(f"Connected to Mist API: {config.host}")
        print(f"Organization: {config.org_id}")
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please ensure your .env file has API_TOKEN, ORG_ID, and HOST variables")
        return
    
    # Initialize client
    client = MistBulkTopologyClient(config)
    
    print("Starting advanced topology analysis...")
    
    # Get complete topology
    topology = client.get_complete_topology()
    
    # Display basic stats
    stats = topology.get('statistics', {})
    print(f"=== DISCOVERY SUMMARY ===")
    print(f"API Calls: {topology.get('api_calls_used', 0)}")
    print(f"Sites: {stats.get('total_sites', 0)}")
    print(f"Devices: {stats.get('total_devices', 0)}")
    print(f"Links: {stats.get('unique_links', 0)}")
    
    # Perform advanced analysis
    analyze_topology_connectivity(topology)
    analyze_site_distribution(topology)
    find_network_issues(topology)
    
    # Generate comprehensive report
    generate_network_report(topology)
    
    print(f"\n✅ Advanced analysis complete!")


if __name__ == "__main__":
    main()