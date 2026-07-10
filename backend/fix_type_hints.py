#!/usr/bin/env python3
"""Fix Python 3.8 type hint compatibility."""
import re
from pathlib import Path

def fix_file(filepath):
    """Fix type hints in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Check if already has the imports
    has_typing_imports = 'from typing import' in content and ('Optional' in content or 'List' in content)
    
    # Replace type hints
    replacements = [
        (r'\bstr \| None\b', 'Optional[str]'),
        (r'\bint \| None\b', 'Optional[int]'),
        (r'\bfloat \| None\b', 'Optional[float]'),
        (r'\bbool \| None\b', 'Optional[bool]'),
        (r'\bdict\[', 'Dict['),
        (r'\blist\[', 'List['),
        (r'\btuple\[', 'Tuple['),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Add imports if needed
    if content != original:
        # Check what types are used
        needs_optional = 'Optional[' in content
        needs_list = 'List[' in content
        needs_dict = 'Dict[' in content
        needs_tuple = 'Tuple[' in content
        
        if not has_typing_imports:
            # Add typing imports after other imports
            import_line = 'from typing import '
            imports = []
            if needs_optional:
                imports.append('Optional')
            if needs_list:
                imports.append('List')
            if needs_dict:
                imports.append('Dict')
            if needs_tuple:
                imports.append('Tuple')
            
            if imports:
                import_line += ', '.join(imports) + '\n\n'
                # Insert after existing imports
                lines = content.split('\n')
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith('from ') or line.startswith('import '):
                        insert_pos = i + 1
                    elif insert_pos > 0 and line.strip() and not line.startswith('#'):
                        break
                
                lines.insert(insert_pos, import_line.rstrip())
                content = '\n'.join(lines)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Find all Python files
backend_dir = Path(__file__).parent / 'app'
fixed_count = 0

for py_file in backend_dir.rglob('*.py'):
    if fix_file(py_file):
        print(f"Fixed: {py_file}")
        fixed_count += 1

print(f"\nTotal files fixed: {fixed_count}")
