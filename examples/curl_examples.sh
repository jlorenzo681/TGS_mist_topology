#!/bin/bash
#
# Mist REST API Bulk Topology Retrieval Examples
# Demonstrates efficient curl commands for topology discovery
#

# Configuration - Load from .env file if available
if [ -f ../.env ]; then
    echo "Loading configuration from .env file..."
    export $(grep -v '^#' ../.env | xargs)
    MIST_TOKEN="$API_TOKEN"
    ORG_ID="$ORG_ID"
    API_HOST="$HOST"
else
    echo "No .env file found, using default values"
    MIST_TOKEN="your-api-token-here"
    ORG_ID="your-org-id-here"
    API_HOST="api.mist.com"  # or api.eu.mist.com, api.ac2.mist.com
fi

# Base URL
BASE_URL="https://${API_HOST}/api/v1"

# Headers
HEADERS=(-H "Content-Type: application/json" -H "Authorization: Token ${MIST_TOKEN}")

echo "=== Mist REST API Bulk Topology Retrieval ==="
echo "Organization: ${ORG_ID}"
echo "API Host: ${API_HOST}"

# Validate configuration
if [ "$MIST_TOKEN" = "your-api-token-here" ] || [ "$ORG_ID" = "your-org-id-here" ]; then
    echo "⚠️  Warning: Using placeholder values. Please update your .env file or set variables manually."
fi
echo ""

# 1. Get ALL devices across entire organization (single call)
echo "1. Getting organization-wide device inventory..."
curl "${HEADERS[@]}" \
     -X GET \
     "${BASE_URL}/orgs/${ORG_ID}/inventory" \
     -o inventory.json

if [ $? -eq 0 ]; then
    echo "✅ Inventory retrieved successfully -> inventory.json"
else
    echo "❌ Failed to retrieve inventory"
fi
echo ""

# 2. Get organization-wide device statistics (single call)  
echo "2. Getting organization-wide device statistics..."
curl "${HEADERS[@]}" \
     -X GET \
     "${BASE_URL}/orgs/${ORG_ID}/stats/devices" \
     -o device_stats.json

if [ $? -eq 0 ]; then
    echo "✅ Device statistics retrieved successfully -> device_stats.json"
else
    echo "❌ Failed to retrieve device statistics"
fi
echo ""

# 3. Search for specific device types across organization
echo "3. Searching for switches across organization..."
curl "${HEADERS[@]}" \
     -X GET \
     "${BASE_URL}/orgs/${ORG_ID}/devices/search?type=switch&limit=1000" \
     -o switches.json

if [ $? -eq 0 ]; then
    echo "✅ Switch search completed -> switches.json"
else
    echo "❌ Failed to search switches"
fi
echo ""

# 4. Get switch metrics and topology insights
echo "4. Getting switch metrics and topology insights..."
curl "${HEADERS[@]}" \
     -X GET \
     "${BASE_URL}/orgs/${ORG_ID}/insights/switch-metrics" \
     -o switch_insights.json

if [ $? -eq 0 ]; then
    echo "✅ Switch insights retrieved -> switch_insights.json"
else
    echo "❌ Failed to retrieve switch insights"
fi
echo ""

# 5. Export complete device configurations
echo "5. Exporting complete device configurations..."
curl "${HEADERS[@]}" \
     -X GET \
     "${BASE_URL}/orgs/${ORG_ID}/devices/export" \
     -o device_export.json

if [ $? -eq 0 ]; then
    echo "✅ Device export completed -> device_export.json"
else
    echo "❌ Failed to export device configurations"
fi
echo ""

echo "=== Bulk Retrieval Complete ==="
echo "Total API calls made: 5"
echo "Files generated:"
echo "  - inventory.json (complete device inventory)"
echo "  - device_stats.json (device statistics with connectivity)"
echo "  - switches.json (switch-specific search results)"
echo "  - switch_insights.json (topology insights)"
echo "  - device_export.json (complete device configurations)"
echo ""
echo "These files contain all necessary data to build complete topology maps"
echo "without additional API calls, maximizing efficiency and minimizing rate limit usage."