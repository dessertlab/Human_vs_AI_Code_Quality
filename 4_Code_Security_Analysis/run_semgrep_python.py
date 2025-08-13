import json
import os
import subprocess
import time
import argparse
import shutil

def split_jsonl_to_python_files(jsonl_file, output_prefix, lines_per_file=1, files_per_batch=20000):
    start_time = time.time()

    outputs = []

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():  # Skip empty lines
                item = json.loads(line)
                try:
                    output = item.get('') # Select the key you want to extract
                except Exception:
                    outputs.append(item)
                else:
                    outputs.append(output)

    total_lines = len(outputs)
    total_files = total_lines // lines_per_file
    total_batches = (total_files + files_per_batch - 1) // files_per_batch

    print(f"Total lines: {total_lines}, Total files: {total_files}, Total batches: {total_batches}")

    split_times = []
    semgrep_times = []
    delete_times = []

    temp_dir = f"{output_prefix}_tempfiles"
    os.makedirs(temp_dir, exist_ok=True)

    for batch in range(total_batches):
        print(f"Processing batch {batch + 1}/{total_batches}")
        batch_start_index = batch * files_per_batch * lines_per_file
        batch_end_index = min((batch + 1) * files_per_batch * lines_per_file, total_lines)
        batch_outputs = outputs[batch_start_index:batch_end_index]

        num_files = (batch_end_index - batch_start_index) // lines_per_file

        # 1. Write the batch files
        batch_split_start = time.time()
        for i in range(num_files):
            start_index = batch_start_index + i * lines_per_file
            end_index = start_index + lines_per_file
            chunk = batch_outputs[start_index - batch_start_index:end_index - batch_start_index]

            output_file = os.path.join(temp_dir, f"{output_prefix}_{start_index+1}.py")
            with open(output_file, 'w', encoding='utf-8') as f_out:
                for line in chunk:
                    f_out.write(line)
        batch_split_end = time.time()
        split_times.append(batch_split_end - batch_split_start)

        # 2. Run Semgrep on the batch
        json_filename = f"{output_prefix}_semgrep_results_batch_{batch+1}.json"
        batch_semgrep_time = run_semgrep_analysis(json_filename, temp_dir)
        semgrep_times.append(batch_semgrep_time)

        # 3. Clean up only this batch's files
        batch_delete_start = time.time()
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if file_path.endswith('.py') and os.path.isfile(file_path):
                os.remove(file_path)
        batch_delete_end = time.time()
        delete_times.append(batch_delete_end - batch_delete_start)

    # Final full clean-up
    shutil.rmtree(temp_dir)

    end_time = time.time()
    split_json_time = end_time - start_time
    return split_json_time, split_times, semgrep_times, delete_times

def run_semgrep_analysis(json_filename, target_dir):
    start_time = time.time()

    print(f"Running Semgrep analysis on {target_dir} and saving results to {json_filename}...")
    semgrep_command = [
        "semgrep", "scan",
        "--verbose",
        "--output", json_filename,
        "--json",
        "--no-git-ignore",
        "--max-memory=30000",
        "--max-target-bytes=1000000",
        "--timeout-threshold", "10",
        "--timeout", "60",
        "--metrics", "off",
        "--include", "*.py",  # <-- only scan Python files
        "--config", "p/trailofbits",
        "--config", "p/default",
        "--config", "p/comment",
        "--config", "p/python",
        "--config", "p/cwe-top-25",
        "--config", "p/owasp-top-ten",
        "--config", "p/r2c-security-audit",
        "--config", "p/insecure-transport",
        "--config", "p/secrets",
        "--config", "p/findsecbugs",
        "--config", "p/gitlab",
        "--config", "p/mobsfscan",
        "--config", "p/command-injection",
        "--config", "p/sql-injection",
        target_dir
    ]
    
    subprocess.run(semgrep_command, check=True)

    end_time = time.time()
    run_semgrep_time = end_time - start_time
    return run_semgrep_time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process JSONL file and run Semgrep analysis.')
    parser.add_argument('jsonl_file', type=str, help='The path to the JSONL file.')

    args = parser.parse_args()

    json_filename = os.path.basename(args.jsonl_file)
    output_prefix = os.path.splitext(json_filename)[0]

    start_time = time.time()

    split_json_time, split_times, semgrep_times, delete_times = split_jsonl_to_python_files(args.jsonl_file, output_prefix)

    end_time = time.time()
    total_time = end_time - start_time

    print(f"Total execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")

    print("\nDetailed timings per batch:")
    for i, (split_time, semgrep_time, delete_time) in enumerate(zip(split_times, semgrep_times, delete_times), start=1):
        print(f"Batch {i}: Semgrep time: {semgrep_time:.2f} s, Batch cleanup time: {delete_time:.2f} s")
