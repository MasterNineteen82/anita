import os
import json
import argparse
from datetime import datetime

def find_python_files(base_dir, output_file=None):
    """Find all Python files in the directory and its subdirectories."""
    python_files = []
    file_count = 0
    
    print(f"Searching for Python files in: {base_dir}")
    
    # Result structure for JSON output
    results = {
        "scan_date": datetime.now().isoformat(),
        "base_directory": base_dir,
        "total_files_scanned": 0,
        "python_files_found": 0,
        "directories": {}
    }
    
    for root, dirs, files in os.walk(base_dir):
        file_count += 1
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                python_files.append(full_path)
                
                # Add to results structure
                dir_name = os.path.dirname(full_path)
                if dir_name not in results["directories"]:
                    results["directories"][dir_name] = []
                
                # Get file size and last modified time
                file_stats = os.stat(full_path)
                file_info = {
                    "name": file,
                    "path": full_path,
                    "size_bytes": file_stats.st_size,
                    "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                }
                
                results["directories"][dir_name].append(file_info)
    
    # Update summary info
    results["total_files_scanned"] = file_count
    results["python_files_found"] = len(python_files)
    
    # Print summary
    print(f"\nFound {len(python_files)} Python files out of {file_count} total files.")
    
    if python_files:
        print("\nPython files by directory:")
        # Print directory summary
        for dir_name, files in results["directories"].items():
            print(f"\n{dir_name} ({len(files)} files):")
            for file_info in files:
                print(f"  - {file_info['name']} ({file_info['size_bytes']} bytes)")
    
    # Save to JSON file if specified
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find Python files in the project")
    parser.add_argument("--base-dir", default="k:\\anita\\poc", help="Base directory to search")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    
    args = parser.parse_args()
    find_python_files(args.base_dir, args.output)