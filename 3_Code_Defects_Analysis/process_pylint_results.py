import json
import pprint
from collections import Counter, defaultdict

# === CONFIG ===
model = input("Specify name of model to analyze: ") 
INPUT_FILE = f"pylint_output_{model}_with_odc.jsonl"

# === SYMBOLS TO EXCLUDE ===
EXCLUDED_SYMBOLS = {
    "bad-indentation",
    "missing-module-docstring",
    "missing-function-docstring",
    "missing-final-newline",
    "bad-docstring-quotes",
    "consider-using-f-string",
    "undefined-variable",
    "import-error",  # ImportError is not a defect in the code, but a problem with the environment -> AI assistants add unuseful imports
    "invalid-name", # not a defect, but a style issue
    "redundant-u-string-prefix", # python 2.0 syntax
    "multiple-statements" # multiple statements on one line (colon) -> not a defect, but a style issue
    "pointless-string-statement", # not a defect, but a style issue
    "unnecessary-comprehension" # not a defect, but a style issue
}

# === VARIABILI DI SUPPORTO ===
total_defects = 0
total_size = 0
syntax_error_count = 0
odc_counter = Counter()
symbol_counter = Counter()
unique_defective_indices = set()
defects_by_index = defaultdict(list)
symbols_by_odc = defaultdict(Counter)

# === ELABORAZIONE FILE ===
with open(INPUT_FILE, "r") as f:
    for line in f:
        data = json.loads(line)
        index = data.get("hm_index")
        messages = data.get("pylint_output", [])
        total_size += 1

        has_valid_defect = False

        for msg in messages:
            symbol = msg.get("symbol")
            odc = msg.get("odc_category", "--")

            if symbol in EXCLUDED_SYMBOLS:
                continue 

            if symbol == "syntax-error":
                syntax_error_count += 1
                continue

            if odc != "--":
                total_defects += 1
                odc_counter[odc] += 1
                symbol_counter[symbol] += 1
                defects_by_index[index].append(odc)
                symbols_by_odc[odc][symbol] += 1
                has_valid_defect = True

        if has_valid_defect:
            unique_defective_indices.add(index)

# === CALCOLO STATISTICHE ===
unique_instance_count = len(unique_defective_indices)
average_defects_per_instance = total_defects / unique_instance_count if unique_instance_count else 0

# === OUTPUT STATISTICHE ===
print("\nPylint + ODC stats")
print("────────────────────────────")
print(f"Total number of defects: {total_defects}")
print(f"Total number of defective samples: {unique_instance_count} ({(unique_instance_count/total_size)*100:.2f}%)")
print(f"Total number of syntax errors: {syntax_error_count} ({(syntax_error_count/total_size)*100:.2f}%)")
print(f"Average number of defects per sample: {average_defects_per_instance:.2f}")

print("\nTotal defects divided per ODC Defect Type::")
for category, count in odc_counter.most_common():
    print(f"  - {category}: {count}")

print("\nTop 10 defects:")
for symbol, count in symbol_counter.most_common(10):
    print(f"  - {symbol}: {count}")

print("\nDistribution of ODC Defect Types per sample:")
distribution = Counter(len(set(v)) for v in defects_by_index.values())
for num_cats, count in sorted(distribution.items()):
    print(f"  - {count} samples in {num_cats} different ODC defect types")

print("\nDistrbution of defects per ODC Defect Type:")
for odc, sym_counter in symbols_by_odc.items():
    print(f"\n  {odc} ({sum(sym_counter.values())})")
    for symbol, count in sym_counter.most_common():
        print(f"   • {symbol}: {count}")
