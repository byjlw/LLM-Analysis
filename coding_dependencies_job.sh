#!/bin/bash

# Check if API key is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <api_key> [num_ideas] [start_step working_dir]"
    echo "Examples:"
    echo "  Basic: $0 sk_or_..."
    echo "  With num_ideas: $0 sk_or_... 20"
    echo "  With start_step: $0 sk_or_... 15 2 my_analysis"
    exit 1
fi

API_KEY=$1
NUM_IDEAS=${2:-15}
START_STEP=${3:-1}
WORKING_DIR=${4:-$(date "+%m-%d-%y-%H-%M-%S")}

# Validate that working_dir is provided if start_step is specified
if [ "$START_STEP" != "1" ] && [ "$#" -lt 4 ]; then
    echo "Error: When specifying start_step, working_dir must also be provided"
    echo "Example: $0 sk_or_... 15 2 my_analysis"
    exit 1
fi

# Array of models to test
declare -a models=(
    "qwen/qwen-2.5-coder-32b-instruct"
    "meta-llama/llama-3.3-70b-instruct"
    "openai/gpt-4o-2024-11-20"
    "deepseek/deepseek-chat"
)

# Function to get clean model name
get_clean_model_name() {
    local model=$1
    echo "$model" | tr '/' '_' | tr '[:upper:]' '[:lower:]'
}

# Function to get directory name for a model
get_model_dir() {
    local model=$1
    local clean_model=$(get_clean_model_name "$model")
    echo "${WORKING_DIR}/${clean_model}"
}

# Function to run analysis with a specific model
run_analysis() {
    local model=$1
    local model_dir=$(get_model_dir "$model")
    
    # For non-step-1, check if directory exists
    if [ "$START_STEP" != "1" ]; then
        if [ ! -d "output/${model_dir}" ]; then
            echo "Skipping model $model - no existing directory found in output/${WORKING_DIR}"
            return 0
        fi
    fi
    
    echo "Running analysis with model: $model"
    
    # Run the command and capture both stdout and stderr
    if ! llm-analysis coding-dependencies \
        --api-key "$API_KEY" \
        --model "$model" \
        --num-ideas "${NUM_IDEAS}" \
        --start-step "$START_STEP" \
        --working-dir "$model_dir"; then
        echo "Error: Analysis failed for model $model"
        return 1
    fi
    
    echo "Completed analysis with model: $model"
    echo "Results stored in output/$model_dir"
    echo "----------------------------------------"
}

# Main execution
echo "Starting dependency analysis job..."
echo "Number of ideas to generate: $NUM_IDEAS"
if [ "$START_STEP" != "1" ]; then
    echo "Using custom start step: $START_STEP"
    echo "Using working directory: $WORKING_DIR"
fi
echo "----------------------------------------"

# Run analysis for each model
for model in "${models[@]}"; do
    if ! run_analysis "$model"; then
        echo "Warning: Continuing with next model..."
    fi
    # Add small delay between runs to avoid rate limiting
    sleep 2
done

echo "Job completed!"
