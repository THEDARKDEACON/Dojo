# Requirements Document

## Introduction

The Dojo robot codebase has accumulated significant redundancy over time, including multiple backup directories, duplicate simulation files, redundant configuration files, and scattered backup files. This cleanup project aims to streamline the codebase by removing unnecessary duplicates, consolidating essential files, and establishing clear organization patterns to improve maintainability and reduce confusion for developers.

## Requirements

### Requirement 1

**User Story:** As a developer, I want backup directories and redundant packages removed, so that the codebase is clean and I don't accidentally work with outdated code.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN the `backup_packages/` directory SHALL be completely removed
2. WHEN the cleanup is complete THEN the `backup_redundant_launch_files/` directory SHALL be completely removed
3. WHEN the cleanup is complete THEN all scattered `.backup` files SHALL be removed from the source tree
4. WHEN the cleanup is complete THEN no COLCON_IGNORE files SHALL remain in the active source tree
5. IF any backup content is deemed necessary THEN it SHALL be properly documented before removal

### Requirement 2

**User Story:** As a developer, I want simulation launch files consolidated, so that I have clear, single-purpose launch options without confusion.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN there SHALL be exactly one primary simulation launch file in the robot_gazebo package
2. WHEN the cleanup is complete THEN there SHALL be exactly one gazebo launch file for basic Gazebo startup
3. WHEN the cleanup is complete THEN redundant simulation scripts in the scripts/ directory SHALL be consolidated or removed
4. WHEN the cleanup is complete THEN all remaining simulation launch files SHALL have clear, distinct purposes
5. WHEN the cleanup is complete THEN documentation SHALL clearly specify which launch file to use for different scenarios

### Requirement 3

**User Story:** As a developer, I want RViz configuration files consolidated, so that I can easily choose the right visualization setup without being overwhelmed by options.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN there SHALL be no more than 3 RViz configuration files per package
2. WHEN the cleanup is complete THEN each RViz configuration SHALL have a distinct, documented purpose
3. WHEN the cleanup is complete THEN duplicate RViz configurations with similar content SHALL be merged or removed
4. WHEN the cleanup is complete THEN RViz configurations SHALL be named clearly to indicate their purpose
5. WHEN the cleanup is complete THEN documentation SHALL specify when to use each RViz configuration

### Requirement 4

**User Story:** As a developer, I want URDF files cleaned up, so that I work with the correct robot description without confusion about which file is current.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN there SHALL be one primary URDF xacro file for the robot
2. WHEN the cleanup is complete THEN there SHALL be one compiled URDF file that matches the xacro
3. WHEN the cleanup is complete THEN backup and alternative URDF files SHALL be removed unless actively used
4. WHEN the cleanup is complete THEN orphaned URDF files in the root directory SHALL be removed or relocated
5. WHEN the cleanup is complete THEN the relationship between xacro and compiled URDF files SHALL be clearly documented

### Requirement 5

**User Story:** As a developer, I want configuration files deduplicated, so that I maintain consistent parameters without conflicting definitions.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN duplicate configuration files with similar content SHALL be merged or one SHALL be removed
2. WHEN the cleanup is complete THEN each configuration file SHALL have a clear, documented purpose
3. WHEN the cleanup is complete THEN configuration file naming SHALL be consistent and descriptive
4. WHEN the cleanup is complete THEN any remaining similar configuration files SHALL have documented differences
5. WHEN the cleanup is complete THEN configuration file locations SHALL follow ROS2 package conventions

### Requirement 6

**User Story:** As a developer, I want build artifacts properly managed, so that my workspace stays clean and version control ignores generated files.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN a comprehensive .gitignore file SHALL exist covering all build artifacts
2. WHEN the cleanup is complete THEN build/, install/, and log/ directories SHALL be properly ignored by version control
3. WHEN the cleanup is complete THEN temporary build artifacts SHALL be removed from the repository
4. WHEN the cleanup is complete THEN symlink manifests and build logs SHALL not be tracked in version control
5. WHEN the cleanup is complete THEN the workspace SHALL have clear separation between source and generated files

### Requirement 7

**User Story:** As a developer, I want clear documentation of the cleaned structure, so that I understand the new organization and can maintain it going forward.

#### Acceptance Criteria

1. WHEN the cleanup is complete THEN documentation SHALL list all removed files and directories
2. WHEN the cleanup is complete THEN documentation SHALL explain the purpose of each remaining file type
3. WHEN the cleanup is complete THEN documentation SHALL provide guidelines for maintaining the clean structure
4. WHEN the cleanup is complete THEN documentation SHALL specify naming conventions for future files
5. WHEN the cleanup is complete THEN documentation SHALL include a before/after comparison of the file structure