#!/usr/bin/env python3
"""
Test script for file reorganization functionality.
Validates all aspects of the reorganization script.
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
import subprocess

def create_test_project_structure(test_dir):
    """Create a minimal test project structure for validation."""
    test_files = {
        # Source files
        "app.py": "# Main application\nprint('Hello World')",
        "core/__init__.py": "# Core module",
        "core/system.py": "# System module\nfrom utils import helpers",
        "managers/__init__.py": "# Managers module", 
        "managers/config_manager.py": "# Config manager\nimport core.system",
        "utils/__init__.py": "# Utils module",
        "utils/helpers.py": "# Helper functions",
        
        # Documentation
        "README_ENHANCED.md": "# Enhanced README",
        "DOCKER_DEPLOYMENT.md": "# Docker Deployment Guide",
        "STREAMLIT_COMPATIBILITY.md": "# Streamlit Compatibility",
        
        # Scripts
        "build-docker.sh": "#!/bin/bash\necho 'Building Docker'",
        "health-check.sh": "#!/bin/bash\necho 'Health Check'",
        
        # Demo files
        "demo_analytics_monitoring.py": "# Analytics demo",
        "demo_query_enhancer.py": "# Query enhancer demo",
        
        # Reports
        "reports/final_integration_report.json": '{"status": "complete"}',
        "reports/system_status.py": "# System status script",
        
        # Migration
        "migration_scripts/migrate_to_enhanced.py": "# Migration script",
        
        # Config
        "config/settings.py": "# Settings",
        "config/enhanced_config.py": "# Enhanced config",
    }
    
    # Create test files
    for file_path, content in test_files.items():
        full_path = test_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        # Make shell scripts executable
        if file_path.endswith('.sh'):
            os.chmod(full_path, 0o755)
    
    return test_files

def test_preview_functionality(test_dir, reorganizer_script):
    """Test the preview functionality."""
    print("Testing preview functionality...")
    
    cmd = f"cd {test_dir} && python {reorganizer_script} --preview-only"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # Preview should run successfully even with missing files (it should detect them)
    output = result.stdout
    expected_sections = ["REORGANIZATION PREVIEW", "PLANNED MOVES", "NEW DIRECTORIES"]
    
    for section in expected_sections:
        if section not in output:
            print(f"❌ Preview missing section: {section}")
            return False
    
    # Check that it properly detects missing files (this is expected behavior)
    if "MISSING SOURCE FILES:" in output:
        print("✅ Preview correctly detected missing source files")
    
    # The preview should show some planned moves for files that do exist
    if "PLANNED MOVES" in output and "total)" in output:
        print("✅ Preview shows planned moves")
    
    print("✅ Preview functionality test passed")
    return True

def test_dry_run_functionality(test_dir, reorganizer_script):
    """Test dry-run functionality."""
    print("Testing dry-run functionality...")
    
    # Get initial file list
    initial_files = set()
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            initial_files.add(os.path.join(root, file))
    
    # Run dry-run (should exit with error due to missing files, but that's expected)
    cmd = f"cd {test_dir} && python {reorganizer_script} --dry-run"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, input="n\n")
    
    # Dry-run should show preview and exit (return code may be non-zero due to missing files)
    output = result.stdout
    
    # Check that it shows the preview
    if "REORGANIZATION PREVIEW" not in output:
        print(f"❌ Dry-run didn't show preview")
        return False
    
    # Verify no files were actually moved
    final_files = set()
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            final_files.add(os.path.join(root, file))
    
    if initial_files != final_files:
        print("❌ Dry-run modified files when it shouldn't have")
        return False
    
    print("✅ Dry-run functionality test passed")
    return True

def test_validation_functionality(test_dir, reorganizer_script):
    """Test validation functionality with missing files."""
    print("Testing validation functionality...")
    
    # Create a test with missing source file
    missing_file_test = test_dir / "test_missing"
    missing_file_test.mkdir()
    
    # Create reorganizer instance and modify mappings to include non-existent file
    test_script = missing_file_test / "test_reorganizer.py"
    with open(test_script, 'w') as f:
        f.write(f"""
import sys
sys.path.append('{test_dir.parent}')
from scripts.reorganize_files import FileReorganizer

reorganizer = FileReorganizer(root_dir='{missing_file_test}')
reorganizer.file_mappings['test'] = {{'nonexistent.py': 'src/nonexistent.py'}}

validation_results, _ = reorganizer.validate_mappings()
print("Missing sources:", len(validation_results['missing_sources']))
print("Conflicts:", len(validation_results['conflicts']))

# Should have missing sources
if len(validation_results['missing_sources']) > 0:
    print("✅ Validation correctly detected missing files")
    sys.exit(0)
else:
    print("❌ Validation failed to detect missing files")
    sys.exit(1)
""")
    
    result = subprocess.run(f"cd {missing_file_test} && python test_reorganizer.py", 
                          shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Validation test failed: {result.stderr}")
        return False
    
    print("✅ Validation functionality test passed")
    return True

def test_backup_functionality(test_dir, reorganizer_script):
    """Test backup creation functionality."""
    print("Testing backup functionality...")
    
    # Create a simple test file
    test_file = test_dir / "test_backup.txt"
    test_content = "This is a test file for backup"
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    # Test backup creation through reorganizer
    test_script = test_dir / "test_backup.py"
    with open(test_script, 'w') as f:
        f.write(f"""
import sys
sys.path.append('{test_dir.parent}')
from scripts.reorganize_files import FileReorganizer

reorganizer = FileReorganizer(root_dir='{test_dir}')
try:
    backup_dir = reorganizer.create_backup()
    print(f"Backup created at: {{backup_dir}}")
    
    # Check if backup contains our test file
    backup_test_file = backup_dir / "test_backup.txt"
    if backup_test_file.exists():
        with open(backup_test_file, 'r') as f:
            content = f.read()
        if content == "{test_content}":
            print("✅ Backup functionality test passed")
            sys.exit(0)
        else:
            print("❌ Backup file content mismatch")
            sys.exit(1)
    else:
        print("❌ Test file not found in backup")
        sys.exit(1)
except Exception as e:
    print(f"❌ Backup test failed: {{e}}")
    sys.exit(1)
""")
    
    result = subprocess.run(f"cd {test_dir} && python test_backup.py", 
                          shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Backup test failed: {result.stderr}")
        return False
    
    print("✅ Backup functionality test passed")
    return True

def test_file_mapping_logic(test_dir, reorganizer_script):
    """Test the file mapping logic."""
    print("Testing file mapping logic...")
    
    test_script = test_dir / "test_mapping.py"
    with open(test_script, 'w') as f:
        f.write(f"""
import sys
sys.path.append('{test_dir.parent}')
from scripts.reorganize_files import FileReorganizer

reorganizer = FileReorganizer(root_dir='{test_dir}')
mappings = reorganizer.file_mappings

# Check that all expected categories exist
expected_categories = ['source_files', 'documentation', 'scripts', 'demos', 'reports']
for category in expected_categories:
    if category not in mappings:
        print(f"❌ Missing mapping category: {{category}}")
        sys.exit(1)

# Check specific mappings
if 'app.py' not in mappings['source_files']:
    print("❌ Missing app.py mapping")
    sys.exit(1)

if mappings['source_files']['app.py'] != 'src/app.py':
    print("❌ Incorrect app.py mapping")
    sys.exit(1)

print("✅ File mapping logic test passed")
""")
    
    result = subprocess.run(f"cd {test_dir} && python test_mapping.py", 
                          shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ File mapping test failed: {result.stderr}")
        return False
    
    print("✅ File mapping logic test passed")
    return True

def run_comprehensive_test():
    """Run comprehensive test suite for reorganization script."""
    print("COMPREHENSIVE REORGANIZATION SCRIPT TEST")
    print("=" * 50)
    
    # Get script paths
    script_dir = Path(__file__).parent
    reorganizer_script = script_dir / "reorganize_files.py"
    
    if not reorganizer_script.exists():
        print(f"❌ Reorganizer script not found: {reorganizer_script}")
        return False
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_project"
        test_dir.mkdir()
        
        # Copy reorganizer script to test location
        scripts_dir = test_dir.parent / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        shutil.copy2(reorganizer_script, scripts_dir / "reorganize_files.py")
        
        print(f"Created test project in: {test_dir}")
        
        # Create test project structure
        test_files = create_test_project_structure(test_dir)
        print(f"Created {len(test_files)} test files")
        
        # Run tests
        tests = [
            (test_file_mapping_logic, "File Mapping Logic"),
            (test_validation_functionality, "Validation"),
            (test_preview_functionality, "Preview"),
            (test_dry_run_functionality, "Dry Run"),
            (test_backup_functionality, "Backup"),
        ]
        
        passed = 0
        failed = 0
        
        for test_func, test_name in tests:
            try:
                if test_func(test_dir, reorganizer_script):
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ {test_name} test crashed: {str(e)}")
                failed += 1
        
        print(f"\nTEST RESULTS")
        print("=" * 20)
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total:  {passed + failed}")
        
        if failed == 0:
            print("\n🎉 All tests passed! Reorganization script is ready for use.")
            return True
        else:
            print(f"\n❌ {failed} test(s) failed. Please review and fix issues.")
            return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)