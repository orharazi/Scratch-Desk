#!/usr/bin/env python3
"""
Configuration Alignment Verification Script
============================================

This script verifies that:
1. All settings in settings.json are documented in config_descriptions.json
2. All documented settings exist in settings.json
3. No hardcoded values exist in the codebase that should be configurable

Usage:
    python3 scripts/verify_config_alignment.py [--fix] [--verbose]

Options:
    --fix      Automatically fix alignment issues
    --verbose  Show detailed output
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.json"
DESCRIPTIONS_FILE = PROJECT_ROOT / "config" / "config_descriptions.json"

# Directories to scan for hardcoded values
SCAN_DIRS = ["core", "hardware", "gui", "admin"]

# Patterns to find hardcoded values
HARDCODED_PATTERNS = [
    # time.sleep with literal values
    (r'time\.sleep\s*\(\s*(\d+\.?\d*)\s*\)', 'time.sleep', 'timing'),
    # GPIO pin numbers
    (r'GPIO\.(setup|output|input)\s*\(\s*(\d+)', 'GPIO pin', 'hardware_config.raspberry_pi'),
    # Serial port paths
    (r'["\']\/dev\/tty\w+["\']', 'serial port', 'hardware_config'),
    # Baud rates
    (r'baud\s*[=:]\s*(\d{4,})', 'baud rate', 'hardware_config'),
    # Max position values
    (r'max_[xy]_position\s*[=:]\s*(\d+\.?\d*)', 'position limit', 'hardware_limits'),
    # Width/height of desk
    (r'(WIDTH|HEIGHT)_OF_DESK\s*=\s*(\d+)', 'desk dimension', 'hardware_limits'),
    # Paper offset
    (r'PAPER_OFFSET_[XY]\s*=\s*(\d+\.?\d*)', 'paper offset', 'hardware_limits'),
    # Timeout values
    (r'timeout\s*[=:]\s*(\d+\.?\d*)', 'timeout', 'timing'),
]

# Files to exclude from scanning
EXCLUDE_FILES = [
    'verify_config_alignment.py',
    '__pycache__',
    '.pyc',
    'test_',
]

# Known acceptable hardcoded values (not configuration)
ACCEPTABLE_HARDCODED = [
    '0',  # Zero initialization
    '1',  # Increment
    '0.0',
    '1.0',
    '100',  # Percentage
    '255',  # Max byte value
    '1000',  # Common multiplier
]


class ConfigAlignmentVerifier:
    """Verifies and aligns configuration files"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.settings = {}
        self.descriptions = {}
        self.issues = []
        self.hardcoded_values = []

    def load_files(self) -> bool:
        """Load settings and descriptions files"""
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
            print(f"[OK] Loaded settings.json")
        except Exception as e:
            print(f"[ERROR] Failed to load settings.json: {e}")
            return False

        try:
            with open(DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                self.descriptions = json.load(f)
            print(f"[OK] Loaded config_descriptions.json")
        except Exception as e:
            print(f"[ERROR] Failed to load config_descriptions.json: {e}")
            return False

        return True

    def flatten_settings(self, data: Dict, prefix: str = "") -> Set[str]:
        """Flatten nested settings dict to dot-notation paths"""
        paths = set()
        for key, value in data.items():
            full_path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                paths.update(self.flatten_settings(value, full_path))
            else:
                paths.add(full_path)
        return paths

    def flatten_descriptions(self, sections: Dict, prefix: str = "") -> Set[str]:
        """Flatten descriptions to dot-notation paths"""
        paths = set()

        for section_key, section_data in sections.items():
            section_path = f"{prefix}.{section_key}" if prefix else section_key

            # Direct settings in section
            settings = section_data.get("settings", {})
            for setting_key in settings:
                paths.add(f"{section_path}.{setting_key}")

            # Subsections
            subsections = section_data.get("subsections", {})
            for sub_key, sub_data in subsections.items():
                sub_path = f"{section_path}.{sub_key}"

                # Check if it's a direct setting (like use_real_hardware)
                if "description" in sub_data:
                    paths.add(sub_path)
                else:
                    # It's a nested subsection
                    sub_settings = sub_data.get("settings", {})
                    for setting_key in sub_settings:
                        paths.add(f"{sub_path}.{setting_key}")

        return paths

    def check_alignment(self) -> Tuple[Set[str], Set[str]]:
        """Check alignment between settings and descriptions"""
        settings_paths = self.flatten_settings(self.settings)
        desc_sections = self.descriptions.get("sections", {})
        desc_paths = self.flatten_descriptions(desc_sections)

        # Find mismatches
        in_settings_not_docs = settings_paths - desc_paths
        in_docs_not_settings = desc_paths - settings_paths

        return in_settings_not_docs, in_docs_not_settings

    def scan_for_hardcoded(self) -> List[Dict]:
        """Scan codebase for hardcoded values"""
        findings = []

        for scan_dir in SCAN_DIRS:
            dir_path = PROJECT_ROOT / scan_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                # Skip excluded files
                if any(excl in str(py_file) for excl in EXCLUDE_FILES):
                    continue

                try:
                    content = py_file.read_text(encoding='utf-8')
                    lines = content.split('\n')

                    for line_num, line in enumerate(lines, 1):
                        # Skip comments
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            continue

                        for pattern, desc, suggested_section in HARDCODED_PATTERNS:
                            matches = re.finditer(pattern, line, re.IGNORECASE)
                            for match in matches:
                                value = match.group(1) if match.lastindex else match.group(0)

                                # Skip acceptable values
                                if value in ACCEPTABLE_HARDCODED:
                                    continue

                                # Check if it's actually using settings
                                if 'settings[' in line or 'get_setting' in line or 'self.settings' in line:
                                    continue

                                findings.append({
                                    'file': str(py_file.relative_to(PROJECT_ROOT)),
                                    'line': line_num,
                                    'type': desc,
                                    'value': value,
                                    'suggested_section': suggested_section,
                                    'context': line.strip()[:80]
                                })
                except Exception as e:
                    if self.verbose:
                        print(f"[WARN] Could not read {py_file}: {e}")

        return findings

    def generate_description_template(self, path: str, value: Any) -> Dict:
        """Generate a description template for a setting"""
        key = path.split('.')[-1]

        # Infer type
        if isinstance(value, bool):
            val_type = "bool"
        elif isinstance(value, int):
            val_type = "int"
        elif isinstance(value, float):
            val_type = "float"
        elif isinstance(value, list):
            val_type = "list"
        else:
            val_type = "string"

        template = {
            "description": f"[TODO: Add description for {key}]",
            "type": val_type,
            "default": value,
            "category": "important"
        }

        # Add unit hints based on key name
        if 'delay' in key or 'timeout' in key or 'time' in key or 'interval' in key:
            template["unit"] = "seconds"
        elif 'position' in key or 'offset' in key or 'width' in key or 'height' in key:
            template["unit"] = "cm"
        elif 'speed' in key:
            template["unit"] = "cm/s"
        elif 'pin' in key or 'gpio' in key:
            template["category"] = "critical"
        elif 'port' in key:
            template["category"] = "critical"

        return template

    def fix_alignment(self, in_settings_not_docs: Set[str]) -> bool:
        """Add missing settings to descriptions file"""
        if not in_settings_not_docs:
            return True

        desc_sections = self.descriptions.get("sections", {})

        for path in sorted(in_settings_not_docs):
            parts = path.split('.')
            if len(parts) < 2:
                continue

            section_key = parts[0]
            setting_key = parts[-1]

            # Get the value from settings
            value = self.settings
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break

            if value is None or isinstance(value, dict):
                continue  # Skip nested dicts

            # Create section if needed
            if section_key not in desc_sections:
                desc_sections[section_key] = {
                    "title": section_key.replace('_', ' ').title(),
                    "title_he": f"[תרגום: {section_key}]",
                    "description": f"[TODO: Add description for {section_key} section]",
                    "settings": {}
                }

            section = desc_sections[section_key]

            # Handle subsections
            if len(parts) > 2:
                if "subsections" not in section:
                    section["subsections"] = {}

                subsection_key = parts[1]
                if subsection_key not in section["subsections"]:
                    section["subsections"][subsection_key] = {
                        "title": subsection_key.replace('_', ' ').title(),
                        "settings": {}
                    }

                subsection = section["subsections"][subsection_key]

                # Handle deeper nesting
                if len(parts) > 3:
                    deeper_key = parts[2]
                    if "settings" not in subsection:
                        subsection["settings"] = {}
                    # For now, add to subsection settings
                    if setting_key not in subsection.get("settings", {}):
                        if "settings" not in subsection:
                            subsection["settings"] = {}
                        subsection["settings"][setting_key] = self.generate_description_template(path, value)
                else:
                    if setting_key not in subsection.get("settings", {}):
                        if "settings" not in subsection:
                            subsection["settings"] = {}
                        subsection["settings"][setting_key] = self.generate_description_template(path, value)
            else:
                # Direct setting in section
                if "settings" not in section:
                    section["settings"] = {}
                if setting_key not in section["settings"]:
                    section["settings"][setting_key] = self.generate_description_template(path, value)

        self.descriptions["sections"] = desc_sections
        return True

    def save_descriptions(self) -> bool:
        """Save updated descriptions file"""
        try:
            # Update timestamp
            self.descriptions["generated"] = datetime.now().strftime("%Y-%m-%d")

            with open(DESCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.descriptions, f, indent=2, ensure_ascii=False)
            print(f"[OK] Saved config_descriptions.json")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save config_descriptions.json: {e}")
            return False

    def run(self, fix: bool = False) -> bool:
        """Run the verification"""
        print("\n" + "=" * 70)
        print("Configuration Alignment Verification")
        print("=" * 70 + "\n")

        # Load files
        if not self.load_files():
            return False

        print("\n" + "-" * 50)
        print("Step 1: Checking settings.json <-> config_descriptions.json alignment")
        print("-" * 50)

        in_settings_not_docs, in_docs_not_settings = self.check_alignment()

        # Report settings not in docs
        if in_settings_not_docs:
            print(f"\n[!] {len(in_settings_not_docs)} settings in settings.json but NOT documented:")
            for path in sorted(in_settings_not_docs):
                print(f"    - {path}")
        else:
            print("\n[OK] All settings are documented")

        # Report docs not in settings
        if in_docs_not_settings:
            print(f"\n[!] {len(in_docs_not_settings)} documented settings NOT in settings.json:")
            for path in sorted(in_docs_not_settings):
                print(f"    - {path}")
        else:
            print("\n[OK] All documented settings exist")

        print("\n" + "-" * 50)
        print("Step 2: Scanning for hardcoded values")
        print("-" * 50)

        self.hardcoded_values = self.scan_for_hardcoded()

        if self.hardcoded_values:
            print(f"\n[!] Found {len(self.hardcoded_values)} potential hardcoded values:\n")

            # Group by file
            by_file = {}
            for finding in self.hardcoded_values:
                file_path = finding['file']
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append(finding)

            for file_path, findings in sorted(by_file.items()):
                print(f"  {file_path}:")
                for f in findings:
                    print(f"    Line {f['line']}: {f['type']} = {f['value']}")
                    if self.verbose:
                        print(f"      Context: {f['context']}")
                        print(f"      Suggested: {f['suggested_section']}")
                print()
        else:
            print("\n[OK] No obvious hardcoded values found")

        # Summary
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)

        total_issues = len(in_settings_not_docs) + len(in_docs_not_settings) + len(self.hardcoded_values)

        print(f"\n  Settings not documented:     {len(in_settings_not_docs)}")
        print(f"  Documented but not in settings: {len(in_docs_not_settings)}")
        print(f"  Potential hardcoded values:  {len(self.hardcoded_values)}")
        print(f"  ----------------------------------------")
        print(f"  Total issues:                {total_issues}")

        if total_issues == 0:
            print("\n[SUCCESS] Configuration is fully aligned!")
            return True

        # Fix if requested
        if fix and in_settings_not_docs:
            print("\n" + "-" * 50)
            print("Fixing alignment issues...")
            print("-" * 50)

            if self.fix_alignment(in_settings_not_docs):
                if self.save_descriptions():
                    print(f"\n[OK] Added {len(in_settings_not_docs)} missing descriptions")
                    print("[NOTE] Please review and update the [TODO] placeholders in config_descriptions.json")

        if not fix and total_issues > 0:
            print("\n[TIP] Run with --fix to automatically add missing descriptions")

        return total_issues == 0


def main():
    parser = argparse.ArgumentParser(description="Verify configuration alignment")
    parser.add_argument('--fix', action='store_true', help='Automatically fix alignment issues')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    args = parser.parse_args()

    verifier = ConfigAlignmentVerifier(verbose=args.verbose)
    success = verifier.run(fix=args.fix)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
