import os

services_dir = 'providers/src/snowflake/v00.00.00000/services'

for filename in os.listdir(services_dir):
    if not filename.endswith('.yaml'):
        continue

    file_path = os.path.join(services_dir, filename)

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []

    for line in lines:
        if './common.yaml' in line:
            line = line.replace("./common.yaml", "'").replace("\n", "'\n")
        elif 'common.yaml' in line:   
            line = line.replace("common.yaml", "'").replace("\n", "'\n")
        new_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ Cleaned: {filename}")
