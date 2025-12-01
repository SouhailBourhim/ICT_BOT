# File Reorganization Script Usage Guide

## Overview

The `reorganize_files.py` script provides comprehensive file reorganization capabilities with safety features including dry-run, validation, backup, and rollback functionality.

## Features

- **Dry-run capability**: Preview changes without executing them
- **Comprehensive validation**: Check for missing files and conflicts before execution
- **Automatic backup**: Create backup before reorganization
- **File integrity verification**: SHA256 hash verification for moved files
- **Rollback functionality**: Undo reorganization if needed
- **Detailed logging**: Track all operations for audit and debugging

## Usage

### Basic Commands

```bash
# Preview reorganization (recommended first step)
python scripts/reorganize_files.py --preview-only

# Dry-run (shows preview but doesn't execute)
python scripts/reorganize_files.py --dry-run

# Execute reorganization (with confirmation prompt)
python scripts/reorganize_files.py

# Execute reorganization with verbose output
python scripts/reorganize_files.py --verbose

# Rollback using rollback data file
python scripts/reorganize_files.py --rollback rollback_data_20241201_143022.json
```

### Command Line Options

- `--root DIR`: Specify root directory (default: current directory)
- `--dry-run`: Preview changes without executing
- `--verbose, -v`: Enable verbose output
- `--rollback FILE`: Rollback using specified rollback data file
- `--preview-only`: Only show preview, don't execute

### Workflow

1. **Preview**: Always start with `--preview-only` to see what will be moved
2. **Validate**: Check for any missing files or conflicts in the preview
3. **Backup**: The script automatically creates a backup before execution
4. **Execute**: Run the reorganization after confirming the preview
5. **Verify**: Test functionality after reorganization
6. **Rollback**: Use rollback if issues are discovered

### File Mappings

The script reorganizes files according to these mappings:

#### Source Code → `src/`
- `app.py` → `src/app.py`
- `core/` → `src/core/`
- `managers/` → `src/managers/`
- `processors/` → `src/processors/`
- `retrievers/` → `src/retrievers/`
- `models/` → `src/models/`
- `ui/` → `src/ui/`
- `utils/` → `src/utils/`

#### Documentation → `docs/`
- `README_ENHANCED.md` → `docs/README.md`
- `DOCKER_DEPLOYMENT.md` → `docs/deployment/docker-deployment.md`
- `STREAMLIT_COMPATIBILITY.md` → `docs/technical/streamlit-compatibility.md`
- Other documentation files → appropriate `docs/` subdirectories

#### Scripts → `scripts/`
- Docker scripts → `scripts/docker/`
- Utility scripts → `scripts/utilities/`

#### Demo Files → `demos/`
- `demo_*.py` files → `demos/` with simplified names

#### Reports → `reports/`
- Status and integration files → `reports/`

#### Migration → `migration/`
- Migration scripts → `migration/scripts/`

### Safety Features

#### Automatic Backup
- Creates timestamped backup in `backup/pre_reorganization_YYYYMMDD_HHMMSS/`
- Includes integrity verification with SHA256 hashes
- Can be used for manual rollback if needed

#### Validation
- Checks for missing source files
- Detects destination conflicts
- Validates directory creation permissions
- Reports issues before execution

#### Rollback
- Saves rollback data during reorganization
- Allows complete undo of reorganization
- Verifies file integrity during rollback

### Output Files

After reorganization, the script creates:
- `reorganization_log_YYYYMMDD_HHMMSS.json`: Detailed operation log
- `rollback_data_YYYYMMDD_HHMMSS.json`: Data needed for rollback
- Backup directory with complete project backup

### Error Handling

The script handles various error conditions:
- Missing source files (validation failure)
- Permission issues (directory creation)
- File integrity problems (hash mismatch)
- Partial failures (continues with remaining files)

### Testing

Run the test suite to validate functionality:

```bash
python scripts/test_reorganization.py
```

This tests all major functionality including:
- File mapping logic
- Validation functionality
- Preview capabilities
- Dry-run behavior
- Backup creation

### Post-Reorganization Steps

After successful reorganization:

1. **Update imports**: Use import analyzer to identify needed changes
2. **Test functionality**: Run test suite and verify application startup
3. **Update documentation**: Reflect new structure in README and guides
4. **Update CI/CD**: Modify build scripts and deployment configs if needed

### Troubleshooting

#### Common Issues

1. **Permission Denied**: Ensure write permissions on target directories
2. **Missing Files**: Review file mappings and ensure all source files exist
3. **Import Errors**: Update Python import statements after reorganization
4. **Path Issues**: Update hardcoded paths in configuration files

#### Recovery

If issues occur:
1. Use rollback functionality: `python scripts/reorganize_files.py --rollback <rollback_file>`
2. Restore from backup manually if rollback fails
3. Check operation logs for detailed error information

### Best Practices

1. Always run preview first
2. Ensure clean git state before reorganization
3. Test in development environment first
4. Keep backups until reorganization is fully validated
5. Update import statements promptly after reorganization
6. Document any custom modifications to file mappings