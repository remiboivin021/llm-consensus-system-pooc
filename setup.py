"""Setup configuration for CrewAI Consensus Agent."""

from pathlib import Path
from setuptools import setup, find_packages

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="crewai-consensus-agent",
    version="1.1.0",
    description="CrewAI agent with LLM consensus integration for enhanced code generation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/crewai-consensus-agent",
    packages=find_packages(),
    py_modules=["crewai_consensus_agent"],
    python_requires=">=3.10",
    install_requires=[
        "crewai>=0.28.0",
        "crewai-tools>=0.4.0",
        "httpx>=0.27.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
        "litellm>=1.0.0",
        "fastapi>=0.115.0",
        "uvicorn>=0.30.0",
        "jinja2>=3.1.0",
        "python-multipart>=0.0.9",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "black>=24.0.0",
            "ruff>=0.3.0",
            "mypy>=1.9.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "crewai-consensus=examples:main",
            "product-workshop=product_workshop.main:run",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="crewai llm consensus code-generation ai agents",
)
