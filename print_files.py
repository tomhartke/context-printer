
> ### `print_files.py`
```python
import os

# Specify the paths you want to include here
paths = [
    "scripts",
    # "state",
    # "docs",
]

# Only include files that have these extensions
allowed_extensions = {".py", ".js", ".json", ".yml", ".yaml", ".sh", ".md", ".html", ".css", ".txt"}

# Where to print the output
file_explanation_output_file = "files_explanation.txt"

# Directories to exclude from traversal
exclude_dirs = {".ipynb_checkpoints", "__pycache__"}

all_files = []

def guess_code_block_language(filename):
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext == '.py':
        return 'python'
    elif ext == '.js':
        return 'javascript'
    elif ext == '.json':
        return 'json'
    elif ext in ['.yml', '.yaml']:
        return 'yaml'
    elif ext == '.sh':
        return 'bash'
    elif ext == '.md':
        return 'md'
    elif ext == '.html':
        return 'html'
    elif ext == '.css':
        return 'css'
    else:
        return ''  # no specific language

def print_tree(root, prefix="", out=None):
    items = os.listdir(root)
    items.sort()
    for i, item in enumerate(items):
        # Skip excluded directories
        if item in exclude_dirs:
            continue

        path = os.path.join(root, item)
        connector = "└── " if i == len(items)-1 else "├── "

        if os.path.isdir(path):
            print(prefix + connector + item, file=out)
            new_prefix = prefix + ("    " if i == len(items)-1 else "│   ")
            print_tree(path, new_prefix, out=out)
        else:
            # Check allowed extension
            _, ext = os.path.splitext(item)
            ext = ext.lower()
            if ext in allowed_extensions:
                print(prefix + connector + item, file=out)
                all_files.append(path)

if __name__ == "__main__":
    with open(file_explanation_output_file, "w", encoding="utf-8") as out:
        # Print the directory structure for all specified paths
        for folder in paths:
            if os.path.isfile(folder):
                _, ext = os.path.splitext(folder)
                if ext.lower() in allowed_extensions:
                    print(folder, file=out)
                    all_files.append(folder)
                    print("", file=out)
            else:
                # A directory - print its structure
                print(folder + "/", file=out)
                print_tree(folder, out=out)
                print("", file=out)

        # Now print file contents separately
        print("========== FILE CONTENTS ==========\n", file=out)
        for fpath in all_files:
            lang = guess_code_block_language(fpath)
            # Ensure we can read the file
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception as e:
                content = f"Error reading file: {e}"

            print(f"FILE: {fpath}", file=out)
            print("```" + lang, file=out)
            print(content, file=out)
            print("```", file=out)
            print("", file=out)
