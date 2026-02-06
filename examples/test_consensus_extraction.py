"""
Test de l'extraction automatique de fichiers depuis le consensus.

Ce script montre comment le CodeGenerationTool appelle automatiquement
le consensus ET extrait les fichiers du JSON retourné.
"""

import os
from crewai import Agent, Task, Crew
from crewai_consensus_agent import (
    ConsensusConfig,
    ProjectConfig,
    create_consensus_agent,
)


def example_with_real_consensus():
    """
    Exemple complet: l'agent appelle le consensus et extrait les fichiers automatiquement.
    """
    print("=" * 80)
    print("Test avec Vrai Consensus - Extraction Automatique")
    print("=" * 80)
    print()
    
    # Vérifier que l'API consensus est configurée
    api_url = os.getenv("CONSENSUS_API_URL", "http://localhost:8000/v1/consensus")
    print(f"API Consensus: {api_url}")
    print()
    
    # Créer l'agent
    agent = create_consensus_agent()
    
    # Créer une tâche qui utilise code_generation
    task = Task(
        description="""
        Use the code_generation tool to create a simple calculator project.
        
        Parameters:
        - prompt: "Create a Python calculator with add, subtract, multiply, divide functions. Include comprehensive unit tests using pytest. Return in JSON format with 'files' array containing 'filename' and 'code' fields."
        - project_name: "calculator-consensus"
        - file_path: "output.json"  (fallback si pas de JSON)
        
        The tool will automatically:
        1. Call the consensus API
        2. Parse the JSON response
        3. Extract all files from the "files" array
        4. Decode escape sequences (\\n, \\t, etc.)
        5. Create each file in ~/workspace/calculator-consensus/
        """,
        agent=agent,
        expected_output="Calculator project with all files extracted from consensus response",
    )
    
    # Exécuter
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    
    print("🚀 Lancement de l'agent...")
    print()
    
    result = crew.kickoff()
    
    print()
    print("=" * 80)
    print("Résultat:")
    print("=" * 80)
    print(result)
    
    # Vérifier les fichiers créés
    project_config = ProjectConfig()
    project_path = project_config.get_project_path("calculator-consensus")
    
    if project_path.exists():
        print()
        print("=" * 80)
        print("Fichiers créés:")
        print("=" * 80)
        for file in sorted(project_path.rglob("*")):
            if file.is_file():
                rel_path = file.relative_to(project_path)
                size = file.stat().st_size
                print(f"  ✓ {rel_path} ({size} bytes)")


def example_direct_tool_usage():
    """
    Exemple d'utilisation directe de l'outil (sans CrewAI).
    """
    print("\n" + "=" * 80)
    print("Test Direct de l'Outil")
    print("=" * 80)
    print()
    
    from crewai_consensus_agent import CodeGenerationTool, ConsensusConfig, ProjectConfig
    
    # Créer l'outil
    tool = CodeGenerationTool(
        consensus_config=ConsensusConfig(),
        project_config=ProjectConfig(),
    )
    
    # Utiliser l'outil directement
    print("Appel du consensus pour générer un web scraper...")
    result = tool._run(
        prompt="""Create a Python web scraper with:
        1. A parser module using BeautifulSoup
        2. A fetcher module using httpx with retry logic
        3. Unit tests for both
        Return in JSON format with 'files' array.""",
        project_name="scraper-test",
        file_path="fallback.json"
    )
    
    print()
    print("Résultat:")
    print(result)


def example_show_json_format():
    """
    Montre le format JSON attendu par le consensus.
    """
    print("\n" + "=" * 80)
    print("Format JSON Attendu du Consensus")
    print("=" * 80)
    print()
    
    example_json = """
    {
      "files": [
        {
          "filename": "calculator.py",
          "code": "def add(a, b):\\n    return a + b\\n\\ndef subtract(a, b):\\n    return a - b"
        },
        {
          "filename": "test_calculator.py",
          "code": "import pytest\\nfrom calculator import add, subtract\\n\\ndef test_add():\\n    assert add(2, 3) == 5"
        }
      ],
      "description": "Simple calculator with tests"
    }
    """
    
    print("Le consensus DOIT retourner ce format:")
    print(example_json)
    print()
    print("Points importants:")
    print("  1. ✅ Tableau 'files' avec objets {filename, code}")
    print("  2. ✅ Le champ 'code' contient le code avec \\n pour les sauts de ligne")
    print("  3. ✅ Le champ 'description' est optionnel")
    print()
    print("L'outil va automatiquement:")
    print("  1. 🔍 Détecter le format JSON")
    print("  2. 📝 Extraire chaque fichier")
    print("  3. 🔄 Décoder les \\n en vraies nouvelles lignes")
    print("  4. 💾 Créer les fichiers dans le projet")


def test_with_mock_response():
    """
    Test avec une réponse mock pour montrer le comportement.
    """
    print("\n" + "=" * 80)
    print("Test avec Réponse Simulée")
    print("=" * 80)
    print()
    
    from crewai_consensus_agent import CodeGenerationTool, ConsensusConfig, ProjectConfig
    from unittest.mock import patch
    
    # Réponse mock du consensus (comme celle que vous avez uploadée)
    mock_response = """{
  "files": [
    {
      "filename": "http_fetcher.py",
      "code": "import time\\nfrom typing import Optional, Dict, Any\\nimport httpx\\n\\nclass HTTPFetcher:\\n    def __init__(self, timeout: float = 10.0):\\n        self.timeout = timeout\\n        self.client = httpx.Client(timeout=self.timeout)\\n\\n    def fetch(self, url: str) -> httpx.Response:\\n        response = self.client.get(url)\\n        response.raise_for_status()\\n        return response\\n\\n    def close(self) -> None:\\n        self.client.close()"
    },
    {
      "filename": "test_http_fetcher.py",
      "code": "import pytest\\nfrom http_fetcher import HTTPFetcher\\n\\ndef test_successful_fetch():\\n    fetcher = HTTPFetcher()\\n    # Test mock here\\n    fetcher.close()"
    }
  ],
  "description": "HTTP client with retry logic"
}"""
    
    tool = CodeGenerationTool(
        consensus_config=ConsensusConfig(),
        project_config=ProjectConfig(),
    )
    
    # Mock le client consensus pour retourner notre réponse
    with patch.object(tool, '_consensus_client') as mock_client:
        mock_client_instance = mock_client.return_value if callable(mock_client) else mock_client
        # Accéder au vrai client
        real_client = object.__getattribute__(tool, '_consensus_client')
        real_client.get_winner_content = lambda **kwargs: mock_response
        
        print("Appel de l'outil avec réponse mock...")
        result = tool._run(
            prompt="test",
            project_name="mock-test",
            file_path="fallback.json"
        )
        
        print()
        print("Résultat:")
        print(result)
        
        # Vérifier les fichiers
        project_config = ProjectConfig()
        project_path = project_config.get_project_path("mock-test")
        
        if project_path.exists():
            print()
            print("Fichiers créés:")
            for file in sorted(project_path.rglob("*.py")):
                rel_path = file.relative_to(project_path)
                print(f"  ✓ {rel_path}")
                
                # Montrer un aperçu
                content = file.read_text()
                lines = content.split('\n')
                print(f"    {len(lines)} lignes")
                if lines:
                    print(f"    Première ligne: {lines[0]}")


def main():
    """Menu interactif."""
    examples = {
        "1": ("Test avec vrai consensus", example_with_real_consensus),
        "2": ("Test direct de l'outil", example_direct_tool_usage),
        "3": ("Voir format JSON", example_show_json_format),
        "4": ("Test avec mock", test_with_mock_response),
    }
    
    print("\n" + "🧪 " * 20)
    print("Tests d'Extraction Automatique depuis Consensus")
    print("🧪 " * 20)
    print()
    
    print("Exemples disponibles:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  q. Quitter")
    print()
    
    # Vérifier la configuration
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  OPENROUTER_API_KEY non défini")
        print("   export OPENROUTER_API_KEY='sk-or-v1-...'")
        print()
    
    if not os.getenv("CONSENSUS_API_URL"):
        print("ℹ️  CONSENSUS_API_URL non défini, utilisation de: http://localhost:8000/v1/consensus")
        print()
    
    choice = input("Choisissez un exemple: ").strip()
    
    if choice.lower() == 'q':
        print("Au revoir!")
        return
    
    if choice in examples:
        _, example_func = examples[choice]
        print()
        example_func()
    else:
        print(f"Choix invalide: {choice}")


if __name__ == "__main__":
    main()
