#!/usr/bin/env python3
"""
Import Dependency Analyzer
Maps current import relationships to help with reorganization.
"""

import os
import ast
import json
import datetime
from pathlib import Path
from collections import defaultdict, deque

class ImportAnalyzer:
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir).resolve()
        self.python_files = []
        self.imports = defaultdict(list)  # file -> list of imports
        self.dependencies = defaultdict(set)  # file -> set of files it depends on
        self.dependents = defaultdict(set)  # file -> set of files that depend on it
        self.external_imports = defaultdict(set)  # file -> external packages
        self.relative_imports = defaultdict(list)  # file -> relative imports
        
    def find_python_files(self):
        """Find all Python files in the project."""
        exclude_dirs = {'.git', '__pycache__', '.pytest_cache', '.venv', 'node_modules'}
        
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    rel_path = filepath.relative_to(self.root_dir)
                    self.python_files.append(str(rel_path))
    
    def parse_imports(self, filepath):
        """Parse imports from a Python file."""
        try:
            with open(self.root_dir / filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            'type': 'import',
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    level = node.level
                    
                    for alias in node.names:
                        imports.append({
                            'type': 'from_import',
                            'module': module,
                            'name': alias.name,
                            'alias': alias.asname,
                            'level': level,
                            'line': node.lineno
                        })
            
            return imports
            
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return []
    
    def resolve_import_path(self, import_info, current_file):
        """Resolve import to actual file path if it's a local import."""
        module = import_info['module']
        import_type = import_info['type']
        level = import_info.get('level', 0)
        
        # Handle relative imports
        if level > 0:
            current_dir = Path(current_file).parent
            target_dir = current_dir
            
            # Go up 'level' directories
            for _ in range(level - 1):
                target_dir = target_dir.parent
            
            if module:
                target_path = target_dir / module.replace('.', '/')
            else:
                target_path = target_dir
            
            # Check for __init__.py or .py file
            possible_files = [
                target_path / '__init__.py',
                target_path.with_suffix('.py')
            ]
            
            for possible_file in possible_files:
                if (self.root_dir / possible_file).exists():
                    return str(possible_file)
        
        # Handle absolute imports within the project
        else:
            # Check if it's a local module
            module_path = Path(module.replace('.', '/'))
            
            possible_files = [
                module_path / '__init__.py',
                module_path.with_suffix('.py')
            ]
            
            for possible_file in possible_files:
                if (self.root_dir / possible_file).exists():
                    return str(possible_file)
        
        return None  # External import
    
    def analyze_dependencies(self):
        """Analyze import dependencies between files."""
        self.find_python_files()
        
        # Parse imports for each file
        for filepath in self.python_files:
            imports = self.parse_imports(filepath)
            self.imports[filepath] = imports
            
            for import_info in imports:
                resolved_path = self.resolve_import_path(import_info, filepath)
                
                if resolved_path:
                    # Local dependency
                    self.dependencies[filepath].add(resolved_path)
                    self.dependents[resolved_path].add(filepath)
                else:
                    # External dependency
                    module = import_info['module']
                    if module:
                        # Extract top-level package name
                        top_level = module.split('.')[0]
                        self.external_imports[filepath].add(top_level)
                
                # Track relative imports separately
                if import_info.get('level', 0) > 0:
                    self.relative_imports[filepath].append(import_info)
    
    def find_circular_dependencies(self):
        """Find circular dependencies using DFS."""
        def has_cycle(node, visited, rec_stack, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        cycles = []
        visited = set()
        
        for file in self.python_files:
            if file not in visited:
                has_cycle(file, visited, set(), [])
        
        return cycles
    
    def get_dependency_graph(self):
        """Get the complete dependency graph."""
        return {
            'dependencies': dict(self.dependencies),
            'dependents': dict(self.dependents),
            'external_imports': dict(self.external_imports),
            'relative_imports': dict(self.relative_imports)
        }
    
    def analyze_impact_of_move(self, old_path, new_path):
        """Analyze the impact of moving a file to a new location."""
        impact = {
            'files_to_update': [],
            'import_changes': [],
            'potential_issues': []
        }
        
        # Files that import this file need to be updated
        for dependent in self.dependents.get(old_path, []):
            impact['files_to_update'].append(dependent)
            
            # Analyze what import statements need to change
            for import_info in self.imports.get(dependent, []):
                resolved = self.resolve_import_path(import_info, dependent)
                if resolved == old_path:
                    # This import needs to be updated
                    old_import = self.format_import_statement(import_info)
                    new_import = self.calculate_new_import(import_info, dependent, new_path)
                    
                    impact['import_changes'].append({
                        'file': dependent,
                        'line': import_info['line'],
                        'old_import': old_import,
                        'new_import': new_import
                    })
        
        # Check for potential issues
        if self.relative_imports.get(old_path):
            impact['potential_issues'].append(
                f"File {old_path} uses relative imports that may break when moved"
            )
        
        return impact
    
    def format_import_statement(self, import_info):
        """Format import info back to import statement."""
        if import_info['type'] == 'import':
            stmt = f"import {import_info['module']}"
            if import_info['alias']:
                stmt += f" as {import_info['alias']}"
        else:  # from_import
            level_prefix = '.' * import_info['level']
            module = import_info['module'] or ''
            stmt = f"from {level_prefix}{module} import {import_info['name']}"
            if import_info['alias']:
                stmt += f" as {import_info['alias']}"
        
        return stmt
    
    def calculate_new_import(self, import_info, importing_file, new_target_path):
        """Calculate what the new import statement should be."""
        # This is a simplified version - in practice, you'd need more sophisticated logic
        # to handle all cases of relative vs absolute imports
        
        importing_dir = Path(importing_file).parent
        target_path = Path(new_target_path)
        
        # Calculate relative path
        try:
            rel_path = os.path.relpath(target_path, importing_dir)
            # Convert to module notation
            module_path = str(Path(rel_path).with_suffix(''))
            module_name = module_path.replace(os.sep, '.')
            
            if import_info['type'] == 'import':
                return f"import {module_name}"
            else:
                return f"from {module_name} import {import_info['name']}"
        except:
            return f"# TODO: Update import for moved file {new_target_path}"
    
    def generate_report(self, output_file="import_analysis.json"):
        """Generate comprehensive import analysis report."""
        self.analyze_dependencies()
        
        # Find circular dependencies
        cycles = self.find_circular_dependencies()
        
        # Calculate statistics
        stats = {
            'total_files': len(self.python_files),
            'total_imports': sum(len(imports) for imports in self.imports.values()),
            'files_with_dependencies': len([f for f in self.dependencies if self.dependencies[f]]),
            'files_with_dependents': len([f for f in self.dependents if self.dependents[f]]),
            'circular_dependencies': len(cycles),
            'external_packages': len(set().union(*self.external_imports.values()))
        }
        
        # Most connected files
        most_dependencies = sorted(
            [(f, len(deps)) for f, deps in self.dependencies.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        most_dependents = sorted(
            [(f, len(deps)) for f, deps in self.dependents.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'root_directory': str(self.root_dir),
            'statistics': stats,
            'python_files': self.python_files,
            'imports': dict(self.imports),
            'dependencies': dict(self.dependencies),
            'dependents': dict(self.dependents),
            'external_imports': dict(self.external_imports),
            'relative_imports': dict(self.relative_imports),
            'circular_dependencies': cycles,
            'most_dependencies': most_dependencies,
            'most_dependents': most_dependents
        }
        
        # Save detailed report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate summary
        summary_file = output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("IMPORT DEPENDENCY ANALYSIS\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Generated: {report['timestamp']}\n")
            f.write(f"Root Directory: {report['root_directory']}\n\n")
            
            f.write("STATISTICS\n")
            f.write("-" * 15 + "\n")
            for key, value in stats.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            if cycles:
                f.write("CIRCULAR DEPENDENCIES\n")
                f.write("-" * 20 + "\n")
                for i, cycle in enumerate(cycles, 1):
                    f.write(f"Cycle {i}: {' -> '.join(cycle)}\n")
                f.write("\n")
            
            f.write("FILES WITH MOST DEPENDENCIES\n")
            f.write("-" * 30 + "\n")
            for file, count in most_dependencies:
                f.write(f"{file}: {count} dependencies\n")
            f.write("\n")
            
            f.write("FILES WITH MOST DEPENDENTS\n")
            f.write("-" * 28 + "\n")
            for file, count in most_dependents:
                f.write(f"{file}: {count} dependents\n")
            f.write("\n")
            
            # External packages
            all_external = set().union(*self.external_imports.values())
            if all_external:
                f.write("EXTERNAL PACKAGES\n")
                f.write("-" * 17 + "\n")
                for package in sorted(all_external):
                    f.write(f"{package}\n")
        
        print(f"Import analysis saved to: {output_file}")
        print(f"Summary saved to: {summary_file}")
        
        return report

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze Python import dependencies")
    parser.add_argument("--root", default=".", help="Root directory to analyze")
    parser.add_argument("--output", default="import_analysis.json", help="Output file name")
    parser.add_argument("--analyze-move", nargs=2, metavar=('OLD_PATH', 'NEW_PATH'),
                       help="Analyze impact of moving a file")
    
    args = parser.parse_args()
    
    analyzer = ImportAnalyzer(args.root)
    
    if args.analyze_move:
        old_path, new_path = args.analyze_move
        print(f"Analyzing impact of moving {old_path} to {new_path}...")
        
        analyzer.analyze_dependencies()
        impact = analyzer.analyze_impact_of_move(old_path, new_path)
        
        print(f"\nFiles that need updates: {len(impact['files_to_update'])}")
        for file in impact['files_to_update']:
            print(f"  - {file}")
        
        print(f"\nImport changes needed: {len(impact['import_changes'])}")
        for change in impact['import_changes']:
            print(f"  {change['file']}:{change['line']}")
            print(f"    Old: {change['old_import']}")
            print(f"    New: {change['new_import']}")
        
        if impact['potential_issues']:
            print(f"\nPotential issues:")
            for issue in impact['potential_issues']:
                print(f"  - {issue}")
    
    else:
        print("Analyzing import dependencies...")
        report = analyzer.generate_report(args.output)
        
        print(f"\nAnalysis complete!")
        print(f"Found {report['statistics']['total_files']} Python files")
        print(f"Total imports: {report['statistics']['total_imports']}")
        if report['circular_dependencies']:
            print(f"WARNING: Found {len(report['circular_dependencies'])} circular dependencies!")