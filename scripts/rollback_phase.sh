#!/bin/bash

# Phase-specific Rollback Scripts for Cleanup Operations
# This script provides rollback capabilities for each cleanup phase
# Requirements: 6.1, 7.1

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Global variables
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_SYSTEM="${WORKSPACE_ROOT}/scripts/backup_system.sh"

# Function to rollback Phase 1: Backup Directory Removal
rollback_phase1() {
    log_info "Rolling back Phase 1: Backup Directory Removal"
    
    # Find the most recent Phase 1 backup
    local backup_id=$(jq -r '.backups[] | select(.phase_name == "phase1" or .phase_name == "backup_removal") | .backup_id' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null | tail -1)
    
    if [[ -z "$backup_id" ]]; then
        log_error "No Phase 1 backup found. Cannot rollback."
        return 1
    fi
    
    log_info "Found Phase 1 backup: $backup_id"
    
    # Use backup system to rollback
    "$BACKUP_SYSTEM" rollback "$backup_id" force
    
    log_success "Phase 1 rollback completed."
}

# Function to rollback Phase 2: Simulation File Consolidation
rollback_phase2() {
    log_info "Rolling back Phase 2: Simulation File Consolidation"
    
    local backup_id=$(jq -r '.backups[] | select(.phase_name == "phase2" or .phase_name == "simulation_consolidation") | .backup_id' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null | tail -1)
    
    if [[ -z "$backup_id" ]]; then
        log_error "No Phase 2 backup found. Cannot rollback."
        return 1
    fi
    
    log_info "Found Phase 2 backup: $backup_id"
    "$BACKUP_SYSTEM" rollback "$backup_id" force
    
    log_success "Phase 2 rollback completed."
}

# Function to rollback Phase 3: RViz Configuration Consolidation
rollback_phase3() {
    log_info "Rolling back Phase 3: RViz Configuration Consolidation"
    
    local backup_id=$(jq -r '.backups[] | select(.phase_name == "phase3" or .phase_name == "rviz_consolidation") | .backup_id' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null | tail -1)
    
    if [[ -z "$backup_id" ]]; then
        log_error "No Phase 3 backup found. Cannot rollback."
        return 1
    fi
    
    log_info "Found Phase 3 backup: $backup_id"
    "$BACKUP_SYSTEM" rollback "$backup_id" force
    
    log_success "Phase 3 rollback completed."
}

# Function to rollback Phase 4: URDF File Cleanup
rollback_phase4() {
    log_info "Rolling back Phase 4: URDF File Cleanup"
    
    local backup_id=$(jq -r '.backups[] | select(.phase_name == "phase4" or .phase_name == "urdf_cleanup") | .backup_id' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null | tail -1)
    
    if [[ -z "$backup_id" ]]; then
        log_error "No Phase 4 backup found. Cannot rollback."
        return 1
    fi
    
    log_info "Found Phase 4 backup: $backup_id"
    "$BACKUP_SYSTEM" rollback "$backup_id" force
    
    log_success "Phase 4 rollback completed."
}

# Function to rollback Phase 5: Configuration Deduplication
rollback_phase5() {
    log_info "Rolling back Phase 5: Configuration Deduplication"
    
    local backup_id=$(jq -r '.backups[] | select(.phase_name == "phase5" or .phase_name == "config_deduplication") | .backup_id' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null | tail -1)
    
    if [[ -z "$backup_id" ]]; then
        log_error "No Phase 5 backup found. Cannot rollback."
        return 1
    fi
    
    log_info "Found Phase 5 backup: $backup_id"
    "$BACKUP_SYSTEM" rollback "$backup_id" force
    
    log_success "Phase 5 rollback completed."
}

# Function to rollback Phase 6: Build Artifact Management
rollback_phase6() {
    log_info "Rolling back Phase 6: Build Artifact Management"
    
    local backup_id=$(jq -r '.backups[] | select(.phase_name == "phase6" or .phase_name == "build_artifacts") | .backup_id' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null | tail -1)
    
    if [[ -z "$backup_id" ]]; then
        log_error "No Phase 6 backup found. Cannot rollback."
        return 1
    fi
    
    log_info "Found Phase 6 backup: $backup_id"
    "$BACKUP_SYSTEM" rollback "$backup_id" force
    
    log_success "Phase 6 rollback completed."
}

# Function to rollback all phases in reverse order
rollback_all_phases() {
    log_info "Rolling back all cleanup phases in reverse order..."
    
    local phases=(6 5 4 3 2 1)
    local rollback_count=0
    
    for phase in "${phases[@]}"; do
        log_info "Attempting rollback of Phase $phase..."
        
        case $phase in
            6) rollback_phase6 && ((rollback_count++)) || log_warning "Phase 6 rollback failed or no backup found" ;;
            5) rollback_phase5 && ((rollback_count++)) || log_warning "Phase 5 rollback failed or no backup found" ;;
            4) rollback_phase4 && ((rollback_count++)) || log_warning "Phase 4 rollback failed or no backup found" ;;
            3) rollback_phase3 && ((rollback_count++)) || log_warning "Phase 3 rollback failed or no backup found" ;;
            2) rollback_phase2 && ((rollback_count++)) || log_warning "Phase 2 rollback failed or no backup found" ;;
            1) rollback_phase1 && ((rollback_count++)) || log_warning "Phase 1 rollback failed or no backup found" ;;
        esac
    done
    
    log_success "Rollback completed. $rollback_count phases rolled back."
    
    # Run validation after complete rollback
    log_info "Running validation after complete rollback..."
    local validation_script="${WORKSPACE_ROOT}/scripts/validate_cleanup.sh"
    if [[ -f "$validation_script" ]]; then
        "$validation_script" --full
    else
        log_warning "Validation script not found: $validation_script"
    fi
}

# Function to show available backups for rollback
show_available_rollbacks() {
    log_info "Available phase rollbacks:"
    
    if [[ ! -f "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" ]]; then
        log_warning "No backup manifest found. No rollbacks available."
        return 1
    fi
    
    echo ""
    echo "========================================="
    echo "        AVAILABLE PHASE ROLLBACKS"
    echo "========================================="
    
    local phases=(1 2 3 4 5 6)
    for phase in "${phases[@]}"; do
        local phase_names=()
        case $phase in
            1) phase_names=("phase1" "backup_removal") ;;
            2) phase_names=("phase2" "simulation_consolidation") ;;
            3) phase_names=("phase3" "rviz_consolidation") ;;
            4) phase_names=("phase4" "urdf_cleanup") ;;
            5) phase_names=("phase5" "config_deduplication") ;;
            6) phase_names=("phase6" "build_artifacts") ;;
        esac
        
        local found_backup=""
        for phase_name in "${phase_names[@]}"; do
            local backup_id=$(jq -r '.backups[] | select(.phase_name == "'$phase_name'") | .backup_id' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null | tail -1)
            if [[ -n "$backup_id" ]]; then
                found_backup="$backup_id"
                break
            fi
        done
        
        if [[ -n "$found_backup" ]]; then
            local backup_info=$(jq -r '.backups[] | select(.backup_id == "'$found_backup'") | "Description: " + .description + "\nTimestamp: " + .timestamp' "${WORKSPACE_ROOT}/.cleanup_backups/backup_manifest.json" 2>/dev/null)
            echo -e "${GREEN}Phase $phase: Available${NC}"
            echo "  Backup ID: $found_backup"
            echo "  $backup_info"
        else
            echo -e "${RED}Phase $phase: No backup available${NC}"
        fi
        echo ""
    done
    
    echo "========================================="
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Phase-specific Rollback Scripts for Cleanup Operations"
    echo ""
    echo "Commands:"
    echo "  phase1                 Rollback Phase 1: Backup Directory Removal"
    echo "  phase2                 Rollback Phase 2: Simulation File Consolidation"
    echo "  phase3                 Rollback Phase 3: RViz Configuration Consolidation"
    echo "  phase4                 Rollback Phase 4: URDF File Cleanup"
    echo "  phase5                 Rollback Phase 5: Configuration Deduplication"
    echo "  phase6                 Rollback Phase 6: Build Artifact Management"
    echo "  all                    Rollback all phases in reverse order"
    echo "  list                   Show available phase rollbacks"
    echo "  help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 phase1              # Rollback only Phase 1"
    echo "  $0 all                 # Rollback all phases"
    echo "  $0 list                # Show what rollbacks are available"
}

# Main script execution
main() {
    local command="${1:-}"
    
    # Check if backup system exists
    if [[ ! -f "$BACKUP_SYSTEM" ]]; then
        log_error "Backup system script not found: $BACKUP_SYSTEM"
        exit 1
    fi
    
    case "$command" in
        phase1)
            rollback_phase1
            ;;
        phase2)
            rollback_phase2
            ;;
        phase3)
            rollback_phase3
            ;;
        phase4)
            rollback_phase4
            ;;
        phase5)
            rollback_phase5
            ;;
        phase6)
            rollback_phase6
            ;;
        all)
            rollback_all_phases
            ;;
        list)
            show_available_rollbacks
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        "")
            log_error "No command specified."
            show_usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"