# align-settings

Verify and align configuration files for the Scratch-Desk CNC system.

## When to use

Use `/align-settings` when you need to:
- Verify that all settings in settings.json are documented in config_descriptions.json
- Find hardcoded values in the codebase that should be configurable
- Automatically add missing setting descriptions
- Ensure the System Configuration tab in the admin tool shows all settings

## What this skill does

1. **Alignment Check**: Compares `config/settings.json` with `config/config_descriptions.json`:
   - Finds settings that exist but are not documented
   - Finds documented settings that don't exist in settings.json

2. **Hardcoded Value Scan**: Searches the codebase for:
   - `time.sleep()` calls with literal values
   - Hardcoded GPIO pin numbers
   - Hardcoded serial port paths
   - Hardcoded desk dimensions and offsets

3. **Auto-Fix Mode**: When run with `--fix`:
   - Adds [TODO] placeholders for undocumented settings
   - Generates proper description templates with type inference

## Instructions

Run the config alignment verification script:

```bash
python3 scripts/verify_config_alignment.py
```

If issues are found and you want to automatically add missing descriptions:

```bash
python3 scripts/verify_config_alignment.py --fix
```

For verbose output showing file contexts:

```bash
python3 scripts/verify_config_alignment.py --verbose
```

After running with `--fix`, review the `config/config_descriptions.json` file and update any `[TODO]` placeholders with proper descriptions.

## Files involved

- `scripts/verify_config_alignment.py` - The verification script
- `config/settings.json` - Master configuration file
- `config/config_descriptions.json` - Setting descriptions for admin UI
- `admin/tabs/config_tab.py` - System Configuration tab that displays all settings
