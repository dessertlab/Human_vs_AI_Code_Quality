import time
import subprocess
import os
import argparse
import shutil
from pathlib import Path

def run_semgrep_analysis(temp_dir, json_filename):
    start_time = time.time()

    print(f"Running Semgrep analysis on files in {temp_dir} and saving results to {json_filename}...")
    original_dir = os.getcwd()

    try:
        os.chdir(temp_dir)

        semgrep_command = [
            "semgrep", "scan",
            "--verbose",
            "--output", json_filename,
            "--json",
            "-j", "21",
            "--no-git-ignore",
            "--max-memory=30000",
            "--max-target-bytes=1000000",
            "--timeout-threshold", "10",
            "--timeout", "60",
            "--metrics", "off",
            "--config", "p/trailofbits",
            "--config", "p/default",
            "--config", "p/comment",
            "--config", "p/java",
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
            "."
        ]
        
        subprocess.run(semgrep_command, check=True)
    finally:
        os.chdir(original_dir)

    end_time = time.time()
    run_semgrep_time = end_time - start_time
    return run_semgrep_time

def batch_files(input_folder, batch_size):
    """Yields batches of files from the input folder."""
    java_files = list(Path(input_folder).rglob("*.java"))
    for i in range(0, len(java_files), batch_size):
        yield java_files[i:i + batch_size]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Batch process Java files and run Semgrep analysis.')
    parser.add_argument('dataset_name', type=str, help='The dataset name for output files.')
    parser.add_argument('batch_size', type=int, help='Number of files to process per batch.')
    args = parser.parse_args()

    input_folder = "./wrapped"
    output_folder = "./semgrep_batches"  
    temp_dir = "./temp_batch" 
    dataset_name = args.dataset_name
    batch_size = args.batch_size

    Path(output_folder).mkdir(parents=True, exist_ok=True)

    for batch_index, batch in enumerate(batch_files(input_folder, batch_size)):
        if Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
        Path(temp_dir).mkdir(parents=True, exist_ok=True)

        for file in batch:
            shutil.copy(file, temp_dir)

        json_filename = os.path.abspath(os.path.join(output_folder, f"{dataset_name}_semgrep_results_batch_{batch_index+1}.json"))

        try:
            batch_time = run_semgrep_analysis(temp_dir, json_filename)
            print(f"Batch {batch_index+1} completed in {batch_time:.2f} minutes ({batch_time/60:.2f} hrs).")
        except Exception as e:
            print(f"Error processing batch {batch_index+1}: {e}")

        shutil.rmtree(temp_dir)