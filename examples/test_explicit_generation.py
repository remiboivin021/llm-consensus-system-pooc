"""
Exemple explicite pour créer un web scraper avec extraction garantie des fichiers.

Ce script montre comment utiliser correctement le code_generation tool
pour s'assurer que TOUS les fichiers sont réellement créés.
"""

import os
from pathlib import Path
from crewai import Agent, Task, Crew
from crewai_consensus_agent import (
    ConsensusConfig,
    ProjectConfig,
    create_consensus_agent,
)


def create_web_scraper_explicit():
    """
    Crée un web scraper en forçant l'utilisation explicite du code_generation tool.
    """
    print("=" * 80)
    print("Création Web Scraper avec Extraction Explicite")
    print("=" * 80)
    print()
    
    agent = create_consensus_agent()
    
    # Tâche TRÈS explicite qui force l'utilisation du bon outil
    task = Task(
        description="""
        Create a web scraper project by using the code_generation tool MULTIPLE times.
        
        Project name: web-scraper-v2
        
        IMPORTANT: You MUST use the code_generation tool for EACH component.
        DO NOT just create empty directories.
        
        Step 1: Generate the parser
        - Use code_generation tool with:
          * prompt: "Create a BeautifulSoup-based HTML parser in Python. The parser should have methods to extract titles, links, and text content. Include type hints and docstrings. Return JSON format with 'files' array containing: parser.py with the DocumentParser class. Use this exact JSON format: {\"files\": [{\"filename\": \"parser.py\", \"code\": \"...\"}], \"description\": \"...\"}"
          * project_name: "web-scraper-v2"
          * file_path: "scraper/core/parser.py"
        
        Step 2: Generate the fetcher
        - Use code_generation tool with:
          * prompt: "Create an HTTP fetcher using httpx with retry logic, timeout handling, and rate limiting. Include type hints and error handling. Return JSON format with 'files' array containing: fetcher.py with the HTTPFetcher class. Use this exact JSON format: {\"files\": [{\"filename\": \"fetcher.py\", \"code\": \"...\"}], \"description\": \"...\"}"
          * project_name: "web-scraper-v2"
          * file_path: "scraper/core/fetcher.py"
        
        Step 3: Generate the models
        - Use code_generation tool with:
          * prompt: "Create Pydantic models for Page (url, title, content, links, metadata). Include validators. Return JSON format with 'files' array containing: page.py. Use this exact JSON format: {\"files\": [{\"filename\": \"page.py\", \"code\": \"...\"}], \"description\": \"...\"}"
          * project_name: "web-scraper-v2"
          * file_path: "scraper/models/page.py"
        
        Step 4: Generate the CLI
        - Use code_generation tool with:
          * prompt: "Create a CLI using typer for web scraping with options for URL, output format (json/csv), and max pages. Return JSON format with 'files' array. Use this exact JSON format: {\"files\": [{\"filename\": \"cli.py\", \"code\": \"...\"}], \"description\": \"...\"}"
          * project_name: "web-scraper-v2"
          * file_path: "scraper/cli.py"
        
        Step 5: Generate the tests
        - Use code_generation tool with:
          * prompt: "Create pytest tests for the HTML parser with fixtures and multiple test cases. Return JSON format with 'files' array. Use this exact JSON format: {\"files\": [{\"filename\": \"test_parser.py\", \"code\": \"...\"}], \"description\": \"...\"}"
          * project_name: "web-scraper-v2"
          * file_path: "tests/test_parser.py"
        
        Step 6: Create requirements.txt using file_system tool
        - Use file_system tool with:
          * operation: "create_file"
          * project_name: "web-scraper-v2"
          * path: "requirements.txt"
          * content: "beautifulsoup4>=4.12.0\\nhttpx>=0.27.0\\npydantic>=2.0.0\\ntyper>=0.9.0\\npytest>=8.0.0"
        
        Step 7: Create README.md using file_system tool
        - Use file_system tool with:
          * operation: "create_file"
          * project_name: "web-scraper-v2"
          * path: "README.md"
          * content: "# Web Scraper\\n\\nA Python web scraper with BeautifulSoup, httpx, and CLI interface.\\n\\n## Installation\\n\\npip install -r requirements.txt\\n\\n## Usage\\n\\npython -m scraper.cli --url https://example.com"
        
        After ALL files are created, use file_system tool to list them:
        - operation: "list"
        - project_name: "web-scraper-v2"
        - path: "."
        """,
        agent=agent,
        expected_output="All 7 files created and verified in ~/workspace/web-scraper-v2/",
    )
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    
    print("🚀 Lancement...")
    print()
    
    result = crew.kickoff()
    
    print()
    print("=" * 80)
    print("Résultat de CrewAI:")
    print("=" * 80)
    print(result)
    
    # Vérification manuelle
    verify_files("web-scraper-v2")


def create_simple_calculator():
    """
    Exemple plus simple: créer juste une calculatrice.
    """
    print("=" * 80)
    print("Création Calculatrice Simple")
    print("=" * 80)
    print()
    
    agent = create_consensus_agent()
    
    task = Task(
        description="""
        Create a calculator project using code_generation tool ONCE.
        
        Use code_generation tool with these EXACT parameters:
        - prompt: "Create a Python calculator with add, subtract, multiply, divide functions AND unit tests using pytest. Return in JSON format with 'files' array containing TWO files: calculator.py and test_calculator.py. Use this EXACT format: {\"files\": [{\"filename\": \"calculator.py\", \"code\": \"def add(a, b):\\\\n    return a + b\\\\n\\\\ndef subtract(a, b):\\\\n    return a - b\\\\n\\\\ndef multiply(a, b):\\\\n    return a * b\\\\n\\\\ndef divide(a, b):\\\\n    if b == 0:\\\\n        raise ValueError('Division by zero')\\\\n    return a / b\"}, {\"filename\": \"test_calculator.py\", \"code\": \"import pytest\\\\nfrom calculator import add, subtract, multiply, divide\\\\n\\\\ndef test_add():\\\\n    assert add(2, 3) == 5\\\\n\\\\ndef test_subtract():\\\\n    assert subtract(5, 3) == 2\\\\n\\\\ndef test_multiply():\\\\n    assert multiply(4, 3) == 12\\\\n\\\\ndef test_divide():\\\\n    assert divide(10, 2) == 5\\\\n\\\\ndef test_divide_by_zero():\\\\n    with pytest.raises(ValueError):\\\\n        divide(10, 0)\"}], \"description\": \"Simple calculator with tests\"}"
        - project_name: "simple-calculator"
        - file_path: "output.json"
        
        Then use file_system tool to verify:
        - operation: "list"
        - project_name: "simple-calculator"
        - path: "."
        """,
        agent=agent,
        expected_output="Calculator with 2 files created",
    )
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    
    print()
    print("Résultat:", result)
    
    verify_files("simple-calculator")


def verify_files(project_name: str):
    """Vérifie manuellement que les fichiers ont été créés."""
    print()
    print("=" * 80)
    print(f"Vérification Manuelle: {project_name}")
    print("=" * 80)
    
    project_config = ProjectConfig()
    project_path = project_config.get_project_path(project_name)
    
    if not project_path.exists():
        print(f"❌ Le projet n'existe pas: {project_path}")
        return
    
    print(f"✓ Projet existe: {project_path}")
    print()
    
    # Lister tous les fichiers
    files = list(project_path.rglob("*"))
    py_files = [f for f in files if f.suffix == ".py"]
    other_files = [f for f in files if f.is_file() and f.suffix != ".py"]
    dirs = [f for f in files if f.is_dir()]
    
    print(f"📊 Statistiques:")
    print(f"   Fichiers Python: {len(py_files)}")
    print(f"   Autres fichiers: {len(other_files)}")
    print(f"   Dossiers: {len(dirs)}")
    print()
    
    if py_files:
        print("🐍 Fichiers Python:")
        for file in sorted(py_files):
            rel_path = file.relative_to(project_path)
            size = file.stat().st_size
            lines = len(file.read_text().split('\n'))
            print(f"   ✓ {rel_path} ({size} bytes, {lines} lines)")
    else:
        print("❌ Aucun fichier Python trouvé!")
    
    if other_files:
        print()
        print("📄 Autres fichiers:")
        for file in sorted(other_files):
            rel_path = file.relative_to(project_path)
            size = file.stat().st_size
            print(f"   ✓ {rel_path} ({size} bytes)")
    
    if dirs:
        print()
        print("📁 Dossiers:")
        for dir in sorted(dirs):
            rel_path = dir.relative_to(project_path)
            print(f"   📁 {rel_path}/")
    
    # Afficher la structure en arbre
    print()
    print("🌳 Structure:")
    print_tree(project_path, project_path)


def print_tree(path: Path, root: Path, prefix: str = ""):
    """Affiche l'arborescence des fichiers."""
    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{item.name}")
        
        if item.is_dir():
            extension = "    " if is_last else "│   "
            print_tree(item, root, prefix + extension)


def direct_tool_test():
    """Test direct de l'outil sans CrewAI."""
    print("=" * 80)
    print("Test Direct du CodeGenerationTool")
    print("=" * 80)
    print()
    
    from crewai_consensus_agent import CodeGenerationTool, ConsensusConfig, ProjectConfig
    
    tool = CodeGenerationTool(
        consensus_config=ConsensusConfig(),
        project_config=ProjectConfig(),
    )
    
    print("Appel direct du consensus...")
    
    result = tool._run(
        prompt="""Create a simple hello world Python script with a main function and a test. 
        Return JSON format: {"files": [{"filename": "hello.py", "code": "def hello():\\n    return 'Hello, World!'\\n\\nif __name__ == '__main__':\\n    print(hello())"}, {"filename": "test_hello.py", "code": "from hello import hello\\n\\ndef test_hello():\\n    assert hello() == 'Hello, World!'"}], "description": "Simple hello world"}""",
        project_name="direct-test",
        file_path="output.json"
    )
    
    print()
    print("Résultat de l'outil:")
    print(result)
    print()
    
    verify_files("direct-test")


def main():
    """Menu."""
    examples = {
        "1": ("Web Scraper Explicite (recommandé)", create_web_scraper_explicit),
        "2": ("Calculatrice Simple", create_simple_calculator),
        "3": ("Test Direct de l'Outil", direct_tool_test),
    }
    
    print("\n" + "🔧 " * 20)
    print("Tests d'Extraction avec Vérification")
    print("🔧 " * 20)
    print()
    
    print("Exemples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  q. Quitter")
    print()
    
    choice = input("Choisissez: ").strip()
    
    if choice.lower() == 'q':
        return
    
    if choice in examples:
        _, func = examples[choice]
        print()
        func()
    else:
        print(f"Choix invalide: {choice}")


if __name__ == "__main__":
    main()
