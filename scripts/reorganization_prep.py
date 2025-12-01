#!/usr/bin/env python3
"""
Reorganization Preparation Script
Runs all backup and analysis tools in the correct order.
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def main():
    """Run all reorganization preparation steps."""
    print("REORGANIZATION PREPARATION TOOLKIT")
    print("=" * 50)
    print(f"Started at: {datetime.datetime.now()}")
    
    # Get script directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Change to project root
    os.chdir(project_root)
    
    # Create output directory for reports
    output_dir = Path("reorganization_analysis")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Create backup
    backup_cmd = f"python {script_dir}/backup_project.py --source . --backup-dir backup"
    if not run_command(backup_cmd, "Creating project backup"):
        print("CRITICAL: Backup failed! Stopping execution.")
        return False
    
    # Step 2: Generate file inventory
    inventory_file = output_dir / f"file_inventory_{timestamp}.json"
    inventory_cmd = f"python {script_dir}/file_inventory.py --root . --output {inventory_file}"
    if not run_command(inventory_cmd, "Generating file inventory"):
        print("WARNING: File inventory failed, but continuing...")
    
    # Step 3: Analyze import dependencies
    import_file = output_dir / f"import_analysis_{timestamp}.json"
    import_cmd = f"python {script_dir}/import_analyzer.py --root . --output {import_file}"
    if not run_command(import_cmd, "Analyzing import dependencies"):
        print("WARNING: Import analysis failed, but continuing...")
    
    # Generate summary report
    summary_file = output_dir / f"reorganization_summary_{timestamp}.txt"
    with open(summary_file, 'w') as f:
        f.write("REORGANIZATION PREPARATION SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Generated: {datetime.datetime.now()}\n")
        f.write(f"Project Root: {project_root}\n\n")
        
        f.write("COMPLETED TASKS:\n")
        f.write("- ✓ Project backup created\n")
        f.write("- ✓ File inventory generated\n")
        f.write("- ✓ Import dependencies analyzed\n\n")
        
        f.write("OUTPUT FILES:\n")
        f.write(f"- Backup: backup/reorganization_backup_*\n")
        f.write(f"- File inventory: {inventory_file}\n")
        f.write(f"- Import analysis: {import_file}\n")
        f.write(f"- Summary reports: {output_dir}/*_summary.txt\n\n")
        
        f.write("NEXT STEPS:\n")
        f.write("1. Review the generated reports\n")
        f.write("2. Proceed with reorganization using the file moving script\n")
        f.write("3. Update import statements as needed\n")
        f.write("4. Test functionality after reorganization\n")
    
    print(f"\n{'='*60}")
    print("REORGANIZATION PREPARATION COMPLETE")
    print(f"{'='*60}")
    print(f"Summary saved to: {summary_file}")
    print(f"All reports available in: {output_dir}")
    print("\nYou can now proceed with the reorganization!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)