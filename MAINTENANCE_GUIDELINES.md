# Maintenance Guidelines

This document provides comprehensive guidelines for maintaining the clean, organized structure of the Dojo robot codebase and preventing the accumulation of redundant files and backup artifacts.

## Table of Contents
- [Overview](#overview)
- [Daily Development Practices](#daily-development-practices)
- [File Management Guidelines](#file-management-guidelines)
- [Backup Prevention](#backup-prevention)
- [Regular Maintenance Tasks](#regular-maintenance-tasks)
- [Code Review Checklist](#code-review-checklist)
- [Monitoring and Alerts](#monitoring-and-alerts)

## Overview

The Dojo robot codebase has been systematically cleaned to remove redundancy and establish clear organization patterns. These guidelines ensure the codebase remains clean, maintainable, and free from the accumulation of backup files and duplicates that previously caused confusion.

### Key Principles
1. **Single Source of Truth**: Each file type should have one authoritative version
2. **Clear Purpose**: Every file must have a documented, distinct purpose
3. **No Backup Accumulation**: Prevent creation of `.backup`, `.old`, or similar files
4. **Consistent Naming**: Follow established naming conventions
5. **Regular Cleanup**: Perform periodic maintenance to prevent drift

## Daily Development Practices

### Before Adding New Files

#### 1. Check for Existing Similar Files
```bash
# Search for similar functionality
find src/ -name "*similar_name*" -type f
grep -r "similar_functionality" src/

# Check launch files
find src/ -name "*.launch.py" | grep -i "keyword"

# Check configuration files
find src/ -name "*.yaml" | grep -i "config_type"
```

#### 2. Verify File Necessity
Ask these questions before creating new files:
- Does a similar file already exist?
- Can existing functionality be extended instead?
- Is this file truly necessary or just convenient?
- Does it serve a distinct purpose from existing files?

#### 3. Follow Naming Conventions
Refer to [FILE_ORGANIZATION_GUIDE.md](FILE_ORGANIZATION_GUIDE.md) for:
- File naming patterns
- Directory placement rules
- Documentation requirements

### During Development

#### 1. Avoid Creating Backup Files
**Never create files with these patterns:**
- `*.backup`
- `*.old`
- `*.bak`
- `*_backup.*`
- `*_old.*`
- `*.orig`

**Instead, use version control:**
```bash
# Create a branch for experimental changes
git checkout -b feature/experimental-changes

# Make changes and commit
git add .
git commit -m "Experimental changes"

# If changes don't work, switch back
git checkout main
```

#### 2. Use Descriptive Commit Messages
```bash
# Good commit messages
git commit -m "Add perception launch file for camera-only mode"
git commit -m "Consolidate duplicate RViz configurations"
git commit -m "Remove redundant simulation launch file"

# Avoid generic messages
git commit -m "Update files"
git commit -m "Fix stuff"
```

#### 3. Clean Up Temporary Files
```bash
# Remove temporary files before committing
find . -name "*.tmp" -delete
find . -name "*.temp" -delete
find . -name "*~" -delete
```

## File Management Guidelines

### Launch Files

#### Maximum Limits
- **robot_gazebo**: Maximum 3 launch files
- **robot_description**: Maximum 3 launch files  
- **Other packages**: Maximum 4 launch files per package

#### Before Adding New Launch Files
1. **Review existing launch files** in the package
2. **Check if functionality can be added** to existing files via parameters
3. **Consider if a new parameter** would be better than a new file
4. **Document the distinct purpose** of the new launch file

#### Launch File Checklist
- [ ] Serves a distinct purpose from existing launch files
- [ ] Has comprehensive docstring explaining purpose and parameters
- [ ] Uses descriptive filename following naming conventions
- [ ] Includes parameter validation and default values
- [ ] Updated package README with launch file description

### Configuration Files

#### Deduplication Rules
1. **Compare before creating**: Check for similar configuration files
2. **Merge when possible**: Combine configurations with similar purposes
3. **Document differences**: Clearly explain why separate configs are needed
4. **Use namespaces**: Group related parameters under clear namespaces

#### Configuration File Checklist
- [ ] No duplicate parameters across files in same package
- [ ] Clear, descriptive filename indicating purpose
- [ ] Comprehensive comments explaining parameters
- [ ] Follows YAML best practices (consistent indentation, clear structure)
- [ ] Updated configuration README with file description

### RViz Configurations

#### Strict Limits
- **Maximum 3 RViz configurations per package**
- Each configuration must serve a **distinct visualization purpose**

#### Before Adding RViz Configurations
1. **Review existing configurations** in the package
2. **Check if displays can be added** to existing configurations
3. **Verify distinct purpose** - avoid overlapping functionality
4. **Consider user workflow** - when would someone use this vs. existing configs?

#### RViz Configuration Checklist
- [ ] Serves distinct visualization purpose
- [ ] Maximum 3 configs per package not exceeded
- [ ] Descriptive filename indicating visualization scenario
- [ ] Appropriate displays configured for intended use case
- [ ] Updated package README with configuration description

### URDF Files

#### Hierarchy Rules
1. **One primary xacro file** per robot (`robot.urdf.xacro`)
2. **One compiled URDF** (`robot.urdf`) - auto-generated only
3. **Component-specific xacros** in logical subdirectories
4. **No backup or alternative versions**

#### URDF Maintenance Checklist
- [ ] Changes made to `.xacro` files, never `.urdf` directly
- [ ] Compiled URDF regenerated after xacro changes
- [ ] No backup files (`.clean`, `.backup`, etc.) created
- [ ] Component xacros in appropriate subdirectories
- [ ] Documentation updated with file relationships

## Backup Prevention

### Version Control Best Practices

#### Use Branches Instead of Backup Files
```bash
# Instead of creating backup files, use branches
git checkout -b backup/before-major-changes
git checkout main

# Make changes on main branch
# If needed, compare or restore from backup branch
git diff backup/before-major-changes main
```

#### Stash Changes Instead of Backup Files
```bash
# Instead of creating .backup files, use git stash
git stash push -m "Experimental changes before refactor"

# Make other changes
# Restore stashed changes later if needed
git stash pop
```

### IDE Configuration

#### Configure Your Editor
Prevent automatic backup file creation:

**VS Code (`settings.json`):**
```json
{
  "files.hotExit": "off",
  "files.autoSave": "off"
}
```

**Vim (`.vimrc`):**
```vim
set nobackup
set nowritebackup
set noswapfile
```

**Emacs (`.emacs`):**
```lisp
(setq make-backup-files nil)
(setq auto-save-default nil)
```

### Git Configuration

#### Update .gitignore
Ensure comprehensive patterns to prevent backup files:
```gitignore
# Backup files
*.backup
*.bak
*.old
*.orig
*~
*.tmp
*.temp

# Editor backup files
.#*
\#*#
*.swp
*.swo
*~

# IDE files
.vscode/settings.json
.idea/
```

## Regular Maintenance Tasks

### Weekly Tasks

#### 1. Scan for Backup Files
```bash
# Run weekly scan for backup files
find . -name "*.backup" -o -name "*.bak" -o -name "*.old" -o -name "*~"

# If found, investigate and remove
# Determine why they were created and prevent recurrence
```

#### 2. Review Recent Additions
```bash
# Check files added in last week
git log --since="1 week ago" --name-only --pretty=format: | sort | uniq

# Review for:
# - Duplicate functionality
# - Backup file patterns
# - Unclear naming
```

#### 3. Validate Launch File Count
```bash
# Check launch file counts per package
for pkg in src/*/; do
  count=$(find "$pkg/launch" -name "*.launch.py" 2>/dev/null | wc -l)
  if [ $count -gt 4 ]; then
    echo "WARNING: $pkg has $count launch files (max recommended: 4)"
  fi
done
```

### Monthly Tasks

#### 1. Configuration File Audit
```bash
# Find similar configuration files
find src/ -name "*.yaml" | sort | while read file; do
  basename=$(basename "$file" .yaml)
  similar=$(find src/ -name "*${basename}*" -name "*.yaml" | grep -v "$file")
  if [ -n "$similar" ]; then
    echo "Similar configs found for $file:"
    echo "$similar"
  fi
done
```

#### 2. RViz Configuration Review
```bash
# Check RViz configuration counts
for pkg in src/*/; do
  count=$(find "$pkg/rviz" -name "*.rviz" 2>/dev/null | wc -l)
  if [ $count -gt 3 ]; then
    echo "WARNING: $pkg has $count RViz configs (max recommended: 3)"
  fi
done
```

#### 3. Documentation Sync Check
```bash
# Verify README files are up to date
find src/ -name "README.md" -exec grep -l "TODO\|FIXME\|outdated" {} \;
```

### Quarterly Tasks

#### 1. Comprehensive Structure Review
- Review entire package structure against [FILE_ORGANIZATION_GUIDE.md](FILE_ORGANIZATION_GUIDE.md)
- Identify any drift from established patterns
- Plan cleanup activities if needed

#### 2. Dependency Cleanup
```bash
# Check for unused dependencies
colcon list --packages-up-to robot_control
# Review package.xml files for unused dependencies
```

#### 3. Performance Impact Assessment
- Measure build times and compare to baseline
- Identify any performance degradation from file accumulation
- Plan optimization if needed

## Code Review Checklist

### For All Pull Requests

#### File Addition Review
- [ ] No backup files added (`.backup`, `.old`, `.bak`, etc.)
- [ ] New files follow naming conventions
- [ ] New files have distinct, documented purposes
- [ ] No duplicate functionality introduced
- [ ] Appropriate directory placement

#### Launch File Review
- [ ] Launch file count limits not exceeded
- [ ] Comprehensive docstring with purpose and parameters
- [ ] No duplicate launch functionality
- [ ] Parameters have reasonable defaults
- [ ] Updated package README

#### Configuration File Review
- [ ] No duplicate parameters across files
- [ ] Clear parameter organization and comments
- [ ] Follows established naming patterns
- [ ] Updated configuration README

#### RViz Configuration Review
- [ ] RViz config count limits not exceeded (max 3 per package)
- [ ] Distinct visualization purpose
- [ ] No duplicate display configurations
- [ ] Updated package README

#### Documentation Review
- [ ] README files updated for new functionality
- [ ] Clear documentation of file purposes
- [ ] No outdated references to removed files
- [ ] Consistent documentation style

### Reviewer Guidelines

#### Red Flags to Watch For
1. **Multiple similar files** being added simultaneously
2. **Generic filenames** like `config.yaml`, `test.launch.py`
3. **Backup file patterns** in any form
4. **Undocumented file purposes**
5. **Exceeding file count limits**

#### Questions to Ask
1. "Could this functionality be added to an existing file?"
2. "Is the purpose of this file clearly distinct from existing files?"
3. "Are we following the established naming conventions?"
4. "Is the documentation updated appropriately?"

## Monitoring and Alerts

### Automated Checks

#### Pre-commit Hooks
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Check for backup files
backup_files=$(find . -name "*.backup" -o -name "*.bak" -o -name "*.old" -o -name "*~")
if [ -n "$backup_files" ]; then
  echo "ERROR: Backup files found:"
  echo "$backup_files"
  echo "Remove backup files before committing"
  exit 1
fi

# Check launch file counts
for pkg in src/*/; do
  count=$(find "$pkg/launch" -name "*.launch.py" 2>/dev/null | wc -l)
  if [ $count -gt 4 ]; then
    echo "WARNING: $pkg has $count launch files (recommended max: 4)"
  fi
done
```

#### CI/CD Integration
Add to your CI pipeline:
```yaml
# .github/workflows/maintenance-check.yml
name: Maintenance Check
on: [push, pull_request]
jobs:
  maintenance-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check for backup files
        run: |
          if find . -name "*.backup" -o -name "*.bak" -o -name "*.old" | grep -q .; then
            echo "Backup files found - failing build"
            exit 1
          fi
      - name: Check file counts
        run: ./scripts/check_file_counts.sh
```

### Metrics Tracking

#### File Count Tracking
```bash
# Create monthly reports
echo "$(date): Launch files: $(find src/ -name "*.launch.py" | wc -l)" >> metrics/file_counts.log
echo "$(date): RViz configs: $(find src/ -name "*.rviz" | wc -l)" >> metrics/file_counts.log
echo "$(date): Config files: $(find src/ -name "*.yaml" | wc -l)" >> metrics/file_counts.log
```

#### Repository Size Tracking
```bash
# Track repository size growth
du -sh . >> metrics/repo_size.log
```

## Emergency Procedures

### If Backup Files Accumulate

#### Immediate Actions
1. **Stop development** and assess the situation
2. **Identify the source** of backup file creation
3. **Review recent changes** that may have caused the issue
4. **Clean up backup files** using version control history

#### Investigation Steps
```bash
# Find all backup files
find . -name "*.backup" -o -name "*.bak" -o -name "*.old" -o -name "*~"

# Check when they were created
find . -name "*.backup" -exec ls -la {} \;

# Check git history for when they appeared
git log --name-only --since="1 week ago" | grep -E "\.(backup|bak|old)$"
```

#### Recovery Process
1. **Backup current state** (ironically, but using git)
2. **Remove backup files** after verifying they're not needed
3. **Update .gitignore** to prevent recurrence
4. **Fix the root cause** (editor settings, scripts, etc.)
5. **Document the incident** and prevention measures

### If File Counts Exceed Limits

#### Assessment Process
1. **Document current state** and file purposes
2. **Identify consolidation opportunities**
3. **Plan consolidation strategy**
4. **Execute consolidation with testing**
5. **Update documentation**

#### Consolidation Strategy
```bash
# For launch files - merge similar functionality
# For RViz configs - combine compatible displays
# For config files - merge related parameters
# Document all changes in CLEANUP_CHANGES_LOG.md
```

## Tools and Scripts

### Maintenance Scripts

#### File Count Checker (`scripts/check_file_counts.sh`)
```bash
#!/bin/bash
# Check file counts across packages
for pkg in src/*/; do
  pkg_name=$(basename "$pkg")
  launch_count=$(find "$pkg/launch" -name "*.launch.py" 2>/dev/null | wc -l)
  rviz_count=$(find "$pkg/rviz" -name "*.rviz" 2>/dev/null | wc -l)
  
  if [ $launch_count -gt 4 ]; then
    echo "WARNING: $pkg_name has $launch_count launch files (max: 4)"
  fi
  
  if [ $rviz_count -gt 3 ]; then
    echo "WARNING: $pkg_name has $rviz_count RViz configs (max: 3)"
  fi
done
```

#### Backup File Scanner (`scripts/scan_backup_files.sh`)
```bash
#!/bin/bash
# Scan for backup files and report
backup_files=$(find . -name "*.backup" -o -name "*.bak" -o -name "*.old" -o -name "*~")
if [ -n "$backup_files" ]; then
  echo "Backup files found:"
  echo "$backup_files"
  exit 1
else
  echo "No backup files found - good!"
fi
```

### Recommended Tools

#### File Organization
- **`tree`** - Visualize directory structure
- **`find`** - Search for files by pattern
- **`grep`** - Search file contents
- **`colcon`** - ROS2 build system with package management

#### Version Control
- **Git branches** - Instead of backup files
- **Git stash** - Temporary change storage
- **Git hooks** - Automated checks

#### Monitoring
- **`watch`** - Monitor file counts in real-time
- **`du`** - Track directory sizes
- **Custom scripts** - Automated maintenance checks

## Conclusion

Maintaining a clean, organized codebase requires consistent effort and adherence to established guidelines. By following these maintenance practices, the Dojo robot codebase will remain:

- **Easy to navigate** and understand
- **Free from redundancy** and confusion
- **Maintainable** by current and future developers
- **Scalable** for additional functionality

Regular application of these guidelines, combined with automated checks and team awareness, will prevent the accumulation of technical debt and maintain the high-quality organization achieved through the cleanup process.

Remember: **Prevention is easier than cleanup**. Following these guidelines consistently will save significant time and effort compared to periodic major cleanup operations.