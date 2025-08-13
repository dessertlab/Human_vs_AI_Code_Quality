import json
import os
import tempfile
import subprocess
from tqdm import tqdm
import pandas as pd

# === CONFIG ===
INPUT_FILE = ""     # Your dataset
OUTPUT_FILE = ""     # Adjust for code type
CODE_TYPE_TO_ANALYZE = ""                    # field name in the dataset
ODC_MAPPING_XLSX = "../../category_ODC_pylint.xlsx"  # mapping file

# # === SYMBOLS TO EXCLUDE ===
# EXCLUDED_SYMBOLS = {
#     "bad-indentation",
#     "missing-function-docstring",
#     "missing-module-docstring",
#     "missing-final-newline",
#     "bad-docstring-quotes",
#     "consider-using-f-string",
#     "undefined-variable"
# }


# === Load ODC Mapping from Excel ===
def load_odc_mapping_from_excel(xlsx_path: str) -> dict:
    df = pd.read_excel(xlsx_path, engine="openpyxl")
    return dict(zip(df["Pylint Symbol"], df["ODC Defect Type"]))

odc_mapping = load_odc_mapping_from_excel(ODC_MAPPING_XLSX)

# === Run pylint and capture JSON output ===
def run_pylint_json(code: str) -> list:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(code)
        tmp_filename = tmp.name

    try:
        result = subprocess.run(
            ["pylint", tmp_filename, "--output-format=json", "--score=no", "-j=21"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        output = result.stdout.strip()
        json_output = json.loads(output) if output else []
    except subprocess.TimeoutExpired:
        json_output = [{"type": "fatal", "message": "Pylint timeout"}]
    except Exception as e:
        json_output = [{"type": "fatal", "message": str(e)}]
    finally:
        os.unlink(tmp_filename)

    # ➕ Add ODC category to each message
    filtered_output = []
    for msg in json_output:
        symbol = msg.get("symbol")
        # if symbol in EXCLUDED_SYMBOLS:
        #     continue  # 
        msg["odc_category"] = odc_mapping.get(symbol, "--")
        filtered_output.append(msg)

    return filtered_output


    return json_output

# === Main loop ===
with open(INPUT_FILE, "r") as infile, open(OUTPUT_FILE, "w") as outfile:
    for line in tqdm(infile, desc=f"Analyzing {CODE_TYPE_TO_ANALYZE}"):
        item = json.loads(line)
        hm_index = item.get("hm_index")
        code = item.get(CODE_TYPE_TO_ANALYZE, "")
        if not code.strip():
            continue

        pylint_json = run_pylint_json(code)
        outfile.write(json.dumps({
            "hm_index": hm_index,
            "pylint_output": pylint_json
        }) + "\n")

print(f"Output saved to {OUTPUT_FILE}")