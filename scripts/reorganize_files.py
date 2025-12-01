#!/usr/bin/env python3
"""
File Reorganization Script
Comprehensive script for reorganizing project structure with dry-run, validation, and rollback capabilities.
"""

import os
import shutil
import json
import datetime
import hashlib
import subprocess
from pathlib import Path
from collections import defaultdict
import argparse
import sys

class FileReorganizer:
    """Main class for handling file reorganization operations."""
    
    def __init__(self, root_dir=".", dry_run=False, verbose=False):
        self.root_dir = Path(root_dir).resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        self.operations_log = []
        self.backup_dir = None
        self.rollback_data = {}
        
        # Define file mapping based on design specifications
        self.file_mappings = self._define_file_mappings()
        
    def _define_file_mappings(self):
        """Define comprehensive file mapping rules based on design specifications."""
        return {
            # Source code moves
            "source_files": {
                "app.py": "src/app.py",
                "core/": "src/core/",
                "managers/": "src/managers/", 
                "processors/": "src/processors/",
                "retrievers/": "src/retrievers/",
                "models/": "src/models/",
                "ui/": "src/ui/",
                "utils/": "src/utils/",
            },
            
            # Documentation moves
            "documentation": {
                "README_ENHANCED.md": "docs/README.md",
                "DOCKER_DEPLOYMENT.md": "docs/deployment/docker-deployment.md",
                "DOCKER_DESKTOP_GUIDE.md": "docs/deployment/docker-desktop-guide.md",
                "STREAMLIT_COMPATIBILITY.md": "docs/technical/streamlit-compatibility.md",
                "FRENCH_LANGUAGE_SUPPORT.md": "docs/technical/french-language-support.md",
                "UI_ENHANCEMENTS_GUIDE.md": "docs/technical/ui-enhancements-guide.md",
                "FINAL_VERIFICATION.md": "docs/technical/final-verification.md",
                "INTEGRATION_COMPLETE.md": "docs/technical/integration-complete.md",
                "ISSUE_RESOLUTION.md": "docs/technical/issue-resolution.md",
            },
            
            # Script moves
            "scripts": {
                "build-docker.sh": "scripts/docker/build-docker.sh",
                "quick-docker-check.sh": "scripts/docker/quick-docker-check.sh",
                "docker-troubleshoot.sh": "scripts/docker/docker-troubleshoot.sh",
                "fix-docker-desktop.sh": "scripts/docker/fix-docker-desktop.sh",
                "start-docker.sh": "scripts/docker/start-docker.sh",
                "setup-colima.sh": "scripts/docker/setup-colima.sh",
                "health-check.sh": "scripts/utilities/health-check.sh",
                "start_enhanced_system.sh": "scripts/utilities/start_enhanced_system.sh",
            },
            
            # Demo files
            "demos": {
                "demo_analytics_monitoring.py": "demos/analytics_monitoring.py",
                "demo_query_enhancer.py": "demos/query_enhancer.py", 
                "demo_response_synthesis.py": "demos/response_synthesis.py",
                "demo_ui_enhancements.py": "demos/ui_enhancements.py",
            },
            
            # Status and report files
            "reports": {
                # final_integration_report.json already moved to config/
                "system_status.py": "reports/system_status.py",
            },
            
            # Migration files (already in correct location, but ensure structure)
            "migration": {
                "migration_scripts/": "migration/scripts/",
            }
        }
    
    def _log_operation(self, operation_type, source, destination, status, details=""):
        """Log an operation for tracking and potential rollback."""
        operation = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": operation_type,
            "source": str(source),
            "destination": str(destination),
            "status": status,
            "details": details
        }
        self.operations_log.append(operation)
        
        if self.verbose:
            print(f"[{operation_type}] {source} -> {destination} ({status})")
    
    def _calculate_file_hash(self, filepath):
        """Calculate SHA256 hash for file integrity verification."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def create_backup(self):
        """Create a backup before reorganization."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.root_dir / "backup" / f"pre_reorganization_{timestamp}"
        
        print(f"Creating backup in: {self.backup_dir}")
        
        if not self.dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Use existing backup script
            backup_script = self.root_dir / "scripts" / "backup_project.py"
            if backup_script.exists():
                cmd = f"python {backup_script} --source {self.root_dir} --backup-dir {self.backup_dir.parent}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Backup failed: {result.stderr}")
            else:
                # Fallback manual backup
                self._manual_backup()
        
        self._log_operation("BACKUP", self.root_dir, self.backup_dir, "SUCCESS")
        return self.backup_dir
    
    def _manual_backup(self):
        """Manual backup implementation as fallback."""
        exclude_patterns = {'.git', '__pycache__', '.pytest_cache', '.venv', 'backup'}
        
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_patterns]
            
            if 'backup' in Path(root).parts:
                continue
                
            for file in files:
                if file.endswith(('.pyc', '.pyo')):
                    continue
                    
                source_path = Path(root) / file
                rel_path = source_path.relative_to(self.root_dir)
                dest_path = self.backup_dir / rel_path
                
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)
    
    def validate_mappings(self):
        """Validate that all source files exist and destinations are valid."""
        validation_results = {
            "valid": [],
            "missing_sources": [],
            "invalid_destinations": [],
            "conflicts": []
        }
        
        all_moves = []
        
        # Collect all moves from mappings
        for category, mappings in self.file_mappings.items():
            for source, destination in mappings.items():
                source_path = self.root_dir / source
                dest_path = self.root_dir / destination
                
                # Check if source exists
                if source.endswith('/'):
                    # Directory mapping
                    if source_path.exists() and source_path.is_dir():
                        # Add all files in directory
                        for file_path in source_path.rglob('*'):
                            if file_path.is_file():
                                rel_path = file_path.relative_to(source_path)
                                file_dest = dest_path / rel_path
                                all_moves.append((file_path, file_dest, category))
                    else:
                        validation_results["missing_sources"].append(str(source_path))
                else:
                    # File mapping
                    if source_path.exists():
                        all_moves.append((source_path, dest_path, category))
                    else:
                        validation_results["missing_sources"].append(str(source_path))
        
        # Check for conflicts and validate destinations
        dest_paths = set()
        for source_path, dest_path, category in all_moves:
            # Check for destination conflicts
            if str(dest_path) in dest_paths:
                validation_results["conflicts"].append(f"Multiple files mapping to: {dest_path}")
            else:
                dest_paths.add(str(dest_path))
            
            # Validate destination directory can be created
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                validation_results["valid"].append((str(source_path), str(dest_path), category))
            except Exception as e:
                validation_results["invalid_destinations"].append(f"{dest_path}: {str(e)}")
        
        return validation_results, all_moves
    
    def preview_reorganization(self):
        """Preview what the reorganization will do without executing."""
        print("REORGANIZATION PREVIEW")
        print("=" * 50)
        
        validation_results, all_moves = self.validate_mappings()
        
        # Show validation results
        if validation_results["missing_sources"]:
            print("\nMISSING SOURCE FILES:")
            for source in validation_results["missing_sources"]:
                print(f"  ❌ {source}")
        
        if validation_results["conflicts"]:
            print("\nCONFLICTS:")
            for conflict in validation_results["conflicts"]:
                print(f"  ⚠️  {conflict}")
        
        if validation_results["invalid_destinations"]:
            print("\nINVALID DESTINATIONS:")
            for dest in validation_results["invalid_destinations"]:
                print(f"  ❌ {dest}")
        
        # Show planned moves by category
        moves_by_category = defaultdict(list)
        for source_path, dest_path, category in all_moves:
            moves_by_category[category].append((source_path, dest_path))
        
        print(f"\nPLANNED MOVES ({len(all_moves)} total):")
        for category, moves in moves_by_category.items():
            print(f"\n{category.upper()} ({len(moves)} files):")
            for source_path, dest_path in moves[:5]:  # Show first 5
                print(f"  {source_path} -> {dest_path}")
            if len(moves) > 5:
                print(f"  ... and {len(moves) - 5} more files")
        
        # Show directory structure that will be created
        new_dirs = set()
        for _, dest_path, _ in all_moves:
            new_dirs.add(str(dest_path.parent))
        
        print(f"\nNEW DIRECTORIES TO CREATE ({len(new_dirs)}):")
        for dir_path in sorted(new_dirs)[:10]:  # Show first 10
            print(f"  📁 {dir_path}")
        if len(new_dirs) > 10:
            print(f"  ... and {len(new_dirs) - 10} more directories")
        
        return len(validation_results["missing_sources"]) == 0 and len(validation_results["conflicts"]) == 0
    
    def execute_reorganization(self):
        """Execute the file reorganization."""
        print("EXECUTING REORGANIZATION")
        print("=" * 50)
        
        # Validate first
        validation_results, all_moves = self.validate_mappings()
        
        if validation_results["missing_sources"] or validation_results["conflicts"]:
            print("❌ Validation failed. Cannot proceed with reorganization.")
            return False
        
        # Create backup
        if not self.dry_run:
            self.create_backup()
        
        # Execute moves
        success_count = 0
        error_count = 0
        
        for source_path, dest_path, category in all_moves:
            try:
                if not self.dry_run:
                    # Create destination directory
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Calculate source hash for verification
                    source_hash = self._calculate_file_hash(source_path)
                    
                    # Move file
                    shutil.move(str(source_path), str(dest_path))
                    
                    # Verify move
                    dest_hash = self._calculate_file_hash(dest_path)
                    if source_hash != dest_hash:
                        raise Exception("File integrity check failed after move")
                    
                    # Store rollback information
                    self.rollback_data[str(dest_path)] = {
                        "original_path": str(source_path),
                        "hash": source_hash,
                        "category": category
                    }
                
                self._log_operation("MOVE", source_path, dest_path, "SUCCESS", category)
                success_count += 1
                
            except Exception as e:
                self._log_operation("MOVE", source_path, dest_path, "ERROR", str(e))
                error_count += 1
                print(f"❌ Error moving {source_path}: {str(e)}")
        
        print(f"\nReorganization completed: {success_count} successful, {error_count} errors")
        
        # Save operations log and rollback data
        if not self.dry_run:
            self._save_operation_logs()
        
        return error_count == 0
    
    def _save_operation_logs(self):
        """Save operation logs and rollback data."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save operations log
        log_file = self.root_dir / f"reorganization_log_{timestamp}.json"
        with open(log_file, 'w') as f:
            json.dump(self.operations_log, f, indent=2)
        
        # Save rollback data
        rollback_file = self.root_dir / f"rollback_data_{timestamp}.json"
        with open(rollback_file, 'w') as f:
            json.dump(self.rollback_data, f, indent=2)
        
        print(f"📝 Operations log saved to: {log_file}")
        print(f"🔄 Rollback data saved to: {rollback_file}")
    
    def rollback_reorganization(self, rollback_file):
        """Rollback reorganization using saved rollback data."""
        print("ROLLING BACK REORGANIZATION")
        print("=" * 50)
        
        if not Path(rollback_file).exists():
            print(f"❌ Rollback file not found: {rollback_file}")
            return False
        
        with open(rollback_file, 'r') as f:
            rollback_data = json.load(f)
        
        success_count = 0
        error_count = 0
        
        for dest_path, info in rollback_data.items():
            try:
                original_path = info["original_path"]
                expected_hash = info["hash"]
                
                if not self.dry_run:
                    # Verify file integrity before rollback
                    current_hash = self._calculate_file_hash(dest_path)
                    if current_hash != expected_hash:
                        print(f"⚠️  Warning: File {dest_path} has been modified since reorganization")
                    
                    # Create original directory if needed
                    Path(original_path).parent.mkdir(parents=True, exist_ok=True)
                    
                    # Move file back
                    shutil.move(dest_path, original_path)
                
                self._log_operation("ROLLBACK", dest_path, original_path, "SUCCESS")
                success_count += 1
                
            except Exception as e:
                self._log_operation("ROLLBACK", dest_path, original_path, "ERROR", str(e))
                error_count += 1
                print(f"❌ Error rolling back {dest_path}: {str(e)}")
        
        print(f"\nRollback completed: {success_count} successful, {error_count} errors")
        return error_count == 0
    
    def update_import_statements(self):
        """Update import statements to reflect new file locations."""
        print("UPDATING IMPORT STATEMENTS")
        print("=" * 50)
        
        # This is a placeholder for import statement updates
        # The actual implementation would scan Python files and update imports
        print("⚠️  Import statement updates need to be implemented separately")
        print("   Use the import analyzer script to identify required changes")
        
        return True


def main():
    """Main function to handle command line interface."""
    parser = argparse.ArgumentParser(description="Reorganize project file structure")
    parser.add_argument("--root", default=".", help="Root directory of project")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--rollback", help="Rollback using specified rollback data file")
    parser.add_argument("--preview-only", action="store_true", help="Only show preview, don't execute")
    
    args = parser.parse_args()
    
    reorganizer = FileReorganizer(
        root_dir=args.root,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    try:
        if args.rollback:
            success = reorganizer.rollback_reorganization(args.rollback)
        elif args.preview_only or args.dry_run:
            success = reorganizer.preview_reorganization()
            if success:
                print("\n✅ Preview completed successfully. No issues found.")
                if not args.dry_run:
                    print("   Run without --preview-only to execute reorganization.")
            else:
                print("\n❌ Preview found issues. Please resolve before proceeding.")
        else:
            # Show preview first
            print("Showing preview before execution...\n")
            preview_success = reorganizer.preview_reorganization()
            
            if not preview_success:
                print("\n❌ Preview found issues. Aborting reorganization.")
                return False
            
            # Ask for confirmation
            response = input("\nProceed with reorganization? (y/N): ")
            if response.lower() != 'y':
                print("Reorganization cancelled.")
                return False
            
            # Execute reorganization
            success = reorganizer.execute_reorganization()
            
            if success:
                print("\n✅ Reorganization completed successfully!")
                print("   Remember to update import statements and test functionality.")
            else:
                print("\n❌ Reorganization completed with errors. Check logs for details.")
        
        return success
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)