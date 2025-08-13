import os
import json
import re
import string

input_path = "" # Your dataset path here
output_dir = "" # Your output directory here
code_field = ""  # Field containing the Java code you want to analyze in the JSONL file


def extract_top_level_type_name(code_str):
    match = re.search(r'public\s+(class|interface|enum)\s+(\w+)', code_str)
    return match.group(2) if match else None

def extract_and_clean_package(code_str):
    match = re.search(r'^\s*package\s+[^\n;]+;', code_str, flags=re.MULTILINE)
    package_stmt = match.group(0) if match else ""
    cleaned_code = re.sub(r'^\s*package\s+[^\n;]+;\n?', '', code_str, flags=re.MULTILINE)
    return package_stmt.strip(), cleaned_code.strip()

def extract_and_clean_imports(code_str):
    imports = re.findall(r'^\s*import\s+[^\n;]+;', code_str, flags=re.MULTILINE)
    cleaned_code = re.sub(r'^\s*import\s+[^\n;]+;\n?', '', code_str, flags=re.MULTILINE)
    return '\n'.join(imports), cleaned_code.strip()

def wrap_code_in_temp_class(code_str, class_name):
    indented = '\n'.join('    ' + line for line in code_str.splitlines())
    return f"public class {class_name} {{\n{indented}\n}}"

def sanitize_filename(name):
    allowed = set(string.ascii_letters + string.digits + "_")
    return ''.join(c if c in allowed else "_" for c in name)

def rename_class_everywhere(code_str, old_name, new_name):
    # Rename class declaration
    code_str = re.sub(
        rf'\bpublic\s+(class|interface|enum)\s+{old_name}\b',
        rf'public \1 {new_name}',
        code_str,
        count=1
    )
    # Rename constructor
    code_str = re.sub(rf'\b{old_name}\s*\(', f'{new_name}(', code_str)

    # Rename usages (instantiations, static, cast, vars)
    usage_patterns = [
        rf'\bnew\s+{old_name}\b',
        rf'\b{old_name}\s*\.',
        rf'\({old_name}\)',
        rf'\b{old_name}\s+\w',
    ]
    for pattern in usage_patterns:
        code_str = re.sub(pattern, lambda m: m.group(0).replace(old_name, new_name), code_str)

    return code_str

def has_orphan_methods(code_str):
    method_pattern = re.compile(
        r'^\s*(public|protected|private)?\s+(static\s+)?[\w<>\[\]]+\s+\w+\s*\([^;]*\)\s*(throws\s+[\w, ]+)?\s*{',
        flags=re.MULTILINE
    )
    return bool(method_pattern.search(code_str))

def save_content_to_file(content, filename_base, directory):
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, f"{filename_base}.java")
    with open(file_path, "w") as f:
        f.write(content)

seen_classnames = dict()

with open(input_path, 'r') as f:
    for idx, line in enumerate(f):
        try:
            entry = json.loads(line)
            func_code = entry.get(code_field)
            if func_code:
                package_stmt, code_no_package = extract_and_clean_package(func_code)
                imports_stmt, cleaned_code = extract_and_clean_imports(code_no_package)

                # Check if it has a public class and no orphan methods
                top_level_class = re.search(r'^\s*public\s+class\s+\w+', cleaned_code, re.MULTILINE)
                should_wrap = has_orphan_methods(cleaned_code) or not top_level_class

                if not should_wrap:
                    class_name = extract_top_level_type_name(cleaned_code)
                    if class_name:
                        count = seen_classnames.get(class_name, 0) + 1
                        seen_classnames[class_name] = count

                        if count == 1:
                            final_class_name = class_name
                        else:
                            final_class_name = f"{class_name}_{count}"
                            cleaned_code = rename_class_everywhere(cleaned_code, class_name, final_class_name)

                        filename_base = sanitize_filename(final_class_name)
                        final_code = '\n\n'.join(filter(None, [package_stmt, imports_stmt, cleaned_code]))
                    else:
                        filename_base = f"TempClass{idx}"
                        wrapped_code = wrap_code_in_temp_class(cleaned_code, filename_base)
                        final_code = '\n\n'.join(filter(None, [package_stmt, imports_stmt, wrapped_code]))
                else:
                    filename_base = f"TempClass{idx}"
                    wrapped_code = wrap_code_in_temp_class(cleaned_code, filename_base)
                    final_code = '\n\n'.join(filter(None, [package_stmt, imports_stmt, wrapped_code]))

                save_content_to_file(final_code.strip(), filename_base, output_dir)

        except json.JSONDecodeError:
            print(f"Skipping malformed JSON line {idx}")
        except Exception as e:
            print(f"Error processing line {idx}: {e}")

# Print how many files were created
num_files = len([f for f in os.listdir(output_dir) if f.endswith(".java")])
print(f"\nSaved {num_files} .java files in: {output_dir}\n")