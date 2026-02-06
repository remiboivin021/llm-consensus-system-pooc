"""
Example usage scenarios for the CrewAI Consensus Agent.

This script demonstrates various ways to use the agent for different tasks.
"""

import os
from pathlib import Path

from crewai import Task, Crew
from crewai_consensus_agent import (
    ConsensusConfig,
    ProjectConfig,
    create_consensus_agent,
    create_project_crew,
)


def example_1_simple_project():
    """Example 1: Create a simple Python calculator project."""
    print("=" * 80)
    print("Example 1: Simple Calculator Project")
    print("=" * 80)
    
    consensus_config = ConsensusConfig(
        api_url=os.getenv("CONSENSUS_API_URL", "http://localhost:8000/v1/consensus"),
    )
    
    agent = create_consensus_agent(consensus_config=consensus_config)
    
    crew = create_project_crew(
        agent=agent,
        project_description="""
        A Python calculator library with:
        - Basic operations (add, subtract, multiply, divide)
        - Advanced operations (power, square root, factorial)
        - Comprehensive unit tests using pytest
        - Type hints and documentation
        """,
        project_name="calculator-lib",
    )
    
    result = crew.kickoff()
    print(f"\nResult: {result}")


def example_2_web_api():
    """Example 2: Create a REST API project."""
    print("=" * 80)
    print("Example 2: REST API Project")
    print("=" * 80)
    
    consensus_config = ConsensusConfig(
        api_url=os.getenv("CONSENSUS_API_URL", "http://localhost:8000/v1/consensus"),
    )
    
    agent = create_consensus_agent(consensus_config=consensus_config)
    
    tasks = [
        Task(
            description="""
            Create a FastAPI-based REST API for a book library system.
            
            Project name: book-library-api
            
            Requirements:
            1. Use llm_consensus to design the API structure
            2. Create the following files:
               - main.py (FastAPI application)
               - models.py (Pydantic models for Book)
               - database.py (SQLite database setup)
               - routes.py (API endpoints)
               - test_api.py (pytest tests)
               - requirements.txt (dependencies)
               - README.md (documentation)
            
            3. Initialize git repository
            4. Create initial commit with message "Initial commit: Book Library API"
            
            All files must be in ~/workspace/book-library-api
            """,
            agent=agent,
            expected_output="Complete REST API project with all files and git repository",
        ),
    ]
    
    crew = Crew(agents=[agent], tasks=tasks, verbose=True)
    result = crew.kickoff()
    print(f"\nResult: {result}")


def example_3_with_github():
    """Example 3: Create project and push to GitHub."""
    print("=" * 80)
    print("Example 3: Project with GitHub Integration")
    print("=" * 80)
    
    consensus_config = ConsensusConfig(
        api_url=os.getenv("CONSENSUS_API_URL", "http://localhost:8000/v1/consensus"),
    )
    
    agent = create_consensus_agent(consensus_config=consensus_config)
    
    tasks = [
        Task(
            description="""
            Create a Python data analysis toolkit and publish to GitHub.
            
            Project name: data-toolkit
            
            Steps:
            1. Use llm_consensus to plan the project structure
            2. Create the following files:
               - data_toolkit/__init__.py
               - data_toolkit/cleaner.py (data cleaning utilities)
               - data_toolkit/analyzer.py (analysis functions)
               - tests/test_cleaner.py
               - tests/test_analyzer.py
               - setup.py
               - README.md
               - .gitignore
            
            3. Initialize git repository
            4. Create initial commit
            5. Create GitHub repository (public)
            6. Push to GitHub
            7. Create an issue titled "Add visualization module"
            
            All files in ~/workspace/data-toolkit
            """,
            agent=agent,
            expected_output="Complete project pushed to GitHub with issue created",
        ),
    ]
    
    crew = Crew(agents=[agent], tasks=tasks, verbose=True)
    result = crew.kickoff()
    print(f"\nResult: {result}")


def example_4_multi_file_generation():
    """Example 4: Generate multiple related files."""
    print("=" * 80)
    print("Example 4: Multi-File Project Generation")
    print("=" * 80)
    
    consensus_config = ConsensusConfig(
        api_url=os.getenv("CONSENSUS_API_URL", "http://localhost:8000/v1/consensus"),
    )
    
    agent = create_consensus_agent(consensus_config=consensus_config)
    
    tasks = [
        Task(
            description="""
            Create a Python web scraper project with clean architecture.
            
            Project name: web-scraper
            
            Use the code_generation tool to create each file:
            
            1. scraper/core/parser.py
               Prompt: "Create a BeautifulSoup-based HTML parser with methods to extract titles, links, and text content. Include type hints and docstrings."
            
            2. scraper/core/fetcher.py
               Prompt: "Create an HTTP fetcher using httpx with retry logic, timeout handling, and rate limiting. Include type hints and error handling."
            
            3. scraper/models/page.py
               Prompt: "Create Pydantic models for Page (url, title, content, links, metadata). Include validators."
            
            4. scraper/cli.py
               Prompt: "Create a CLI using typer for web scraping with options for URL, output format (json/csv), and max pages."
            
            5. tests/test_parser.py
               Prompt: "Create pytest tests for the HTML parser with fixtures and multiple test cases."
            
            6. requirements.txt
               Content: "beautifulsoup4>=4.12.0\nhttpx>=0.27.0\npydantic>=2.0.0\ntyper>=0.9.0\npytest>=8.0.0"
            
            7. README.md
               Use llm_consensus to generate comprehensive documentation
            
            8. Initialize git and create initial commit
            
            All files in ~/workspace/web-scraper
            """,
            agent=agent,
            expected_output="Complete web scraper project with all files generated via consensus",
        ),
    ]
    
    crew = Crew(agents=[agent], tasks=tasks, verbose=True)
    result = crew.kickoff()
    print(f"\nResult: {result}")


def example_5_custom_workspace():
    """Example 5: Use custom workspace location."""
    print("=" * 80)
    print("Example 5: Custom Workspace Location")
    print("=" * 80)
    
    consensus_config = ConsensusConfig(
        api_url=os.getenv("CONSENSUS_API_URL", "http://localhost:8000/v1/consensus"),
    )
    
    # Use custom workspace location
    custom_workspace = Path.home() / "my_projects" / "ai_generated"
    project_config = ProjectConfig(
        workspace_root=custom_workspace,
        create_workspace=True,
    )
    
    agent = create_consensus_agent(
        consensus_config=consensus_config,
        project_config=project_config,
    )
    
    crew = create_project_crew(
        agent=agent,
        project_description="""
        A Python CLI tool for file organization with:
        - Automatic file categorization by extension
        - Duplicate file detection
        - Safe file moving with undo capability
        - Configuration file support
        - Full test coverage
        """,
        project_name="file-organizer",
    )
    
    result = crew.kickoff()
    print(f"\nResult: {result}")
    print(f"\nProject created in: {custom_workspace / 'file-organizer'}")


def main():
    """Run examples based on user choice."""
    examples = {
        "1": ("Simple Calculator", example_1_simple_project),
        "2": ("REST API", example_2_web_api),
        "3": ("GitHub Integration", example_3_with_github),
        "4": ("Multi-File Generation", example_4_multi_file_generation),
        "5": ("Custom Workspace", example_5_custom_workspace),
    }
    
    print("\nCrewAI Consensus Agent Examples")
    print("=" * 80)
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  q. Quit")
    
    choice = input("\nSelect an example (or 'q' to quit): ").strip()
    
    if choice.lower() == 'q':
        print("Goodbye!")
        return
    
    if choice in examples:
        _, example_func = examples[choice]
        example_func()
    else:
        print(f"Invalid choice: {choice}")


if __name__ == "__main__":
    # Check if consensus API URL is set
    if not os.getenv("CONSENSUS_API_URL"):
        print("\nWARNING: CONSENSUS_API_URL not set. Using default: http://localhost:8000/v1/consensus")
        print("Set it with: export CONSENSUS_API_URL=http://your-api:8000/v1/consensus\n")
    
    main()
