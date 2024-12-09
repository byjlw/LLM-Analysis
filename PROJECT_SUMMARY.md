# LLM CODING ANALYSIS

## 1. Project Overview
This project analyzes the code returned by LLM models to deterimine which models and frameworks are being used for a particular coding request and will eventually dig deeper to see how these frameworks are leveraged

## 2. Technical Details and Architecture


### 2.1
* python 3.10+
* use OpenRouter for interacting with LLMs
* default_config.json for storing model to use
* cli to kick the process off and allows for passing in models and openrouter key
* Should use venv with .venv as the folder
* Allow for installing this project
* Each run should should result in a new folder for the output files in `/output` and should include a timestamp

## 3. Data Flow
1. In anitial prompt `prompts/1-span_ideas.txt` will be sent to openrouter to generate a json file with a list of product ideas following this format
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
4. Append `prompts/4-collect-dependencies.txt` with the code received in step 3. to get the depedencies and models which will follow this structure

```
{
  "frameworks": [
    "torch",
    "transformers.AutoModelForSequenceClassification",
    "transformers.AutoTokenizer"
  ],
  "models": [
    "distilbert-base-uncased"
  ]
}
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
  ],
  "models": [
    {
      "name": "distilbert-base-uncased",
      "count": 2
    }
  ]
}
```