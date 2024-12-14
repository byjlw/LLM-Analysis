# LLM Analysis
**A python project that uses LLMs, to analyze LLMs, built using an LLM. 90% of this code is generated using cline and Clude 3.5 Sonnet**
A Python tool for analyzing various aspects of Large Language Model (LLM) outputs. Currently focused on analyzing code dependencies to determine which frameworks are being used for particular coding requests.

See [Project Summary](docs/PROJECT_SUMMARY.md) for more details on the design

## Features
- Generate product ideas using LLM models
- Convert product ideas into detailed requirements
- Generate code implementations based on requirements
- Analyze and track frameworks used in generated code
- Comprehensive dependency tracking and analysis
- Flexible workflow with ability to start from any step
- Custom working directory naming
- Verified at num ideas up to 100
- Verified against Llama, Antropic, Qwen, OpenAI and DeepSeek models

## Requirements

- Python 3.10 or higher
- OpenRouter API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/byjlw/llm-analysis.git
cd llm-analysis
```

2. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Usage

Run the code dependency analysis with default settings:
```bash
llm-analysis coding-dependencies --api-key your-api-key-here
```

Customize the run with command-line options:
```bash
llm-analysis coding-dependencies \
    --config path/to/config.json \
    --model meta-llama/llama-3.3-70b-instruct \
    --output-dir custom/output/path \
    --log-level DEBUG \
    --start-step 2 \
    --working-dir my-project
```

### Multi-Model Analysis Script

Analyze multiple models at once using this script. Update the script with the models you want to use.
```bash
./coding_dependencies_job.sh <api_key> [num_ideas] [start_step working_dir]
```

Parameters:
- `api_key`: (Required) Your OpenRouter API key
- `num_ideas`: (Optional) Number of ideas to generate (defaults to 15)
- `start_step`: (Optional) Which pipeline stage to start from (1-4)
- `working_dir`: (Required if start_step is provided) Name of the working directory

Examples:
```bash
# Basic usage - creates timestamped directory
./coding_dependencies_job.sh sk_or_...

# Generate 20 ideas - creates timestamped directory
./coding_dependencies_job.sh sk_or_... 20

# Start from step 2 using existing directory
./coding_dependencies_job.sh sk_or_... 15 2 my_analysis
```

The script:
- Runs analysis using multiple models
- Directory structure:
  * Creates a parent working directory (timestamp if not specified)
  * Each model gets its own subdirectory within the working directory
- When starting from a later step (2-4):
  * Uses the specified working directory
  * Skips models that don't have existing subdirectories
- Continues to next model if one fails
- Includes delay between runs to prevent rate limiting

Example output structure:
```
output/
└── 03-15-24-14-30-45/          # Parent directory (timestamp or user-specified)
    ├── qwen_qwen-2.5-coder-32b-instruct/
    │   ├── ideas.json
    │   ├── requirements/
    │   ├── code/
    │   └── dependencies.json
    ├── meta-llama_llama-3.3-70b-instruct/
    ├── openai_gpt-4o-2024-11-20/
    └── deepseek_deepseek-chat/
```

### Available Steps

The code dependency analysis follows a 4-step process:
1. Ideas Generation (`--start-step 1` or `--start-step ideas`)
2. Requirements Analysis (`--start-step 2` or `--start-step requirements`)
3. Code Generation (`--start-step 3` or `--start-step code`)
4. Dependencies Collection (`--start-step 4` or `--start-step dependencies`)

You can start from any step using the `--start-step` argument. The tool will assume that any necessary files from previous steps are already present in the working directory.

### Working Directory

By default, the tool creates a timestamped directory for each run. You can specify a custom directory name using the `--working-dir` argument:

```bash
llm-analysis coding-dependencies --working-dir my-project
```

## Configuration Options

### Command Line Arguments

All available command line arguments:

- `--api-key`: OpenRouter API key (can also be set via OPENROUTER_API_KEY environment variable)
- `--output-dir`: Output directory (default: 'output')
- `--working-dir`: Working directory name (defaults to timestamp)
- `--num-ideas`: Number of ideas to generate (default: 15)
- `--model`: Model to use for generation (default: 'meta-llama/llama-3.3-70b-instruct')
- `--log-level`: Logging level (choices: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO)
- `--start-step`: Step to start from (1/ideas, 2/requirements, 3/code, 4/dependencies)

### Configuration File

The tool supports configuration through a JSON file. The tool looks for configuration files in the following order:

1. Custom config file path specified via command line (`--config path/to/config.json`)
2. `config.json` in the current working directory
3. Default config at `src/config/default_config.json`

To create a custom config file:

```bash
# Copy the default config to your current directory
cp src/config/default_config.json config.json

# Edit config.json with your settings
```

Available configuration options:

```json
{
    "openrouter": {
        "api_key": "",                              // Your OpenRouter API key
        "default_model": "openai/gpt-4o-2024-11-20", // Default LLM model to use
        "timeout": 120,                             // API request timeout in seconds
        "max_retries": 3                            // Maximum number of API request retries
    },
    "output": {
        "base_dir": "output",                       // Base directory for output files
        "ideas_filename": "ideas.json",             // Filename for generated ideas
        "dependencies_filename": "dependencies.json" // Filename for dependency analysis
    },
    "prompts": {
        "ideas": "prompts/1-spawn_ideas.txt",           // Prompt file for idea generation
        "requirements": "prompts/2-idea-to-requirements.txt", // Prompt for requirements generation
        "code": "prompts/3-write-code.txt",             // Prompt for code generation
        "dependencies": "prompts/4-collect-dependencies.txt", // Prompt for dependency collection
        "error_format": "prompts/e1-wrong_format.txt"   // Prompt for format error handling
    },
    "logging": {
        "level": "DEBUG",                           // Logging level
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s" // Log message format
    }
}
```

Configuration precedence:
1. Command line arguments
2. Environment variables (for API key)
3. Custom config file specified via --config
4. config.json in current working directory
5. Default config file (src/config/default_config.json)

## Output Structure

The tool creates a working directory (timestamped or custom-named) for each run under the output directory:
```
output/
└── working-dir/
    ├── ideas.json
    ├── requirements/
    │   └── requirements_*.txt
    ├── code/
    │   └── generated_files
    └── dependencies.json
```

## Dependencies Analysis

The tool uses LLM to analyze code files and identify frameworks used. Key features:
- All code files are processed as .txt files for consistency
- LLM analyzes the code to identify frameworks and libraries
- Tracks usage frequency of each framework
- Framework detection is language-agnostic and based on LLM analysis

Example dependencies.json:
You can see a full run output in `docs/example_output`
```json
{
    "frameworks": [
        {
            "name": "Ruby on Rails",
            "count": 2
        },
        {
            "name": "PostgreSQL",
            "count": 1
        },
        {
            "name": "Vue.js",
            "count": 1
        }
    ]
}
```

The dependency analysis process:
1. Code files are read as text
2. Each file is analyzed by the LLM to extract a list of frameworks
3. Results are aggregated and framework counts are updated
4. Final results are saved in dependencies.json

## Development

1. Install development dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest
```

3. Run linting:
```bash
flake8 src tests
black src tests
mypy src tests
```

4. Guidelines for AI Coding Agents
Ensure the Coding Agent uses the [AI Rules and Guidelines](docs/AI_RULES_AND_GUIDELINES.md) in every request
