import json
import tiktoken
import lizard
import statistics
from collections import defaultdict
from tqdm import tqdm

ENC = tiktoken.encoding_for_model("gpt-4")

def analyze_code(code: str):
    lines = code.splitlines()
    analysis = lizard.analyze_file.analyze_source_code("temp.java", code)
    function_metrics = []
    token_set = set()

    for func in analysis.function_list:
        try:
            snippet = "\n".join(lines[func.start_line - 1 : func.end_line])
            tokens = ENC.encode(snippet)
            token_set.update(tokens)
            function_metrics.append({
                "nloc": func.nloc,
                "ccn": func.cyclomatic_complexity,
                "token_count": len(tokens),
                "function_name_length": len(func.name)
            })
        except Exception as e:
            print(f"Skipping a function due to error: {e}")
    return function_metrics, token_set

def print_stats(metrics_by_field, tokens_by_field):
    for field, metrics in metrics_by_field.items():
        print(f"\nStats for {field} ({len(metrics)} functions):")
        for key in ["nloc", "ccn", "token_count", "function_name_length"]:
            values = [m[key] for m in metrics]
            print(f"  {key.upper():20} | Avg: {statistics.mean(values):6.2f} | Min: {min(values):3} | Max: {max(values):3} | Std: {statistics.stdev(values):6.2f}" if len(values) > 1 else f"  {key.upper():20} | Only one value: {values[0]}")
        print(f"  {'UNIQUE_TOKENS':20} | Total: {len(tokens_by_field[field])}")

    all_metrics = [m for metrics in metrics_by_field.values() for m in metrics]
    all_tokens = set().union(*tokens_by_field.values())
    print(f"\nAggregated Stats across ALL models ({len(all_metrics)} functions):")
    for key in ["nloc", "ccn", "token_count", "function_name_length"]:
        values = [m[key] for m in all_metrics]
        print(f"  {key.upper():20} | Avg: {statistics.mean(values):6.2f} | Min: {min(values):3} | Max: {max(values):3} | Std: {statistics.stdev(values):6.2f}")
    print(f"  {'UNIQUE_TOKENS':20} | Total: {len(all_tokens)}")

def main():
    metrics_by_field = defaultdict(list)
    tokens_by_field = defaultdict(set)

    with open("java_dataset.jsonl", "r") as f:
        lines = f.readlines()
        for line in tqdm(lines, desc="Processing Java code"):
            item = json.loads(line)
            for field in ["human_code", "chatgpt_code", "dsc_code", "qwen_code"]:
                code = item.get(field)
                if code:
                    metrics, tokens = analyze_code(code)
                    metrics_by_field[field].extend(metrics)
                    tokens_by_field[field].update(tokens)

    print_stats(metrics_by_field, tokens_by_field)

if __name__ == "__main__":
    main()
