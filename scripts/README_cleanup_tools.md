# Cleanup Validation and Backup System

This directory contains scripts for validating system integrity and managing backups during the codebase cleanup process.

## Scripts Overview

### 1. validate_cleanup.sh
**Purpose:** Validates system integrity before and after cleanup operations
**Requirements:** 6.1, 6.2

**Features:**
- Build system validation
- Launch file syntax checking
- Simulation capability verification
- Hardware launch capability verification
- Package dependency validation

**Usage:**
```bash
# Run full validation (recommended before cleanup)
./scripts/validate_cleanup.sh

# Run specific validation checks
./scripts/validate_cleanup.sh --build      # Test build system only
./scripts/validate_cleanup.sh --launch     # Check launch files only
./scripts/validate_cleanup.sh --simulation # Check simulation setup
./scripts/validate_cleanup.sh --hardware   # Check hardware setup
```

### 2. backup_system.sh
**Purpose:** Creates backups and enables rollback for cleanup phases
**Requirements:** 6.1, 7.1

**Features:**
- Backup creation for files/directories before modification
- Backup manifest tracking
- Automatic .gitignore management
- Validation checkpoint creation

**Usage:**
```bash
# Initialize backup system
./scripts/backup_system.sh init

# List available backups
./scripts/backup_system.sh list
```

### 3. rollback_phase.sh
**Purpose:** Provides phase-specific rollback capabilities
**Requirements:** 6.1, 7.1

**Features:**
- Individual phase rollback (Phase 1-6)
- Complete rollback of all phases
- Rollback availability checking
- Post-rollback validation

**Usage:**
```bash
# Show available rollbacks
./scripts/rollback_phase.sh list

# Rollback specific phase
./scripts/rollback_phase.sh phase1

# Rollback all phases (in reverse order)
./scripts/rollback_phase.sh all
```

## Cleanup Workflow

1. **Pre-cleanup Validation:**
   ```bash
   ./scripts/validate_cleanup.sh --full
   ```

2. **Initialize Backup System:**
   ```bash
   ./scripts/backup_system.sh init
   ```

3. **Before Each Phase:**
   - Create backup of files to be modified
   - Run validation checkpoint

4. **After Each Phase:**
   - Run validation to ensure system integrity
   - Create validation checkpoint

5. **If Issues Occur:**
   ```bash
   # Check available rollbacks
   ./scripts/rollback_phase.sh list
   
   # Rollback specific phase
   ./scripts/rollback_phase.sh phase1
   ```

## Requirements Mapping

- **Requirement 6.1:** System validation before and after cleanup
- **Requirement 6.2:** Launch file and simulation capability testing
- **Requirement 7.1:** Backup and rollback system for safe cleanup operations

## Dependencies

- **bash:** Shell scripting environment
- **jq:** JSON processing (for backup system)
- **ROS2:** For build system validation
- **Python3:** For launch file syntax validation
- **xmllint:** For package.xml validation

## Output Files

- `validation_report.log`: Detailed validation results
- `.cleanup_backups/`: Backup directory (auto-added to .gitignore)
- `.cleanup_backups/backup_manifest.json`: Backup tracking manifest
- `.cleanup_backups/checkpoint_*.json`: Validation checkpoint markers

## Safety Features

- All scripts use `set -e` for immediate error exit
- Backup system automatically manages .gitignore
- Rollback system validates backup existence before attempting rollback
- Validation checkpoints ensure system integrity at each phase
- Color-coded output for easy status identification

## Error Handling

- Scripts provide clear error messages with suggested actions
- Validation failures are logged with detailed information
- Rollback system checks backup availability before proceeding
- All operations can be safely interrupted and resumed