import json
import pprint
import argparse
import re
from collections import defaultdict
from collections import defaultdict, Counter 

"""
Read filename and max batch number from commandline. Rename all the files to have a single name and number.
"""

parser = argparse.ArgumentParser(description='Process Semgrep results.')
parser.add_argument('json_filename', type=str, help='Base filename for Semgrep JSON results')
parser.add_argument('max_batch_num', type=int, help='Maximum batch number to process')

args = parser.parse_args()
json_filename = args.json_filename
max_batch_num = args.max_batch_num

"""
Read json file in batches and create a single list of total errors, results, and scanned files.
Count number of issues, number of scanned file, number of files that caused errors and compute issues percentage.

NB: skipped files contain errors (already accounted for in total_errors) and incompatible rules due to version 
and language (filtered out from the errors)
"""

total_errors = []
total_results = []
total_scanned = []
total_skipped = []

for i in range(1, max_batch_num + 1):
    json_filename_complete = f"{json_filename}_{i}.json"
    filtered_errors = []
    with open(json_filename_complete, 'r', encoding='utf-8') as results_f:
        samples = json.load(results_f)
        filtered_errors.extend(
            [error for error in samples['errors'] if not error['path'].startswith('https:/semgrep.dev/...')]
        )  # Filtering out incompatible rules
        total_errors.extend(filtered_errors)
        total_results.extend(samples['results'])
        total_scanned.extend(samples['paths']['scanned'])
        total_skipped.extend(samples['paths']['skipped'])

"""
Calculate file number from the filename to obtain the dataset line number and insert it into the path field.
This is done to filter out duplicates.
"""
pattern = r'.*_(\d+)\.py'

def calculate_line_number(filename):
    match = re.match(pattern, filename)
    # print(f"Filename: {filename}, Match: {int(match.group(1)) if match else None}")
    return int(match.group(1)) if match else None


for error in total_errors:
    error['path'] = calculate_line_number(error['path'])

for result in total_results:
    result['path'] = calculate_line_number(result['path'])

for i in range(len(total_scanned)):
    total_scanned[i] = calculate_line_number(total_scanned[i])


"""
Remove duplicates from the errors and results lists.
_______________________
dedup_err is the list of errors w/o duplicates
dedup_res is the list of defective functions (i.e., w/o duplicated issues)
total_results is the list of issues w/o errors
dedup_res_no_errors is the list of defective functions w/o errors
"""

dedup_err = {err['path'] for err in total_errors}
dedup_res = {res['path'] for res in total_results}

dedup_res_no_errors = [res for res in dedup_res if res not in dedup_err]
total_results = [res for res in total_results if res['path'] not in dedup_err]

"""
Normalize CWE names dynamically to ensure uniqueness.
"""

def extract_cwe_number(cwe_name):
    """Extract CWE-XXX format from any given CWE description."""
    match = re.match(r"(CWE-\d+)", cwe_name, re.IGNORECASE)
    return match.group(1) if match else cwe_name


"""
Divide issues based on category type. 
Since not all issues are correctly categories (i.e., missing "category" field), 
we select them based on whether they have a "CWE" field.
"""

security_issues = []
seen_issues = set()
severity_types = set()
normalized_cwe_dict = defaultdict(str)

# Process security issues and normalize CWEs
for result in total_results:
    metadata = result.get('extra', {}).get('metadata', {})
    cwes = metadata.get('cwe')
    severity = result.get('extra', {}).get('severity')

    if cwes:
        if isinstance(cwes, list):
            updated_cwes = []
            for cwe in cwes:
                base_cwe = extract_cwe_number(cwe)
                if base_cwe in normalized_cwe_dict:
                    standardized_cwe = max(normalized_cwe_dict[base_cwe], cwe, key=len)
                else:
                    standardized_cwe = cwe  # Keep first occurrence as reference
                    normalized_cwe_dict[base_cwe] = standardized_cwe
                updated_cwes.append(standardized_cwe)
            result['extra']['metadata']['cwe'] = [cwe.upper() for cwe in updated_cwes]
        else:
            cwes = f"{cwes.upper()}"
            base_cwe = extract_cwe_number(cwes)
            if base_cwe in normalized_cwe_dict:
                standardized_cwe = max(normalized_cwe_dict[base_cwe], cwes, key=len)
            else:
                standardized_cwe = cwes  # Keep first occurrence as reference
                normalized_cwe_dict[base_cwe] = standardized_cwe
            result['extra']['metadata']['cwe'] = standardized_cwe.upper()

        # Use a unique identifier for each issue (path, CWE, severity, and message)
        issue_id = (
            result['path'], 
            tuple(sorted(result['extra']['metadata']['cwe'])),  # Ensure consistent ordering of CWEs
            result['extra'].get('severity', ''), 
            result['extra'].get('lines', '').strip(),  # Remove accidental whitespace
        )

        if issue_id not in seen_issues:
            seen_issues.add(issue_id)  # Add to set to track unique issues
            security_issues.append(result)

        if severity:
            severity_types.add(severity)

# Deduplicate CWEs by keeping only the longest description for each CWE number
deduplicated_cwes = {}

for base_cwe, cwe_description in normalized_cwe_dict.items():
    base_cwe = base_cwe.upper()  # Ensure "CWE" is always uppercase
    cwe_description = cwe_description.strip()  # Remove any accidental spaces

    # Keep the longest description per CWE number
    if base_cwe not in deduplicated_cwes or len(cwe_description) > len(deduplicated_cwes[base_cwe]):
        deduplicated_cwes[base_cwe] = cwe_description

unified_cwes = set(deduplicated_cwes.values())

for result in security_issues:
    metadata = result.get('extra', {}).get('metadata', {})
    cwes = metadata.get('cwe')

    if cwes:
        if isinstance(cwes, list):
            result['extra']['metadata']['cwe'] = [deduplicated_cwes[extract_cwe_number(cwe).upper()] for cwe in cwes]
        else:
            result['extra']['metadata']['cwe'] = deduplicated_cwes[extract_cwe_number(cwes).upper()]

"""
NEW: Compute and print the Top‑10 most frequent CWEs across the dataset
"""

cwe_counter = Counter()
for issue in security_issues:
    cwes = issue['extra']['metadata']['cwe']
    if isinstance(cwes, list):
        cwe_counter.update(cwes)
    else:
        cwe_counter.update([cwes])


"""
Divide security-related issues by CWE severity category.
"""

cwes_by_severity = {severity: {} for severity in severity_types}

for issue in security_issues:
    metadata = issue.get('extra', {}).get('metadata', {})
    cwes = metadata.get('cwe')
    severity = issue.get('extra', {}).get('severity')

    if severity and cwes:
        if isinstance(cwes, list):
            for cwe in cwes:
                if cwe not in cwes_by_severity[severity]:
                    cwes_by_severity[severity][cwe] = []
                cwes_by_severity[severity][cwe].append(issue)
        else:
            if cwes not in cwes_by_severity[severity]:
                cwes_by_severity[severity][cwes] = []
            cwes_by_severity[severity][cwes].append(issue)

cwes_counts_by_severity = {
    severity: {cwe: len(issues) for cwe, issues in cwes_dict.items()}
    for severity, cwes_dict in cwes_by_severity.items()
}

"""
Compute percentages of defects, errors and clean functions.

NB: security_issues is already error-free because "total_results" is error free 
-> we only need to remove path duplicates to obtain the number of defective functions (only security)
"""

# Computing defective functions (i.e., removing duplicate security issues). 
# We only need the number and path to later remove them from the dataset
defective_func_security_set = {issue['path'] for issue in security_issues}

defective_func_rate = (len(defective_func_security_set) / len(total_scanned)) * 100
errors_rate = (len(dedup_err) / len(total_scanned)) * 100
clean_rate = ((len(total_scanned) - len(defective_func_security_set) - len(dedup_err)) / len(total_scanned)) * 100

print(f"Total skipped functions: {len(total_skipped)} (errors + incompatible rules)")
print(f"Total scanned functions: {len(total_scanned)} (100%)")
print(f"Total clean functions: {len(total_scanned)-len(defective_func_security_set)-len(dedup_err)} ({clean_rate:.2f}%)")
print(f"Total defective functions (excluding errors): {len(defective_func_security_set)} ({defective_func_rate:.2f}%)")
print(f"Total errors: {len(total_errors)}. Errors w/o duplicates: {len(dedup_err)} ({errors_rate:.2f}%)")
print(f"Total issues (considering multiple issues per function and excluding errors): {len(security_issues)}")

print(f"\nFinal Unified CWE Set (without duplicates): {len(unified_cwes)}")
# pprint.pprint(unified_cwes)

print("\nTop 10 CWEs by occurrence (across all severities):")
for rank, (cwe, count) in enumerate(cwe_counter.most_common(10), start=1):
    print(f"{rank:2}. {cwe}: {count}")

print(f"\nSeverity types: {severity_types}")
print(f"CWEs divided by severity:")
pprint.pprint(cwes_counts_by_severity)


