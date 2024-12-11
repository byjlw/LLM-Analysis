"""
Setup configuration for the LLM Analysis tool.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llm-analysis",
    version="0.1.0",
    author="Jesse White",
    description="A tool for analyzing various aspects of LLM model outputs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/byjlw/llm-analysis",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "llm-analysis=src.cli:main",
        ],
    },
    package_data={
        "src": ["config/*.json"],
    },
    include_package_data=True,
)
