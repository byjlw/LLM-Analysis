# LLM ANALYSIS

## 1. Project Overview
This project provides tools for analyzing various aspects of LLM model outputs, with the current focus on analyzing code dependencies to determine which frameworks are being used by coding requests.

## 2. Technical Details and Architecture
[DESIGN_DETAILS.md for full details](DESIGN_DETAILS.md)

### 2.1 Core Concepts
* Python-based CLI tool for analyzing LLM outputs
* 4-stage pipeline:
  1. Generate product ideas
  2. Convert ideas to requirements  
  3. Generate code implementations
  4. Analyze framework dependencies
* See [Core Components in DESIGN_DETAILS.md](DESIGN_DETAILS.md#core-components) for implementation details

### 2.2 Key Features
* Flexible pipeline entry - start from any stage
* Configurable LLM model selection
* Language-agnostic framework detection
* Structured output format
* Error correction for malformed LLM responses

For details on:
* CLI options and configuration: See [Command Line Interface](DESIGN_DETAILS.md#1-command-line-interface-srcclipy)
* Data formats and file structure: See [Processing Pipeline](DESIGN_DETAILS.md#2-processing-pipeline)
* Error handling approach: See [Error Handling](DESIGN_DETAILS.md#error-handling)

## 3 Roadmap

* Report on what APIs and submodules are being used
* Parallel requests to the LLM to speed things up
* Better scaling for idea generation
* Single command to compare frameworks used across an array of LLMs
* Additional analysis types beyond code dependencies
