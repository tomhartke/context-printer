#!/usr/bin/env python3
import os
import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

###############################################################################
# 1) CONFIG
###############################################################################
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".json", ".yml", ".yaml", ".sh",
    ".md", ".html", ".css", ".txt"
}
EXCLUDE_DIRS = {".git", ".ipynb_checkpoints", "__pycache__", "venv", ".ropeproject"}

###############################################################################
# 2) BUILD TREE
###############################################################################
def build_tree(root_path):
    tree = []
    try:
        for entry in sorted(os.listdir(root_path)):
            if entry in EXCLUDE_DIRS:
                continue

            full_path = os.path.join(root_path, entry)
            if os.path.isdir(full_path):
                tree.append({
                    "name": entry + "/",
                    "path": full_path,
                    "type": "dir",
                    "children": build_tree(full_path)
                })
            else:
                _, ext = os.path.splitext(entry)
                if ext.lower() in ALLOWED_EXTENSIONS:
                    tree.append({
                        "name": entry,
                        "path": full_path,
                        "type": "file",
                        "children": []
                    })
    except PermissionError:
        pass
    return tree

###############################################################################
# 3) FLASK ROUTES
###############################################################################
@app.route("/")
def index():
    # We'll pass the current working directory into the HTML as defaultRoot
    default_root = os.getcwd()

    html_page = """
<!DOCTYPE html>
<html>
<head>
    <title>Local Folder Picker</title>
    <style>
        body {
          font-family: sans-serif;
          margin: 20px;
        }
        .indent {
          margin-left: 20px;
        }
        .partial {
          opacity: 0.6;
        }
        ul {
          list-style-type: none;
          padding-left: 1em;
        }
        li {
          margin: 4px 0;
        }
        .folder > label::before {
          content: "📁 ";
        }
        .file > label::before {
          content: "📄 ";
        }
        button {
          margin-top: 20px;
          font-size: 1em;
          padding: 8px;
        }
    </style>
</head>
<body>
    <h1>Local Folder Picker (Partial Selection)</h1>

    <p>Enter a directory path and click "Load Tree":</p>
    <input id="rootDirInput" type="text" style="width: 400px;"
           value="{{ defaultRoot|e }}" />
    <button onclick="loadTree()">Load Tree</button>

    <div id="treeContainer" style="margin-top:20px;"></div>

    <button onclick="submitSelection()">Submit Selection</button>

    <script>
    let treeData = [];
    let rootDir = "";

    async function loadTree() {
      rootDir = document.getElementById("rootDirInput").value.trim();
      if(!rootDir) {
        alert("Enter a directory path first.");
        return;
      }
      try {
        const resp = await fetch("/api/tree?root=" + encodeURIComponent(rootDir));
        if(!resp.ok) throw new Error(resp.statusText);
        treeData = await resp.json();
        const container = document.getElementById("treeContainer");
        container.innerHTML = "";
        const ul = buildUL(treeData);
        container.appendChild(ul);
      } catch(err) {
        alert("Error loading tree: " + err);
      }
    }

    function buildUL(nodes) {
      const ul = document.createElement("ul");
      for(const node of nodes) {
        const li = document.createElement("li");
        li.classList.add(node.type === "dir" ? "folder" : "file");
        const label = document.createElement("label");

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.dataset.path = node.path;
        checkbox.addEventListener("change", (e) => onCheckboxChange(e, node));

        label.appendChild(checkbox);
        label.append(" " + node.name);
        li.appendChild(label);

        if(node.type === "dir" && node.children && node.children.length) {
          const childUL = buildUL(node.children);
          childUL.classList.add("indent");
          li.appendChild(childUL);
        }
        ul.appendChild(li);
      }
      return ul;
    }

    function onCheckboxChange(ev, node) {
      const checked = ev.target.checked;
      // We'll simply do "selectChildren" + "bubble up partial"
      selectChildren(node, checked);
      updateParentsPartial(node);
    }

    function selectChildren(node, checked) {
      if(node.children && node.children.length) {
        for(const child of node.children) {
          const childBox = document.querySelector('input[data-path="' + cssEscape(child.path) + '"]');
          if(childBox) {
            childBox.checked = checked;
          }
          selectChildren(child, checked);
        }
      }
    }

    function updateParentsPartial(node) {
      const parentPath = getParentPath(node.path);
      if(!parentPath) return;

      const parentNode = findNodeByPath(parentPath, treeData);
      if(!parentNode) return;

      const {allChecked, noneChecked} = checkChildrenState(parentNode);
      const parentCheckbox = document.querySelector('input[data-path="' + cssEscape(parentNode.path) + '"]');
      if(parentCheckbox) {
        if(allChecked) {
          parentCheckbox.checked = true;
          parentCheckbox.indeterminate = false;
        } else if(noneChecked) {
          parentCheckbox.checked = false;
          parentCheckbox.indeterminate = false;
        } else {
          parentCheckbox.checked = false;
          parentCheckbox.indeterminate = true;
        }
      }
      updateParentsPartial(parentNode);
    }

    function checkChildrenState(dirNode) {
      if(!dirNode.children || dirNode.children.length === 0) {
        const box = document.querySelector('input[data-path="' + cssEscape(dirNode.path) + '"]');
        const c = box ? box.checked : false;
        return {allChecked: c, noneChecked: !c};
      }
      let total = dirNode.children.length;
      let checkedCount = 0;
      for(const child of dirNode.children) {
        const box = document.querySelector('input[data-path="' + cssEscape(child.path) + '"]');
        if(box && box.checked) {
          checkedCount++;
        }
      }
      const allChecked = (checkedCount === total);
      const noneChecked = (checkedCount === 0);
      return {allChecked, noneChecked};
    }

    function getParentPath(pathStr) {
      const idx = pathStr.lastIndexOf("/");
      if(idx <= 0) return null;
      return pathStr.substring(0, idx);
    }

    function findNodeByPath(pathStr, nodeList) {
      for(const n of nodeList) {
        if(n.path === pathStr) return n;
        if(n.children) {
          const found = findNodeByPath(pathStr, n.children);
          if(found) return found;
        }
      }
      return null;
    }

    function cssEscape(str) {
      return str.replace(/"/g, '\\"').replace(/'/g, "\\'");
    }

    async function submitSelection() {
      let allChecks = document.querySelectorAll('input[type="checkbox"]:checked');
      let paths = [];
      for(const c of allChecks) {
        paths.push(c.dataset.path);
      }
      console.log("Selected:", paths);

      try {
        let resp = await fetch("/api/submit", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({root: rootDir, selected: paths})
        });
        if(!resp.ok) throw new Error(resp.statusText);
        let text = await resp.text();
        alert("Server responded: " + text);
      } catch(err) {
        alert("Submit error: " + err);
      }
    }
    </script>
</body>
</html>
    """
    return render_template_string(html_page, defaultRoot=default_root)

@app.route("/api/tree")
def api_tree():
    root = request.args.get("root", ".")
    if not os.path.isdir(root):
        return jsonify({"error": "Invalid directory"}), 400
    tree = build_tree(root)
    return jsonify(tree)

@app.route("/api/submit", methods=["POST"])
def api_submit():
    data = request.json
    selected = data.get("selected", [])
    root = data.get("root", "")
    print(f"User selected {len(selected)} items under root {root}")
    for s in selected:
        print(" =>", s)
    return "OK from server"

if __name__ == "__main__":
    app.run(debug=True)
