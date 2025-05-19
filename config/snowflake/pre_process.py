#!/usr/bin/env python3

import os
import yaml
import sys
import copy

def load_yaml(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_yaml(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)

def merge_components(target, common):
    if "components" not in target:
        target["components"] = {}

    for section, items in common.get("components", {}).items():
        if section not in target["components"]:
            target["components"][section] = copy.deepcopy(items)
        else:
            for key, value in items.items():
                if key not in target["components"][section]:
                    target["components"][section][key] = copy.deepcopy(value)

def run(input_dir):
    common_path = os.path.join(input_dir, "common.yaml")
    if not os.path.isfile(common_path):
        print(f"❌ common.yaml not found in {input_dir}")
        sys.exit(1)

    common_spec = load_yaml(common_path)

    for filename in os.listdir(input_dir):
        if not filename.endswith((".yaml", ".yml")) or filename == "common.yaml":
            continue

        full_path = os.path.join(input_dir, filename)
        print(f"🔧 Merging components into: {filename}")
        spec = load_yaml(full_path)
        merge_components(spec, common_spec)
        write_yaml(full_path, spec)

    print("✅ Done.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: pre_process.py <input_dir>")
        sys.exit(1)

    run(sys.argv[1])
