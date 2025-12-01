#!/usr/bin/env python3
"""
Project Backup Script
Creates a full backup of the project before reorganization.
"""

import os
import shutil
import datetime
import json
import hashlib
from pathlib import Path

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file for integrity verification."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        return f"ERROR: {str(e)}"

def create_backup(source_dir=".", backup_base_dir="backup"):
    """Create a timestamped backup of the entire project."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(backup_base_dir) / f"reorganization_backup_{timestamp}"
    
    print(f"Creating backup in: {backup_dir}")
    
    # Create backup directory
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Files to exclude from backup
    exclude_patterns = {
        '.git', '__pycache__', '.pytest_cache', '.venv', 
        'node_modules', '.DS_Store', '*.pyc', '*.pyo',
        'backup'  # Don't backup existing backups
    }
    
    backup_manifest = {
        "timestamp": timestamp,
        "source_directory": os.path.abspath(source_dir),
        "backup_directory": str(backup_dir),
        "files": [],
        "errors": []
    }
    
    # Copy files and create manifest
    for root, dirs, files in os.walk(source_dir):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_patterns]
        
        rel_root = os.path.relpath(root, source_dir)
        if rel_root == '.':
            rel_root = ''
            
        # Skip if this is a backup directory
        if 'backup' in Path(root).parts:
            continue
            
        for file in files:
            # Skip excluded file patterns
            if any(pattern in file for pattern in exclude_patterns if '*' not in pattern):
                continue
            if file.endswith(('.pyc', '.pyo')):
                continue
                
            source_path = Path(root) / file
            rel_path = Path(rel_root) / file if rel_root else Path(file)
            dest_path = backup_dir / rel_path
            
            try:
                # Create destination directory if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(source_path, dest_path)
                
                # Calculate hash for verification
                file_hash = calculate_file_hash(source_path)
                
                backup_manifest["files"].append({
                    "original_path": str(source_path),
                    "backup_path": str(dest_path),
                    "relative_path": str(rel_path),
                    "size": source_path.stat().st_size,
                    "hash": file_hash,
                    "modified_time": source_path.stat().st_mtime
                })
                
            except Exception as e:
                error_msg = f"Failed to backup {source_path}: {str(e)}"
                print(f"ERROR: {error_msg}")
                backup_manifest["errors"].append(error_msg)
    
    # Save backup manifest
    manifest_path = backup_dir / "backup_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(backup_manifest, f, indent=2)
    
    print(f"Backup completed successfully!")
    print(f"Files backed up: {len(backup_manifest['files'])}")
    print(f"Errors encountered: {len(backup_manifest['errors'])}")
    print(f"Backup location: {backup_dir}")
    print(f"Manifest saved to: {manifest_path}")
    
    return backup_dir, backup_manifest

def verify_backup(backup_manifest_path):
    """Verify backup integrity by checking file hashes."""
    with open(backup_manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print("Verifying backup integrity...")
    verified = 0
    failed = 0
    
    for file_info in manifest["files"]:
        backup_path = file_info["backup_path"]
        expected_hash = file_info["hash"]
        
        if os.path.exists(backup_path):
            actual_hash = calculate_file_hash(backup_path)
            if actual_hash == expected_hash:
                verified += 1
            else:
                print(f"HASH MISMATCH: {backup_path}")
                failed += 1
        else:
            print(f"MISSING FILE: {backup_path}")
            failed += 1
    
    print(f"Verification complete: {verified} verified, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create project backup before reorganization")
    parser.add_argument("--source", default=".", help="Source directory to backup")
    parser.add_argument("--backup-dir", default="backup", help="Backup base directory")
    parser.add_argument("--verify", help="Verify existing backup using manifest file")
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_backup(args.verify)
        exit(0 if success else 1)
    else:
        backup_dir, manifest = create_backup(args.source, args.backup_dir)
        print(f"\nTo verify this backup later, run:")
        print(f"python {__file__} --verify {backup_dir}/backup_manifest.json")