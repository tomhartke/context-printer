import streamlit as st
import os
import pyperclip

###############################################################################
# 1) CONFIG / GLOBALS
###############################################################################

# Adjust these to your preferences:
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".json", ".yml", ".yaml", ".sh",
    ".md", ".html", ".css", ".txt"
}
EXCLUDE_DIRS = {
    ".git", ".ipynb_checkpoints", "__pycache__",
    "venv", ".ropeproject"
}

# A global map from absolute path -> node
ABS_PATH_TO_NODE = {}

###############################################################################
# 2) DIRECTORY STRUCTURE BUILDING
###############################################################################

def get_directory_structure(root_path, base_path=None):
    """
    Recursively build a tree of dictionaries for directories/files under 'root_path'.
    Each node has:
      - name (str)
      - abs_path (str) : absolute path
      - rel_path (str) : path relative to the original root
      - type: 'dir' or 'file'
      - parent_abs_path (str)
      - children: list of child nodes
    """
    if base_path is None:
        base_path = root_path

    tree = []
    try:
        entries = sorted(os.listdir(root_path))
        for entry in entries:
            if entry in EXCLUDE_DIRS:
                continue

            abs_path = os.path.join(root_path, entry)
            rel_path = os.path.relpath(abs_path, base_path)

            if os.path.isdir(abs_path):
                children = get_directory_structure(abs_path, base_path=base_path)
                tree.append({
                    "name": entry,
                    "abs_path": abs_path,
                    "rel_path": rel_path,
                    "type": "dir",
                    "parent_abs_path": root_path,
                    "children": children
                })
            else:
                _, ext = os.path.splitext(entry)
                if ext.lower() in ALLOWED_EXTENSIONS:
                    tree.append({
                        "name": entry,
                        "abs_path": abs_path,
                        "rel_path": rel_path,
                        "type": "file",
                        "parent_abs_path": root_path,
                        "children": []
                    })
    except PermissionError:
        pass

    return tree


def index_tree_nodes(nodes):
    """
    Populate the global dictionary ABS_PATH_TO_NODE,
    so we can quickly look up any node to find its parent, etc.
    """
    for node in nodes:
        ABS_PATH_TO_NODE[node["abs_path"]] = node
        if node["type"] == "dir":
            index_tree_nodes(node["children"])


###############################################################################
# 3) SELECTION LOGIC
###############################################################################

def propagate_selection_down(node, value):
    """
    Selecting (or unselecting) a folder also selects/unselects *all its children*.
    """
    for child in node["children"]:
        child_sel_key = f"selected_{child['abs_path']}"
        st.session_state[child_sel_key] = value

        if child["type"] == "dir":
            # Recurse
            propagate_selection_down(child, value)


def propagate_selection_up(abs_path):
    """
    If a file is checked => mark its parent directory as checked,
    and continue upward until the root is reached.
    (Unchecking a file does *not* uncheck the parent, to avoid messing up siblings.)
    """
    if abs_path not in ABS_PATH_TO_NODE:
        return

    node = ABS_PATH_TO_NODE[abs_path]
    parent_path = node.get("parent_abs_path")
    if not parent_path or parent_path == abs_path:
        # Reached the top or no parent
        return

    parent_sel_key = f"selected_{parent_path}"
    st.session_state[parent_sel_key] = True

    propagate_selection_up(parent_path)


###############################################################################
# 4) TREE RENDERING
###############################################################################

def render_tree_nodes(nodes, prefix=""):
    """
    Render an ASCII-style tree in the Streamlit UI.
    - prefix: leading spaces/lines (e.g. '│   ') to show hierarchy
    """
    for i, node in enumerate(nodes):
        is_last = (i == len(nodes) - 1)
        branch = "└── " if is_last else "├── "
        # For children, use either "    " or "│   "
        child_prefix = prefix + ("    " if is_last else "│   ")

        expanded_key = f"expanded_{node['abs_path']}"
        selected_key = f"selected_{node['abs_path']}"

        # Ensure keys exist in st.session_state
        if expanded_key not in st.session_state:
            st.session_state[expanded_key] = False
        if selected_key not in st.session_state:
            st.session_state[selected_key] = False

        # UI layout for each line
        col_arrow, col_label = st.columns([0.07, 0.93])

        with col_arrow:
            # Show an arrow button for directories
            if node["type"] == "dir":
                arrow_symbol = "▼" if st.session_state[expanded_key] else "►"
                if st.button(arrow_symbol, key=f"arrow_btn_{node['abs_path']}",
                             help="Expand/Collapse folder"):
                    st.session_state[expanded_key] = not st.session_state[expanded_key]
            else:
                st.write("")  # no arrow for files

        with col_label:
            old_val = st.session_state[selected_key]
            label_text = prefix + branch + node["name"]
            new_val = st.checkbox(label_text, key=selected_key)

            # If user just toggled this directory => propagate to children
            if node["type"] == "dir" and new_val != old_val:
                propagate_selection_down(node, new_val)

            # If user *just checked* a file => propagate upward to parents
            if node["type"] == "file" and (not old_val) and new_val:
                propagate_selection_up(node["abs_path"])

            # If it's a file and is selected => show a comment box
            if node["type"] == "file" and new_val:
                comment_key = f"comment_{node['abs_path']}"
                st.text_input("Comment:", key=comment_key, placeholder="(Optional comment...)")

        # If directory is expanded, render children
        if node["type"] == "dir" and st.session_state[expanded_key]:
            render_tree_nodes(node["children"], prefix=child_prefix)


###############################################################################
# 5) BUILDING THE FINAL TEXT
###############################################################################

def build_selected_tree_text(nodes, prefix=""):
    """
    Create an ASCII tree of only the selected items (folders or files).
    """
    lines = []
    for i, node in enumerate(nodes):
        is_last = (i == len(nodes) - 1)
        branch = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        selected_key = f"selected_{node['abs_path']}"
        is_selected = st.session_state.get(selected_key, False)

        if node["type"] == "dir":
            # Look at children
            subtree = build_selected_tree_text(node["children"], child_prefix)
            # If directory or any child is selected => show it
            if is_selected or subtree.strip():
                lines.append(prefix + branch + node["name"] + "/")
            if subtree.strip():
                lines.append(subtree)
        else:
            if is_selected:
                lines.append(prefix + branch + node["name"])

    return "\n".join(lines)


def assemble_file_contents(nodes):
    """
    Gather file contents for each selected file.
    Skip printing 'COMMENT:' if it's empty.
    """
    output_list = []
    for node in nodes:
        sel_key = f"selected_{node['abs_path']}"
        if node["type"] == "dir":
            # Recurse
            child_text = assemble_file_contents(node["children"])
            if child_text.strip():
                output_list.append(child_text)
        else:
            if st.session_state.get(sel_key, False):
                comment_key = f"comment_{node['abs_path']}"
                comment = st.session_state.get(comment_key, "").strip()

                try:
                    with open(node["abs_path"], "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception as e:
                    content = f"Error reading file: {e}"

                lines = []
                lines.append(f"FILE: {node['rel_path']}")
                if comment:
                    lines.append(f"COMMENT: {comment}")
                lines.append("```")
                lines.append(content)
                lines.append("```")
                output_list.append("\n".join(lines) + "\n")

    return "\n".join(output_list)


def assemble_final_text(tree):
    """
    1) ASCII Tree of selected items
    2) Then file contents
    """
    tree_part = build_selected_tree_text(tree)
    files_part = assemble_file_contents(tree)

    out = []
    out.append("=== SELECTED FILES TREE ===")
    out.append(tree_part if tree_part.strip() else "(No items selected)")
    out.append("")
    out.append("=== FILE CONTENTS ===\n")
    out.append(files_part if files_part.strip() else "(No file contents)")

    return "\n".join(out)


###############################################################################
# 6) STREAMLIT APP
###############################################################################

def main():
    st.set_page_config(page_title="Context Manager", layout="wide")
    st.title("Nested Directory Tree – with Folder Auto-Select + Persistent Comments")

    root_dir = st.text_input("Root directory to scan:", value=os.getcwd())

    # NOTE: We do NOT automatically clear session state here.
    #       That way, if you scan the same directory again, you'll keep your comments.
    #       If you truly want to reset everything, you could add a separate 'Reset' button.

    if st.button("Scan Directory"):
        if not os.path.isdir(root_dir):
            st.error("Invalid directory path")
            return

        # We only rebuild the tree if we have a valid directory
        # ...but we do NOT wipe out the old session keys (comments, selections)
        # in case they're relevant for the same root directory.

        # Clear global map and rebuild it
        ABS_PATH_TO_NODE.clear()
        new_tree = get_directory_structure(root_dir)
        st.session_state["directory_tree"] = new_tree
        index_tree_nodes(new_tree)
        st.success("Directory scanned! (Previous comments/selections preserved if same path)")

    # Render the tree if it exists
    if "directory_tree" in st.session_state:
        render_tree_nodes(st.session_state["directory_tree"], prefix="")

        if st.button("Generate & Copy Context"):
            final_text = assemble_final_text(st.session_state["directory_tree"])
            if final_text.strip():
                try:
                    pyperclip.copy(final_text)
                    st.success("Context generated and copied to clipboard!")
                except Exception as e:
                    st.error(f"Could not copy to clipboard: {e}")

                st.subheader("Context Preview")
                st.text_area("Final Context", value=final_text, height=400)
            else:
                st.warning("No files selected or empty context.")


if __name__ == "__main__":
    main()
