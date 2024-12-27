# context-printer
Select and print contents of files from a repository or folder

This small utility script lets you easily gather and print the contents of selected folders/files in a repository into one big text file (`files_explanation.txt`). You can then paste that text into ChatGPT (or other LLM interfaces) to give it a full context of your codebase.

## Getting Started

1. **Clone or Download** this repository onto your local machine.

2. **Specify which paths** you want to include in `print_files.py` by editing the `paths` list:
   ```python
   paths = [
       "scripts",
       # "state",
       # "docs",
   ]

3. **Run the script** in your terminal:
   ```bash
   python print_files.py
   ```
   This will generate a file called `files_explanation.txt` with:
   - A tree-structure outline of the included directories/files
   - The contents of each file (for allowed extensions)

4. **Copy the contents** of `files_explanation.txt` into ChatGPT (or another LLM), and you’ll have a complete textual snapshot of your codebase for easier reference or sharing.
