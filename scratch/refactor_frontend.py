import os
import glob

views_dir = "/Users/chaitanyanagane/Documents/resume_screening/frontend/src/views"
tsx_files = glob.glob(os.path.join(views_dir, "*.tsx"))

for file in tsx_files:
    with open(file, "r") as f:
        content = f.read()
        
    if "const API_BASE = " not in content:
        # Add API_BASE at the top below imports
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('//'):
                insert_idx = i + 1
            elif line.strip() == '':
                continue
            else:
                break
        
        lines.insert(insert_idx, '\nconst API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";\n')
        content = '\n'.join(lines)
    
    # Replace "http://localhost:8000/api/..." with `${API_BASE}/api/...`
    import re
    content = re.sub(r'"http://localhost:8000(/api/[^"]+)"', r'`${API_BASE}\1`', content)
    # Replace `http://localhost:8000/api/...` with `${API_BASE}/api/...`
    content = re.sub(r'`http://localhost:8000(/api/[^`]+)`', r'`${API_BASE}\1`', content)
    
    with open(file, "w") as f:
        f.write(content)

print("Updated hardcoded URLs.")
