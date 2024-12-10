# LLM CODING ANALYSIS

## 1. Project Overview
This project analyzes the code returned by LLM models to deterimine which frameworks are are being used by coding request

## 2. Technical Details and Architecture


### 2.1 Details
* python 3.10+
* use OpenRouter for interacting with LLMs
* default_config.json for storing model to use
* cli to kick the process off and allows for passing in models and openrouter key
* can start at any place in the pipeline by specifying the stage and working folder on the commandline
* Should use venv with .venv as the folder
* Allow for installing this project
* Each run should should result in a new folder for the output files in `/output` and should include a timestamp by default if no path is provided

## 2.2 Data Flow
1. In anitial prompt `prompts/1-spawn_ideas.txt` will be sent to openrouter to generate a json file with a list of product ideas following this format
```
[
    {
        "Product Idea": "AI-powered investment advisor",
        "Problem it solves": "Provides users with personalized investment recommendations",
        "Software Techstack": ["Python", "Django", "Redis", "React"],
        "Target hardware expectations": ["Web browsers", "Mobile devices"],
        "Company profile": "Fintech",
        "Engineering profile": "Web and data engineers"
    }
]
```
This needs to be saved to the /output folder with the filename `ideas.json`
2. Iterate through the ideas in the ideas.json file, append that item to the prompt in `prompts/2-idea-to-requirements.txt` and send it to the LLM to get the requirements
3. Append `prompts/3-write-code.txt` with the requirements received from step 2. and send it to the LLM to get the code
4. Append `prompts/4-collect-dependencies.txt` with the code received in step 3. to get the dependencies by sending the combined prompt to the LLM to receive a json list of dependencies found in the code
Like this:
```
["Ruby on Rails", "PostgreSQL", "Vue.js", "Redis", "TensorFlow", "PyTorch"]
```
5. Create or update `output/depedencies.json` with the dependencies collected in step 4. If the dependency is already in `dependencies.json` then increment the number by the dependecy following this format

```
{
  "frameworks": [
    {
      "name": "torch",
      "count": 2
    },
    {
      "name": "transformers.AutoModelForSequenceClassification",
      "count": 1
    },
    {
      "name": "transformers.AutoTokenizer",
      "count": 1
    }
  ]
}
```

## 2.3 Error Handling Phiosophy
The responses from LLMs are non-deterministic, espcially given that the user should be able to use any LLM they want.

* For LLM calls that expect a certain format you can catch conversion and processing issues and then respond back to the LLM with `prompts/e1-wrong_format.txt` to fix the format. 

# 3 Roadmap

* Report on what APIs and submodules are being used
* Parallel requests to the LLM to speed things up
* Better scaling for idea generation
* Single command to compare frameworks used across an array of LLMs
