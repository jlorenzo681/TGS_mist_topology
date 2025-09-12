# Mist Network Topology Discovery Tool

Efficient bulk topology retrieval for Juniper Mist networks using REST API endpoints optimized for non-EVPN environments. This implementation follows the best practices outlined in the documentation to minimize API calls and maximize rate limit efficiency.

## Features

- **Bulk Topology Retrieval**: Get complete organization topology in just 2-3 API calls
- **Rate Limit Optimization**: Uses organization-level endpoints instead of site-by-site queries  
- **Multiple Export Formats**: JSON and CSV output support
- **CLI Interface**: Command-line tool with comprehensive options
- **Connection Mapping**: Extracts LLDP and port connectivity information
- **Site Analysis**: Detailed site and device distribution analysis
- **Enhanced Site Information**: Retrieves site names, addresses, timezones, and country codes
- **Error Handling**: Robust retry logic with exponential backoff

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Authentication

**Option A: .env File (Recommended)**
```bash
# Create sample configuration
python mist_topology_cli.py --create-config

# Copy template and edit with your credentials
cp .env.template .env

# Edit .env file with your actual values:
# API_TOKEN=your-actual-api-token-here
# ORG_ID=your-actual-org-id-here
# HOST=api.eu.mist.com
```

**Option B: Environment Variables**
```bash
export API_TOKEN="your-api-token-here"
export ORG_ID="your-org-id-here"
export HOST="api.eu.mist.com"  # Use your regional endpoint
```

**Option C: JSON Configuration File**
```bash
# Create mist_config.json manually
{
  "token": "your-api-token-here",
  "org_id": "your-org-id-here", 
  "host": "api.eu.mist.com",
  "timeout": 30,
  "max_retries": 3
}
```

### 3. Basic Usage

```bash
# Get topology summary
python mist_topology_cli.py --get-topology --summary

# Get detailed site information
python mist_topology_cli.py --get-topology --site-details

# Export to JSON
python mist_topology_cli.py --get-topology --export json --output my_topology

# Export to CSV (creates device and link files)
python mist_topology_cli.py --get-topology --export csv --output network_data

# Search for specific devices
python mist_topology_cli.py --search-devices --type switch
```

## API Endpoints Used

This tool uses the most efficient Mist REST API endpoints:

- `GET /api/v1/orgs/{org_id}/inventory` - Complete device inventory (single call)
- `GET /api/v1/orgs/{org_id}/sites` - Organization sites with detailed information (names, addresses, timezones)
- `GET /api/v1/orgs/{org_id}/stats/devices` - Organization-wide device statistics  
- `GET /api/v1/orgs/{org_id}/devices/search` - Device search and filtering
- `GET /api/v1/sites/{site_id}/discovered_switches` - Unmanaged switch discovery (optional)

## Regional API Hosts

Replace `api.mist.com` with your regional endpoint:
- US: `api.mist.com`
- EU: `api.eu.mist.com` 
- APAC: `api.ac2.mist.com`

## Python Library Usage

### Simple Example

```python
from mist_topology_client import MistBulkTopologyClient, load_config_from_env

# Load configuration from .env file automatically
config = load_config_from_env()
client = MistBulkTopologyClient(config)

# Get complete topology with site details (5-7 API calls)
topology = client.get_complete_topology()

# Display statistics
stats = topology.get('statistics', {})
print(f"Sites: {stats.get('total_sites', 0)}")
print(f"Devices: {stats.get('total_devices', 0)}")
print(f"Links: {stats.get('unique_links', 0)}")

# Export to file
client.export_topology_to_file(topology)
```

### Advanced Analysis

See `examples/advanced_usage.py` for comprehensive topology analysis including:
- Connectivity pattern analysis
- Site distribution statistics  
- Network issue detection
- Comprehensive reporting

## CLI Commands

### Topology Retrieval
```bash
# Basic topology with summary
python mist_topology_cli.py --get-topology --summary

# Detailed site information
python mist_topology_cli.py --get-topology --site-details  

# Export formats
python mist_topology_cli.py --get-topology --export json --output topology
python mist_topology_cli.py --get-topology --export csv --output network
```

### Device Search
```bash
# Search all devices
python mist_topology_cli.py --search-devices

# Search by device type
python mist_topology_cli.py --search-devices --type switch
python mist_topology_cli.py --search-devices --type ap
python mist_topology_cli.py --search-devices --type gateway
```

### Configuration Management
```bash
# Create sample configuration file
python mist_topology_cli.py --create-config

# Use specific config file
python mist_topology_cli.py --config-file my_config.json --get-topology
```

## Output Formats

### JSON Export
Complete topology data structure with all device and connectivity information.

### CSV Export  
Creates two files:
- `{filename}_devices.csv` - Device inventory with site, name, MAC, type, model, status
- `{filename}_links.csv` - Network links with source/target information

### Site Information
The topology data now includes detailed site information for each location:
- **Site Name**: Human-readable site names (e.g., "Peñuelas_Distribution")
- **Physical Address**: Complete site addresses
- **Timezone**: Site-specific timezone information
- **Country Code**: Geographic location identifiers

This enhanced data allows for better geographical analysis and site-based reporting.

## Efficiency Comparison

**❌ Inefficient Approach (Avoid)**
- 1 API call to get sites
- 50 API calls for site devices (50 sites)  
- 1000 API calls for device details (1000 devices)
- **Total: 1051+ API calls**

**✅ Efficient Approach (This Tool)**
- 1 API call for organization inventory
- 1 API call for organization sites (with detailed site information)
- 1 API call for device statistics per site (typically 3-5 sites)
- **Total: 5-7 API calls** (vs 1000+ traditional approach)

This represents a **99.5% reduction** in API calls while retrieving comprehensive information including site details.

## Rate Limiting

- Organization tokens: 5,000 calls/hour per token
- With bulk endpoints: Complete topology in 5-7 calls (including detailed site information)
- Supports automatic retry with exponential backoff
- Rate limit headers are monitored and respected

## Error Handling

- Automatic retry on transient failures
- Exponential backoff for rate limiting
- Comprehensive error reporting
- Graceful handling of partial data

## Examples

The `examples/` directory contains:
- `simple_usage.py` - Basic topology retrieval
- `advanced_usage.py` - Comprehensive analysis and reporting
- `curl_examples.sh` - Raw curl commands for API testing

## Requirements

- Python 3.6+
- `requests` library
- `python-dotenv` library
- Valid Mist API token with organization access

## Authentication

### Creating API Tokens

1. Log into your Mist portal (e.g., `manage.eu.mist.com`)
2. Navigate to Account Settings → API Token
3. Click "Create Token" 
4. **Important**: Copy the token immediately - it won't be shown again
5. Add to your `.env` file as `API_TOKEN=your-token-here`

### Token Types

- **Organization tokens** (recommended): Independent rate limiting (5,000 calls/hour)
- **User tokens**: Shared rate limits across all tokens for the user

### Getting Your Organization ID

1. Log into your Mist portal
2. Look at the URL: `https://manage.eu.mist.com/admin/?org_id=44698e00-9362-410f-9e36-ab39b498fe91`
3. The `org_id` parameter is your Organization ID
4. Add to your `.env` file as `ORG_ID=your-org-id-here`

## Configuration Priority

The tool loads configuration in the following priority order:

1. **`.env` file** (highest priority) - Loads from project root
2. **JSON config file** - Specified with `--config-file` 
3. **Environment variables** - System environment variables
4. **Defaults** - Fallback values (will likely fail authentication)

### .env File Format

Your `.env` file should contain:

```bash
# Required
API_TOKEN=your-token-here
ORG_ID=44698e00-9362-410f-9e36-ab39b498fe91
HOST=api.eu.mist.com

# Optional
SITE_ID=10405890-0a23-4f77-9940-9984bd009feb
DEVICE_ID=00000000-0000-0000-1000-3063ead41980
API_RATE_LIMIT=5
```

## Regional Considerations

Different regions use different API endpoints. Check your Mist portal URL:
- `manage.mist.com` → use `api.mist.com`
- `manage.eu.mist.com` → use `api.eu.mist.com`  
- `manage.ac2.mist.com` → use `api.ac2.mist.com`

## LLDP Configuration

For complete topology discovery, ensure LLDP is enabled on switches:

```
set protocols lldp interface all
set protocols lldp management-address x.x.x.x
set protocols lldp port-id-subtype interface-name
```

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify API token is correct and not expired
- Check organization ID matches your portal URL
- Ensure token has proper permissions
- Confirm `.env` file is in the correct location
- Check that variable names in `.env` match: `API_TOKEN`, `ORG_ID`, `HOST`

**Rate Limiting**  
- Tool automatically handles rate limits with backoff
- Consider using organization tokens for better limits
- Bulk endpoints dramatically reduce call volume

**Missing Connection Data**
- Verify LLDP is enabled on network devices
- Check device firmware supports LLDP reporting
- Some connections may only appear in device statistics

**Regional API Issues**
- Verify correct regional API endpoint
- Check firewall/proxy settings for API access

## Support

This tool implements the official Mist REST API documented at:
- https://www.juniper.net/documentation/us/en/software/mist/api/
- https://api.mist.com/api/v1/docs (interactive documentation)

For API-specific questions, consult the official Mist documentation and GitHub resources.