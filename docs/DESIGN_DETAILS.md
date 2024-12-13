# LLM Analysis Design Details

## System Architecture

## Overview

The LLM Analysis tool analyzes code dependencies in LLM outputs through a 4-stage pipeline:

1. Generate product ideas
2. Convert ideas to requirements
3. Generate code implementations
4. Analyze framework dependencies

## Core Components

### 1. Command Line Interface (`src/cli.py`)

The CLI provides the `coding-dependencies` command with options:
- `--api-key`: OpenRouter API key
- `--output-dir`: Output directory (default: 'output')
- `--working-dir`: Custom directory name (defaults to timestamp)
- `--num-ideas`: Number of ideas to generate (default: 15)
- `--model`: LLM model to use (default: 'meta-llama/llama-3.3-70b-instruct')
- `--start-step`: Which pipeline stage to start from (1-4)

### 2. Processing Pipeline

#### IdeaGenerator (`src/processors/idea_generator.py`)
- Uses LLM to generate product ideas in structured JSON format:
```json
{
    "Product Idea": "AI-powered investment advisor",
    "Problem it solves": "Provides personalized investment recommendations",
    "Software Techstack": ["Python", "Django", "Redis", "React"],
    "Target hardware expectations": ["Web browsers", "Mobile devices"],
    "Company profile": "Fintech",
    "Engineering profile": "Web and data engineers"
}
```
- Validates all required fields are present
- Ensures techstack and hardware expectations are proper lists
- Supports batch generation with automatic retry for format errors
- Uses conversation history to maintain context between batches
- Uses configurable prompts for both initial generation and requesting more items

#### RequirementAnalyzer (`src/processors/requirement_analyzer.py`) 
- Takes each idea and generates detailed requirements
- Creates individual requirement files named after each product
- Maintains mapping between requirements and source ideas
- Stores all requirements in `/requirements` directory
- Implements parallel processing for handling multiple ideas simultaneously
- Includes robust error handling for each parallel task

#### CodeGenerator (`src/processors/code_generator.py`)
- Generates code implementation for each set of requirements
- Uses normalized filenames to maintain traceability
- Stores all generated code as .txt files in `/code` directory
- Maps code files back to their requirements and ideas
- Processes multiple requirements in parallel using ThreadPoolExecutor
- Includes comprehensive logging for parallel execution status

#### DependencyCollector (`src/processors/dependency_collector.py`)
- Analyzes code files to identify frameworks used
- Uses LLM to extract framework names from code
- Tracks usage frequency of each framework
- Processes multiple code files in parallel for improved performance
- Aggregates results from parallel analysis into a unified counter
- Outputs normalized dependency data:
```json
{
    "frameworks": [
        {
            "name": "django",
            "count": 2
        },
        {
            "name": "react",
            "count": 3
        }
    ]
}
```

### 3. Supporting Components

#### OpenRouter Integration (`src/utils/openrouter.py`)
- Handles all LLM API communication
- Manages API authentication and retries
- Default model: meta-llama/llama-3.3-70b-instruct
- Configurable timeout and retry settings

#### File Management (`src/utils/file_handler.py`)
- Creates timestamped output directories
- Manages JSON serialization/deserialization
- Maintains consistent file structure:
```
output/
└── [timestamp]/
    ├── ideas.json
    ├── requirements/
    │   └── requirements_[product_name].txt
    ├── code/
    │   └── [product_name].txt
    └── dependencies.json
```

#### Prompt Processing (`src/utils/process_prompts.py`)
- Handles LLM prompt construction and response processing
- Implements robust JSON cleaning and validation
- Supports conversation history for context maintenance
- Provides specialized functions for each pipeline stage:
  * generate_ideas: Handles batch generation with format validation
  * generate_requirements: Processes individual requirements
  * generate_code: Manages code generation with max token limits
  * generate_dependencies: Analyzes code for framework usage
- Includes comprehensive error handling and retry logic
- Validates JSON structure and data types
- Cleans and extracts JSON from raw responses

### 4. Configuration System

Configuration is loaded in order of precedence:
1. Command line arguments
2. Environment variables (OPENROUTER_API_KEY)
3. Custom config file (--config)
4. Local config.json
5. Default config (src/config/default_config.json)

Key configuration options:
```json
{
    "openrouter": {
        "api_key": "",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "timeout": 120,
        "max_retries": 3
    },
    "output": {
        "base_dir": "output",
        "ideas_filename": "ideas.json",
        "dependencies_filename": "dependencies.json"
    },
    "prompts": {
        "ideas": "prompts/1-spawn_ideas.txt",
        "requirements": "prompts/2-idea-to-requirements.txt",
        "code": "prompts/3-write-code.txt",
        "dependencies": "prompts/4-collect-dependencies.txt",
        "error_format": "prompts/e1-wrong_format.txt",
        "more_items": "prompts/m1-num_more_items.txt"
    }
}
```

## Dependencies

The project has minimal dependencies:
- Python 3.10+
- requests>=2.31.0 (for OpenRouter API communication)

Development dependencies:
- pytest (testing)
- flake8 (linting)
- black (formatting)
- mypy (type checking)

## Error Handling

The tool uses comprehensive error handling throughout:
- Validates LLM responses match expected formats
- Uses error correction prompts for malformed responses
- Maintains traceability between pipeline stages
- Allows restarting from any stage if errors occur
- Includes parallel execution error handling
- Provides detailed logging at all stages

## Key Design Decisions

1. **Parallel Processing**: All processors support parallel execution for improved performance

2. **Text-Based Code Storage**: All generated code is stored as .txt files for consistency and easier LLM processing

3. **Normalized Naming**: Uses normalized product names throughout the pipeline to maintain relationships between ideas, requirements, and code

4. **Flexible Entry Points**: Can start processing from any pipeline stage using existing files

5. **Stateless Processing**: Each stage operates independently using files from previous stages

6. **Framework Detection**: Uses LLM analysis rather than regex/parsing to identify frameworks, making it language-agnostic

7. **Robust Error Handling**: Comprehensive error handling and validation at each stage

8. **Detailed Logging**: Extensive logging throughout the system for debugging and monitoring

9. **Configurable Prompts**: All prompts including more_items are configurable through the configuration system
