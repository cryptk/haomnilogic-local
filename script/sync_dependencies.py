#!/usr/bin/env python3
"""
Synchronizes dependencies between pyproject.toml and manifest.json.
Treats pyproject.toml as the source of truth.
"""

import argparse
import json
import logging
import sys
import tomllib
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def transform_dependency(dep: str) -> str:
    """Transform a pyproject.toml dependency string to a manifest.json requirement string.

    Transforms hyphens to underscores and >= to == for standard HA integration requirements.
    """
    # Normalize name: replace hyphen with underscore for the specific omnilogic library
    # Note: Home Assistant requirements standard usually prefers underscores for this library name.
    transformed = dep.replace("-", "_")

    # Pin version: replace >= with == if present to ensure development version is used
    return transformed.replace(">=", "==")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync dependencies from pyproject.toml to manifest.json")
    parser.add_argument("--check", action="store_true", help="Check for consistency without updating")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    pyproject_path = root / "pyproject.toml"
    manifest_path = root / "custom_components" / "omnilogic_local" / "manifest.json"

    if not pyproject_path.exists():
        logger.error("Error: %s not found", pyproject_path)
        sys.exit(1)
    if not manifest_path.exists():
        logger.error("Error: %s not found", manifest_path)
        sys.exit(1)

    # 1. Read dependencies from pyproject.toml
    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    # Extract project dependencies
    deps = pyproject.get("project", {}).get("dependencies", [])

    # We only care about runtime dependencies, which in this project
    # currently only include python-omnilogic-local.
    # To keep it robust, we transform all runtime dependencies.
    expected_requirements = [transform_dependency(d) for d in deps]

    # 2. Read manifest.json
    with manifest_path.open("r") as f:
        manifest = json.load(f)

    current_requirements = manifest.get("requirements", [])

    # 3. Compare and potentially update
    if set(current_requirements) == set(expected_requirements):
        logger.info("SUCCESS: Dependencies are consistent.")
        sys.exit(0)

    if args.check:
        logger.error("ERROR: Dependency mismatch detected!")
        logger.error("  pyproject.toml (transformed): %s", expected_requirements)
        logger.error("  manifest.json (current):     %s", current_requirements)
        logger.error("\nRun 'python3 script/sync_dependencies.py' to fix.")
        sys.exit(1)

    # Update manifest
    manifest["requirements"] = expected_requirements
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")  # Add trailing newline

    logger.info("SUCCESS: manifest.json updated to match pyproject.toml")


if __name__ == "__main__":
    main()
