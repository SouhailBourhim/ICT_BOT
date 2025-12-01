#!/usr/bin/env python3
"""
File Inventory Script
Documents the current project structure for reorganization planning.
"""

import os
import json
import datetime
from pathlib import Path
from collections import defaultdict

def get_file_info(filepath):
    """Get detailed information about a file."""
    try:
        stat = filepath.stat()
        return {
            "name": filepath.name,
            "path": str(filepath),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_executable": os.access(filepath, os.X_OK),
            "extension": filepath.suffix.lower(),
            "type": classify_file_type(filepath)
        }
    except Exception as e:
        return {
            "name": filepath.name,
            "path": str(filepath),
            "error": str(e)
        }

def classify_file_type(filepath):
    """Classify file based on extension and content."""
    ext = filepath.suffix.lower()
    name = filepath.name.lower()
    
    # Python files
    if ext == '.py':
        return 'python'
    
    # Documentation
    if ext in ['.md', '.rst', '.txt'] or 'readme' in name:
        return 'documentation'
    
    # Configuration
    if ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'] or name in ['dockerfile', '.gitignore', '.dockerignore']:
        return 'configuration'
    
    # Scripts
    if ext in ['.sh', '.bash', '.zsh'] or (filepath.is_file() and os.access(filepath, os.X_OK)):
        return 'script'
    
    # Data files
    if ext in ['.db', '.sqlite', '.sqlite3', '.csv', '.json']:
        return 'data'
    
    # Build/deployment
    if name in ['dockerfile', 'docker-compose.yml', 'requirements.txt', 'setup.py', 'pyproject.toml']:
        return 'build'
    
    # Test files
    if 'test' in name or ext == '.test':
        return 'test'
    
    # Other
    return 'other'

def analyze_directory_structure(root_dir="."):
    """Analyze and document the current directory structure."""
    root_path = Path(root_dir).resolve()
    
    inventory = {
        "timestamp": datetime.datetime.now().isoformat(),
        "root_directory": str(root_path),
        "summary": {
            "total_files": 0,
            "total_directories": 0,
            "file_types": defaultdict(int),
            "extensions": defaultdict(int),
            "size_by_type": defaultdict(int)
        },
        "directories": {},
        "files_by_type": defaultdict(list),
        "large_files": [],
        "executable_files": [],
        "potential_moves": {}
    }
    
    # Exclude patterns
    exclude_dirs = {'.git', '__pycache__', '.pytest_cache', '.venv', 'node_modules'}
    
    for root, dirs, files in os.walk(root_path):
        # Filter excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        rel_root = os.path.relpath(root, root_path)
        if rel_root == '.':
            rel_root = 'root'
        
        # Directory info
        dir_info = {
            "path": root,
            "relative_path": rel_root,
            "file_count": len(files),
            "subdirectory_count": len(dirs),
            "files": []
        }
        
        inventory["summary"]["total_directories"] += 1
        
        # Process files in this directory
        for file in files:
            filepath = Path(root) / file
            file_info = get_file_info(filepath)
            
            if "error" not in file_info:
                inventory["summary"]["total_files"] += 1
                
                # Update summaries
                file_type = file_info["type"]
                extension = file_info["extension"]
                size = file_info["size"]
                
                inventory["summary"]["file_types"][file_type] += 1
                inventory["summary"]["extensions"][extension] += 1
                inventory["summary"]["size_by_type"][file_type] += size
                
                # Categorize files
                inventory["files_by_type"][file_type].append(file_info)
                
                # Track large files (>1MB)
                if size > 1024 * 1024:
                    inventory["large_files"].append(file_info)
                
                # Track executable files
                if file_info["is_executable"]:
                    inventory["executable_files"].append(file_info)
            
            dir_info["files"].append(file_info)
        
        inventory["directories"][rel_root] = dir_info
    
    # Analyze potential reorganization moves
    inventory["potential_moves"] = suggest_reorganization_moves(inventory)
    
    return inventory

def suggest_reorganization_moves(inventory):
    """Suggest potential file moves based on current structure."""
    suggestions = {
        "source_code": [],
        "documentation": [],
        "scripts": [],
        "configuration": [],
        "tests": [],
        "data": [],
        "demos": []
    }
    
    for file_type, files in inventory["files_by_type"].items():
        for file_info in files:
            path = file_info["path"]
            name = file_info["name"]
            
            if file_type == "python":
                if name == "app.py":
                    suggestions["source_code"].append({
                        "current": path,
                        "suggested": "src/app.py",
                        "reason": "Main application entry point"
                    })
                elif "demo_" in name:
                    suggestions["demos"].append({
                        "current": path,
                        "suggested": f"demos/{name}",
                        "reason": "Demonstration script"
                    })
                elif "test_" in name or "/tests/" in path:
                    suggestions["tests"].append({
                        "current": path,
                        "suggested": f"tests/{name}",
                        "reason": "Test file"
                    })
                else:
                    # Determine if it's a core module
                    if any(module in path for module in ["core/", "managers/", "processors/", "retrievers/", "models/", "ui/", "utils/"]):
                        suggestions["source_code"].append({
                            "current": path,
                            "suggested": f"src/{os.path.relpath(path)}",
                            "reason": "Core application module"
                        })
            
            elif file_type == "documentation":
                if name.upper().startswith("README"):
                    suggestions["documentation"].append({
                        "current": path,
                        "suggested": "docs/README.md",
                        "reason": "Main project documentation"
                    })
                elif "DEPLOYMENT" in name.upper() or "DOCKER" in name.upper():
                    suggestions["documentation"].append({
                        "current": path,
                        "suggested": f"docs/deployment/{name.lower()}",
                        "reason": "Deployment documentation"
                    })
                else:
                    suggestions["documentation"].append({
                        "current": path,
                        "suggested": f"docs/{name}",
                        "reason": "General documentation"
                    })
            
            elif file_type == "script":
                if "docker" in name.lower():
                    suggestions["scripts"].append({
                        "current": path,
                        "suggested": f"scripts/docker/{name}",
                        "reason": "Docker-related script"
                    })
                else:
                    suggestions["scripts"].append({
                        "current": path,
                        "suggested": f"scripts/utilities/{name}",
                        "reason": "Utility script"
                    })
            
            elif file_type == "configuration":
                if "/config/" not in path:
                    suggestions["configuration"].append({
                        "current": path,
                        "suggested": f"config/{name}",
                        "reason": "Configuration file"
                    })
    
    return suggestions

def generate_inventory_report(inventory, output_file="file_inventory.json"):
    """Generate a comprehensive inventory report."""
    # Save detailed JSON report
    with open(output_file, 'w') as f:
        json.dump(inventory, f, indent=2, default=str)
    
    # Generate human-readable summary
    summary_file = output_file.replace('.json', '_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("PROJECT FILE INVENTORY SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Generated: {inventory['timestamp']}\n")
        f.write(f"Root Directory: {inventory['root_directory']}\n\n")
        
        # Summary statistics
        summary = inventory['summary']
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 20 + "\n")
        f.write(f"Total Files: {summary['total_files']}\n")
        f.write(f"Total Directories: {summary['total_directories']}\n\n")
        
        # File types
        f.write("FILES BY TYPE\n")
        f.write("-" * 15 + "\n")
        for file_type, count in sorted(summary['file_types'].items()):
            size_mb = summary['size_by_type'][file_type] / (1024 * 1024)
            f.write(f"{file_type:15}: {count:3d} files ({size_mb:.1f} MB)\n")
        f.write("\n")
        
        # Extensions
        f.write("FILE EXTENSIONS\n")
        f.write("-" * 15 + "\n")
        for ext, count in sorted(summary['extensions'].items(), key=lambda x: x[1], reverse=True):
            if ext:  # Skip empty extensions
                f.write(f"{ext:10}: {count:3d} files\n")
        f.write("\n")
        
        # Large files
        if inventory['large_files']:
            f.write("LARGE FILES (>1MB)\n")
            f.write("-" * 20 + "\n")
            for file_info in sorted(inventory['large_files'], key=lambda x: x['size'], reverse=True):
                size_mb = file_info['size'] / (1024 * 1024)
                f.write(f"{file_info['name']:30}: {size_mb:.1f} MB\n")
            f.write("\n")
        
        # Executable files
        if inventory['executable_files']:
            f.write("EXECUTABLE FILES\n")
            f.write("-" * 15 + "\n")
            for file_info in inventory['executable_files']:
                f.write(f"{file_info['path']}\n")
            f.write("\n")
    
    print(f"Inventory report saved to: {output_file}")
    print(f"Summary report saved to: {summary_file}")
    
    return output_file, summary_file

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate project file inventory")
    parser.add_argument("--root", default=".", help="Root directory to analyze")
    parser.add_argument("--output", default="file_inventory.json", help="Output file name")
    
    args = parser.parse_args()
    
    print("Analyzing project structure...")
    inventory = analyze_directory_structure(args.root)
    
    print("Generating reports...")
    json_file, summary_file = generate_inventory_report(inventory, args.output)
    
    print(f"\nAnalysis complete!")
    print(f"Found {inventory['summary']['total_files']} files in {inventory['summary']['total_directories']} directories")
    print(f"Detailed report: {json_file}")
    print(f"Summary report: {summary_file}")