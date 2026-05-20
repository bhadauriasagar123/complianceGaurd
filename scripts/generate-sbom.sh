#!/usr/bin/env bash
set -euo pipefail

mkdir -p sbom

echo "Generating Python SBOM..."
pip install cyclonedx-bom 2>/dev/null || pip install cyclonedx-bom
cd backend && cyclonedx-py requirements -o ../sbom/backend-sbom.json

echo "Generating Node.js SBOM..."
cd ../frontend && npx @cyclonedx/cyclonedx-npm --output-file ../sbom/frontend-sbom.json 2>/dev/null || npm audit --json > ../sbom/frontend-audit.json

echo "SBOM generation complete. Files in sbom/"
