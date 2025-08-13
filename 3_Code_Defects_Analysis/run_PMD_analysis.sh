#!/bin/bash

# Usage check
if [ -z "$1" ]; then
    echo "Usage: $0 <java_files_directory>"
    echo "Please provide the path to the Java files directory."
    exit 1
fi

java_dir="$1"

# Check directory
if [ ! -d "$java_dir" ]; then
    echo "Error: Directory '$java_dir' does not exist."
    exit 1
fi


# Count files in bash too
echo "Counted .java files:"
echo "  In java_dir: $(find "$java_dir" -name '*.java' | wc -l)"
echo

# List of PMD rulesets
rulesets=(
    "category/java/bestpractices.xml"
    #"category/java/codestyle.xml"
    "category/java/design.xml"
    #"category/java/documentation.xml"
    "category/java/errorprone.xml"
    "category/java/multithreading.xml"
    "category/java/performance.xml"
)

# Run PMD
for ruleset in "${rulesets[@]}"; do
    base_name=$(basename "$ruleset" .xml)
    report_file="report_unique_${base_name}.json"
    error_file="errors_unique_${base_name}.json"

    echo "Running PMD with $ruleset..."
    PMD_JAVA_OPTS="-Dpmd.error_recovery" pmd check --dir "$java_dir" --rulesets "$ruleset" --format json -r "$report_file" 2> "$error_file" --verbose -t 21

    if [ $? -eq 0 ]; then
        echo "PMD finished for $ruleset. Output: $report_file"
    else
        echo "PMD failed for $ruleset. See: $error_file"
    fi
    echo "--------------------------------------------"
done

# Clean up
rm -r "$java_dir"
echo "Deleted temporary files. All done!"