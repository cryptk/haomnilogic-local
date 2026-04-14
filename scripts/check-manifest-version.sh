#!/usr/bin/env bash
MANIFEST_VERSION=$(jq -r .requirements[0] custom_components/omnilogic_local/manifest.json)
PYPROJ_VERSION=$(uv export --frozen --no-hashes | grep ^python-omnilogic-local==)

if [[ "${MANIFEST_VERSION}" == "${PYPROJ_VERSION}" ]]; then
  echo "manifest.json version matches project version"
  exit 0
else
  echo "manifest.json version appears to be out of date"
  echo "Manifest version: ${MANIFEST_VERSION}"
  echo "Project version: ${PYPROJ_VERSION}"
  exit 1
fi
