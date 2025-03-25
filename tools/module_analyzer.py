import os
import ast
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dry_run import DryRunLogger

class ModuleAnalyzer:
    """Analyzes Python modules to determine their purpose and dependencies."""
    
    def __init__(self, source_dir: str, logger: DryRunLogger = None):
        self.source_dir = source_dir
        self.logger = logger or DryRunLogger(verbose=True)
        self.results = {
            "modules": {},
            "summary": {
                "api_endpoints": 0,
                "websocket_handlers": 0,
                "services": 0,
                "models": 0,
                "repositories": 0,
                "utilities": 0,
                "unknown": 0
            }
        }
        
        # Define patterns to recognize module types
        self.patterns = {
            "api_endpoints": ["router", "fastapi", "api", "endpoint", "@app", "@router"],
            "websocket_handlers": ["websocket", "websockets", "ws", "connect", "disconnect"],
            "services": ["service", "manager", "handler", "processor"],
            "models": ["model", "schema", "dataclass", "BaseModel", "pydantic"],
            "repositories": ["repository", "dao", "database", "db", "query", "sql"],
            "utilities": ["util", "helper", "common", "tools"]
        }
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        try:
            # Parse the file into an AST
            tree = ast.parse(content)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")
            
            # Extract classes
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "methods": [],
                        "attributes": [],
                        "is_dataclass": False,
                        "is_pydantic": False
                    }
                    
                    # Check for class decorators (e.g., @dataclass)
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                            class_info["is_dataclass"] = True
                    
                    # Check if it inherits from BaseModel (pydantic)
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "BaseModel":
                            class_info["is_pydantic"] = True
                    
                    # Extract methods
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            class_info["methods"].append(child.name)
                        elif isinstance(child, ast.Assign):
                            # Crude attribute extraction
                            for target in child.targets:
                                if isinstance(target, ast.Name):
                                    class_info["attributes"].append(target.id)
                    
                    classes.append(class_info)
            
            # Extract functions
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not isinstance(node.parent, ast.ClassDef):
                    function_info = {
                        "name": node.name,
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                    }
                    functions.append(function_info)
            
            return {
                "imports": imports,
                "classes": classes,
                "functions": functions,
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
        
        except SyntaxError as e:
            return {
                "error": f"Syntax error in file: {str(e)}",
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
        except Exception as e:
            return {
                "error": f"Error analyzing file: {str(e)}",
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
    
    def determine_module_type(self, analysis: Dict[str, Any], file_path: str) -> str:
        """Determine the type of a module based on its content."""
        if "error" in analysis:
            return "unknown"
        
        # Check file and directory names first
        filename = os.path.basename(file_path).lower()
        dirname = os.path.basename(os.path.dirname(file_path)).lower()
        
        # Convert analysis to lowercase strings for pattern matching
        content_str = analysis["content_preview"].lower()
        imports_str = " ".join(analysis["imports"]).lower()
        classes_str = " ".join([c["name"].lower() for c in analysis["classes"]])
        
        # Check for dataclasses or pydantic models
        has_data_models = any(c["is_dataclass"] or c["is_pydantic"] for c in analysis["classes"])
        if has_data_models:
            return "models"
        
        # Score each category
        scores = {}
        for category, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.lower() in filename or pattern.lower() in dirname:
                    score += 5
                if pattern.lower() in content_str:
                    score += 2
                if pattern.lower() in imports_str:
                    score += 1
                if pattern.lower() in classes_str:
                    score += 3
            scores[category] = score
        
        # Return the category with the highest score
        if any(score > 0 for score in scores.values()):
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return "unknown"
    
    def determine_target_path(self, module_type: str, file_path: str) -> str:
        """Determine the target path for a module in the new structure."""
        filename = os.path.basename(file_path)
        
        # Map module types to target directories
        mapping = {
            "api_endpoints": "api/endpoints",
            "websocket_handlers": "api/websockets",
            "services": "domain/services",
            "models": "domain/models",
            "repositories": "infrastructure/repositories",
            "utilities": "utils"
        }
        
        target_dir = mapping.get(module_type, "utils")  # Default to utils for unknown
        return os.path.join("backend", target_dir, filename)
    
    def analyze_directory(self) -> Dict[str, Any]:
        """Analyze all Python files in the directory."""
        count = 0
        
        for root, _, files in os.walk(self.source_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Skip __init__.py files for analysis
                    if file == "__init__.py":
                        continue
                    
                    analysis = self.analyze_file(file_path)
                    self.logger.would_analyze(file_path, analysis)
                    
                    module_type = self.determine_module_type(analysis, file_path)
                    target_path = self.determine_target_path(module_type, file_path)
                    
                    # Log what would happen
                    self.logger.would_move_file(file_path, target_path)
                    
                    # Record in results
                    self.results["modules"][file_path] = {
                        "analysis": analysis,
                        "module_type": module_type,
                        "target_path": target_path
                    }
                    
                    self.results["summary"][module_type] += 1
                    count += 1
        
        print(f"Analyzed {count} Python files in {self.source_dir}")
        return self.results
    
    def save_results(self, output_file: str = None):
        """Save the analysis results to a file."""
        if not output_file:
            output_file = f"module_analysis_{os.path.basename(self.source_dir)}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Analysis results saved to {output_file}")
        print("\nSummary:")
        for category, count in self.results["summary"].items():
            print(f"  {category}: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Python modules to plan migration")
    parser.add_argument("source_dir", help="Directory containing Python modules to analyze")
    parser.add_argument("--output", "-o", help="Output file for analysis results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    logger = DryRunLogger(verbose=args.verbose)
    analyzer = ModuleAnalyzer(args.source_dir, logger)
    analyzer.analyze_directory()
    analyzer.save_results(args.output)