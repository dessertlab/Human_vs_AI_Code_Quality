# Human-Written vs. AI-Generated Code: A Large-Scale Study of Defects, Vulnerabilities, and Complexity

This repository contains the datasets, code, and analyses used in our experiments on code defects, security vulnerabilities and code complexity, as well as ODC (Orthogonal Defect Classification) mappings and final experimental results.

## 1. **Datasets**

  Raw and processed Python and Java datasets used in our study are available on Zenodo at the following link: [datasets](https://zenodo.org/records/15423067). The Python dataset (``python_dataset.jsonl``) contains 285,249 samples, while the Java dataset (``java_dataset.jsonl``) contains 221,795 samples. Each sample has the following structure: ``<index, Human-code, ChatGPT-code, DeepSeek-Coder-code, Qwen-Coder-code>``. 

## 2. **ODC_Mapping**

  Contains the mapping of each rule to ODC defect type for both Pylint (Python) and PMD (Java) used to support our classification of defects.

## 3. **Code_Defects_Analysis**

  This folder contains all code to perform the defects analysis on both Python and Java. 
  
  - _Python_
    - use ``pylint_ODC.py`` to run Pylint on the Python dataset. Modify the jsonl field to analyze (i.e., ``[modelname]_code``)
    - use ``process_pylint_results.py`` to process the results of the previous analysis. This will output a complete report of defective samples, syntax errors, and ODC defect types distribution. 

  - _Java_
    - use ``wrap_java_functions.py`` to wrap all Java samples in minimal dummy classes prior to analysis. This ensures compatibility with PMD, which requires valid Java class structures to work. 
    - use ``run_PMD_analysis.sh`` to run PMD on the Java dataset. Modify the jsonl field to analyze (i.e., ``[modelname]_code``)
    - use ``process_PMD_results.py`` to process the results of the previous analysis. This will output a complete report of defective samples, syntax errors, and ODC defect types distribution. 

## 4. **Code_Security_Analysis**  
  
  This folder contains all code to perform the security vulnerability analysis on both Python and Java using Semgrep.
  
  - _Python_
    - use ``run_semgrep_python.py`` to run Semgrep on the Python dataset. Modify the jsonl field to analyze (i.e., ``[modelname]_code``)
    - use ``process_semgrep_results_python.py`` to process the results of the previous analysis. This will output a complete report of vulnerable samples, errors, and CWEs distribution. 

  - _Java_
    - use ``run_semgrep_java.py`` to run Semgrep on the Java dataset. Modify the jsonl field to analyze (i.e., ``[modelname]_code``).
    - use ``process_semgrep_results_java.py`` to process the results of the previous analysis. This will output a complete report of vulnerable samples, errors, and CWEs distribution. 

## 5. **Code_Complexity_Analysis**  

  Contains scripts, metrics, and results related to code complexity analysis for Python (``complexity_stats_python.py``) and Java (``complexity_stats_java.py``). This includes measures such as NLOC, cyclomatic complexity, and token counts computed using Lizard and Tiktoken. 


## 6. **Results**  

  Contains the complete reports and results obtained from our experimental evaluation, including reports on defects, security vulnerabilities and complexity metrics for both Python and Java.