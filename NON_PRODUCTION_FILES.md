# Non-Production Files Guide

This document lists files and patterns that are excluded from production builds via `.gitignore`.

## Categories of Non-Production Files

### 1. Development and Testing Scripts

**Root Level:**
- `install_vision_deps.sh` - Development setup script
- `start_cutting_edge_robot.py` - Development launcher
- `profile_*.py` - Performance profiling scripts
- `*_test.py` - Test scripts
- `comprehensive_*.py` - Comprehensive test suites
- `validate_*.py` - Validation scripts
- `verify_*.py` - Verification scripts

**Scripts Directory:**
- `scripts/backup_system.sh`
- `scripts/rollback_phase.sh`
- `scripts/validate_*.sh`
- `scripts/verify_*.sh`
- `scripts/test_*.py`
- `scripts/README_cleanup_tools.md`

### 2. Reports and Documentation (Development Only)

**Root Level:**
- `CODEBASE_CLEANUP_PLAN.md`
- `CLEANUP_SUMMARY.md`
- `*_CLEANUP_REPORT.md`
- `*_PLAN.md`
- `*_REPORT.md`
- `PRIORITY1_VALIDATION_REPORT.md`
- `*_INTEGRATION_REPORT.md`
- `TASK_*.md`
- `TASKS_*.md`
- `*_SUMMARY.md`
- `*_VALIDATION_REPORT.md`
- `*_QUICKSTART.md` (except main QUICKSTART.md)

**Docs Directory:**
- `docs/*_INTEGRATION_REPORT.md`
- `docs/*_REPORT.md`
- `docs/CODEBASE_STRUCTURE_ANALYSIS.md`
- `docs/FILE_STRUCTURE_DIAGRAM.md`

### 3. Test Results and Data

**JSON Files:**
- `validation_results.json`
- `test_report_template.json`
- `*_test_results.json`
- `swarm_test_results.json`
- `rl_navigation_test_results.json`
- `priority1_validation_report.json`

**Directories:**
- `test_data/`
- `test_results/`
- `test_output/`
- `validation_output/`
- `*_results/`
- `results/`

### 4. Trained Models and Checkpoints

**Files:**
- `*.pkl` - Pickle files (anomaly models, failure predictors)
- `*.h5` - Keras models
- `*.keras` - Keras models
- `*_model.pt` - PyTorch models
- `*_policy.zip` - RL policies
- `*.pt` - PyTorch checkpoints
- `*.onnx` - ONNX models
- `*.weights` - Weight files
- `*.pth` - PyTorch state dicts

**Directories:**
- `models/`
- `checkpoints/`
- `trained_models/`

**Specific Files:**
- `health_metrics.json`
- `maintenance_log.json`
- `anomaly_model.pkl`
- `failure_predictor.pkl`

### 5. Simulation and Recording Data

**Files:**
- `*.bag` - ROS bag files
- `recordings/` - Simulation recordings
- `simulation_data/` - Generated simulation data

### 6. Performance Profiling

**Files:**
- `*.prof` - Python profiling data
- `*.pstats` - Profiling statistics
- `profile_output/` - Profiling output directory

### 7. Temporary Development Files

**Files:**
- `TODO.md`
- `NOTES.md`
- `SCRATCH.md`
- `WIP_*.md` - Work in progress documents
- `DRAFT_*.md` - Draft documents

### 8. Local Configuration

**Files:**
- `.env`
- `.env.local`
- `local_config.yaml`
- `dev_config.yaml`

## Production-Ready Files

These files **SHOULD** be included in production:

### Essential Documentation
- `README.md` - Main project documentation
- `QUICKSTART.md` - Quick start guide
- `CHANGELOG.md` - Version history
- `CONTRIBUTING.md` - Contribution guidelines
- `RELEASE_NOTES_*.md` - Release notes
- `requirements.txt` - Python dependencies

### Documentation (docs/)
- `docs/INSTALLATION.md` - Installation guide
- `docs/TESTING_GUIDE.md` - Testing procedures
- `docs/TROUBLESHOOTING.md` - Troubleshooting guide
- `docs/IMPLEMENTATION_GUIDE.md` - Implementation details
- `docs/ADVANCED_SAFETY.md` - Safety system docs
- `docs/SEMANTIC_SLAM.md` - SLAM documentation
- `docs/PERFORMANCE_DASHBOARD.md` - Dashboard docs
- `docs/POINT_CLOUD_VISUALIZATION.md` - Visualization docs
- `docs/RVIZ_3D_VISUALIZATION_GUIDE.md` - RViz guide
- `docs/BEHAVIOR_TREE_SAFETY.md` - Safety behavior trees
- `docs/WORLD_SELECTION_GUIDE.md` - World selection
- `docs/LAUNCH_SYSTEM_ARCHITECTURE.md` - Launch system
- `docs/GAZEBO_OGRE2_FIX.md` - Gazebo fixes

### Source Code
- All files in `src/` packages (except test files)
- Launch files (`*.launch.py`)
- Configuration files (`*.yaml`, `*.xml`)
- URDF files (`*.urdf`, `*.xacro`)
- World files (`*.world`)
- RViz configs (`*.rviz`)

### Scripts (Production)
- `scripts/build_workspace.sh` - Build automation
- `scripts/check_dependencies.sh` - Dependency checking
- `scripts/ensure_build_deps.sh` - Dependency installation
- `scripts/install_dependencies.sh` - Installation
- `scripts/launch_robot.py` - Robot launcher
- `scripts/launch_simulation.sh` - Simulation launcher

### Spec Files
- `.kiro/specs/` - All specification files (for reference)

## Rationale

### Why Exclude These Files?

1. **Testing Scripts** - Only needed during development and CI/CD
2. **Reports** - Generated during development, not needed in production
3. **Test Results** - Temporary data from test runs
4. **Models** - Should be trained/downloaded during deployment
5. **Profiling Data** - Development optimization artifacts
6. **Temporary Docs** - Work-in-progress documentation
7. **Local Config** - User-specific settings

### Benefits

1. **Smaller Repository** - Reduced clone size
2. **Cleaner Releases** - Only essential files in releases
3. **Security** - No accidental exposure of test data or local configs
4. **Clarity** - Clear separation between dev and production files
5. **Performance** - Faster builds and deployments

## Verification

To check what files would be excluded:

```bash
# See what would be ignored
git status --ignored

# Check specific file
git check-ignore -v <filename>

# List all ignored files
git ls-files --others --ignored --exclude-standard
```

## Updating

When adding new development files:

1. Check if they match existing patterns in `.gitignore`
2. If not, add appropriate pattern to `.gitignore`
3. Update this document with the new pattern
4. Commit both `.gitignore` and this document

## Notes

- Test files in `src/*/test/` directories are kept (part of package structure)
- Package-specific README files are kept (documentation)
- Configuration templates are kept (examples for users)
- This document itself is production-ready (helps users understand the project)

---

**Last Updated:** November 13, 2025  
**Maintained By:** Development Team
