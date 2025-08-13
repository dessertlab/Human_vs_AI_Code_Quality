import json
import os
import re
import pandas as pd
from collections import Counter, defaultdict

# === CONFIG ===
REPORTS_DIR = "./reports"  # folder with files report_*.json
ODC_MAPPING_FILE = "../../category_ODC_PMD.xlsx"  # mapping PMD rule -> ODC
EXCLUDED_RULES = {
    "AvoidDuplicateLiterals",
    "UseLocaleWithCaseConversions",
    "AbstractClassWithoutAbstractMethod", 
    "AccessorClassGeneration",
    "AbstractClassWithoutAnyMethod",
    "ClassWithOnlyPrivateConstructorsShouldBeFinal", 
    "DataClass",
    "GodClass", 
    "CloneMethodReturnTypeMustMatchClassName",
    "MethodWithSameNameAsEnclosingClass", 
    "MissingStaticMethodInNonInstantiatableClass", 
    "UseUtilityClass", 
    "LawOfDemeter", 
    "UnusedPrivateMethod", 
    "AvoidLiteralsInIfCondition"
}

# === Load mapping PMD -> ODC ===
mapping_df = pd.read_excel(ODC_MAPPING_FILE, engine="openpyxl")
odc_map = dict(zip(mapping_df["PMD Rule"], mapping_df["ODC Defect Type"]))

input("Did you change the total size of the dataset?")

# === VARIABILI DI SUPPORTO ===
total_size = 221795 

total_defects = 0
odc_counter = Counter()
rule_counter = Counter()
unique_defective_files = set()
defects_by_file = defaultdict(list)
rules_by_odc = defaultdict(Counter)

# === NUOVE VARIABILI PER ERRORI ===
processing_errors = defaultdict(int)
error_types_count = Counter()
parse_exception_filenames = set()
priority_counter = Counter()
exception_regex = re.compile(r"(\w+Exception)")

# === PARSING FILES REPORT ===
for fname in os.listdir(REPORTS_DIR):
    if fname.startswith("report_") and fname.endswith(".json"):
        with open(os.path.join(REPORTS_DIR, fname)) as f:
            data = json.load(f)

        # === ERRORI DI PARSING ===
        if "processingErrors" in data:
            for error in data["processingErrors"]:
                processing_errors["total"] += 1

                message = error.get("message", "")
                match = exception_regex.search(message)
                if match:
                    error_type = match.group(1)
                    error_types_count[error_type] += 1

                    if error_type == "ParseException":
                        filename = error.get("filename")
                        if filename:
                            parse_exception_filenames.add(filename)


        for file_entry in data.get("files", []):
            filename = file_entry.get("filename")
            has_valid_defect = False

            for violation in file_entry.get("violations", []):
                rule = violation.get("rule")
                odc = odc_map.get(rule, "--")
                priority = violation.get("priority")
                if priority:
                    priority_counter[priority] += 1

                if rule in EXCLUDED_RULES:
                    continue  # skip excluded rules

                if odc != "--":
                    total_defects += 1
                    odc_counter[odc] += 1
                    rule_counter[rule] += 1
                    defects_by_file[filename].append(odc)
                    rules_by_odc[odc][rule] += 1
                    has_valid_defect = True

            if has_valid_defect:
                unique_defective_files.add(filename)

unique_instance_count = len(unique_defective_files)
average_defects_per_instance = total_defects / unique_instance_count if unique_instance_count else 0

print("\nPMD + ODC stats")
print("────────────────────────────")
print(f"Total number of samples: {total_size}")
print(f"Total number of defects: {total_defects}")
print(f"Total number of defective samples: {unique_instance_count} ({(unique_instance_count/total_size)*100:.2f}%)")
print(f"Average number of defects per sample: {average_defects_per_instance:.2f}")
print(f"Total number of samples with ParseException: {len(parse_exception_filenames)} ({(len(parse_exception_filenames)/total_size)*100:.2f}%)")

print("\nTotal defects divided per ODC Defect Type:")
for category, count in odc_counter.most_common():
    print(f"  - {category}: {count}")

print("\nTop 10 defect:")
for rule, count in rule_counter.most_common(10):
    print(f"  - {rule}: {count}")

print("\nDistribution of ODC Defect Types per sample:")
distribution = Counter(len(set(v)) for v in defects_by_file.values())
for num_cats, count in sorted(distribution.items()):
    print(f"  - {count} samples in {num_cats} different ODC defect types")

print("\nDistrbution of defects per ODC Defect Type:")
for odc, rule_counter in rules_by_odc.items():
    print(f"\n🔸 {odc} ({sum(rule_counter.values())})")
    for rule, count in rule_counter.most_common():
        print(f"   • {rule}: {count}")

print("\nDistribution of defects per priority (severity):")
for p, count in sorted(priority_counter.items()):
    print(f"  - Priority {p}: {count}")

