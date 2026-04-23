import os
import re
import ast

services = ['media', 'messenger', 'email', 'admin']

for svc in services:
    main_path = f'services/{svc}/app/main.py'
    if not os.path.exists(main_path):
        continue
    
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # The previous faulty replace left `configure_logging(), ... )`
    # Let's fix that.
    content = re.sub(r'configure_logging\(\),\s+structlog\.dev.*?cache_logger_on_first_use=True,\n    \)', 'configure_logging()', content, flags=re.DOTALL)
    
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    try:
        ast.parse(content)
        print(f"Updated {main_path} successfully (AST OK)")
    except SyntaxError as e:
        print(f"SyntaxError in {main_path}: {e}")
