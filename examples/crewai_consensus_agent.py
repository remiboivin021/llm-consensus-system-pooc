"""
CrewAI Agent with LLM Consensus Integration

This module provides a CrewAI agent that uses the LLM consensus system
for enhanced decision-making and code generation capabilities.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from crewai import Agent, Crew, Task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ConsensusConfig(BaseModel):
    """Configuration for LLM consensus API."""
    api_url: str = Field(default="http://localhost:8000/v1/consensus")
    models: List[str] = Field(default_factory=lambda: [
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "liquid/lfm-2.5-1.2b-thinking:free",
        "tngtech/deepseek-r1t2-chimera:free"

    ])
    mode: str = Field(default="majority")
    include_raw: bool = Field(default=True)
    normalize_output: bool = Field(default=False)
    include_scores: bool = Field(default=True)
    timeout: int = Field(default=60)


class LLMConsensusClient:
    """Client for interacting with the LLM consensus API."""
    
    def __init__(self, config: ConsensusConfig):
        self.config = config
        self.client = httpx.Client(timeout=config.timeout)
    
    def query(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Query the LLM consensus API.
        
        Args:
            prompt: The prompt to send to the models
            **kwargs: Additional parameters to override config
            
        Returns:
            Dictionary containing consensus result
        """
        payload = {
            "prompt": prompt,
            "models": kwargs.get("models", self.config.models),
            "mode": kwargs.get("mode", self.config.mode),
            "include_raw": kwargs.get("include_raw", self.config.include_raw),
            "normalize_output": kwargs.get("normalize_output", self.config.normalize_output),
            "include_scores": kwargs.get("include_scores", self.config.include_scores),
        }
        
        response = self.client.post(self.config.api_url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_winner_content(self, prompt: str, **kwargs) -> str:
        """
        Get the content from the winning model.
        
        Args:
            prompt: The prompt to send to the models
            **kwargs: Additional parameters
            
        Returns:
            Content from the winning model
        """
        result = self.query(prompt, **kwargs)
        
        if not result.get("winner"):
            raise ValueError("No winner determined by consensus")
        
        winner_model = result["winner"]
        
        # Find the winning response
        for response in result.get("responses", []):
            if response["model"] == winner_model:
                return response.get("content", "")
        
        raise ValueError(f"Winner model {winner_model} not found in responses")
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()


class ProjectConfig(BaseModel):
    """Configuration for project workspace."""
    workspace_root: Path = Field(default_factory=lambda: "~/workspaces")
    create_workspace: bool = Field(default=True)
    
    def get_project_path(self, project_name: str) -> Path:
        """Get the full path for a project."""
        return self.workspace_root / project_name
    
    def ensure_workspace(self):
        """Ensure the workspace directory exists."""
        if self.create_workspace:
            self.workspace_root.mkdir(parents=True, exist_ok=True)


class FileSystemToolInput(BaseModel):
    """Input schema for FileSystemTool."""
    operation: str = Field(description="Operation: 'create_file', 'create_dir', or 'list'")
    project_name: str = Field(description="Name of the project")
    path: str = Field(description="Relative path within project")
    content: str = Field(default="", description="File content (for create_file)")


class FileSystemTool(BaseTool):
    """Tool for file system operations."""
    
    name: str = "file_system"
    description: str = "Create files and directories in the workspace"
    args_schema: type[BaseModel] = FileSystemToolInput
    
    def __init__(self, project_config: Optional[ProjectConfig] = None, **data):
        super().__init__(**data)
        # Store as private attribute to avoid Pydantic validation
        object.__setattr__(self, '_project_config', project_config or ProjectConfig())
    
    def _run(self, operation: str, project_name: str, path: str, content: str = "") -> str:
        """Execute file system operation."""
        project_config = object.__getattribute__(self, '_project_config')
        project_config.ensure_workspace()
        project_path = project_config.get_project_path(project_name)
        target_path = project_path / path
        
        if operation == "create_dir":
            target_path.mkdir(parents=True, exist_ok=True)
            return f"Created directory: {target_path}"
        
        elif operation == "create_file":
            if not content:
                return "Error: content required for create_file operation"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content)
            return f"Created file: {target_path}"
        
        elif operation == "list":
            if not target_path.exists():
                return f"Path does not exist: {target_path}"
            if target_path.is_file():
                return f"File: {target_path}"
            items = [str(p.relative_to(project_path)) for p in target_path.rglob("*")]
            return f"Contents of {target_path}:\n" + "\n".join(items)
        
        else:
            return f"Unknown operation: {operation}"


class GitHubToolInput(BaseModel):
    """Input schema for GitHubTool."""
    operation: str = Field(description="Operation: 'init', 'create_repo', 'commit', 'push', 'create_issue'")
    project_name: str = Field(description="Name of the project")
    message: str = Field(default="", description="Commit message or issue title")
    description: str = Field(default="", description="Issue description")
    repo_name: str = Field(default="", description="GitHub repository name")
    private: bool = Field(default=False, description="Make repository private")


class GitHubTool(BaseTool):
    """Tool for GitHub operations."""
    
    name: str = "github"
    description: str = "Create repositories, issues, commit and push code"
    args_schema: type[BaseModel] = GitHubToolInput
    
    def __init__(self, project_config: Optional[ProjectConfig] = None, **data):
        super().__init__(**data)
        # Store as private attribute to avoid Pydantic validation
        object.__setattr__(self, '_project_config', project_config or ProjectConfig())
    
    def _run(
        self,
        operation: str,
        project_name: str,
        message: str = "",
        description: str = "",
        repo_name: str = "",
        private: bool = False,
    ) -> str:
        """Execute GitHub operation."""
        project_config = object.__getattribute__(self, '_project_config')
        project_config.ensure_workspace()
        project_path = project_config.get_project_path(project_name)
        
        if not project_path.exists():
            return f"Error: Project path does not exist: {project_path}"
        
        try:
            if operation == "init":
                subprocess.run(["git", "init"], cwd=project_path, check=True)
                return f"Initialized git repository in {project_path}"
            
            elif operation == "create_repo":
                if not repo_name:
                    repo_name = project_name
                visibility = "--private" if private else "--public"
                result = subprocess.run(
                    ["gh", "repo", "create", repo_name, visibility, "--source", ".", "--push"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    return f"Error creating repository: {result.stderr}"
                return f"Created repository: {repo_name}\n{result.stdout}"
            
            elif operation == "commit":
                if not message:
                    message = "Auto-commit from CrewAI agent"
                subprocess.run(["git", "add", "."], cwd=project_path, check=True)
                subprocess.run(["git", "commit", "-m", message], cwd=project_path, check=True)
                return f"Committed changes: {message}"
            
            elif operation == "push":
                result = subprocess.run(
                    ["git", "push"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    return f"Error pushing: {result.stderr}"
                return f"Pushed to remote\n{result.stdout}"
            
            elif operation == "create_issue":
                if not message:
                    return "Error: message (title) required for create_issue"
                cmd = ["gh", "issue", "create", "--title", message]
                if description:
                    cmd.extend(["--body", description])
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    return f"Error creating issue: {result.stderr}"
                return f"Created issue: {message}\n{result.stdout}"
            
            else:
                return f"Unknown operation: {operation}"
        
        except subprocess.CalledProcessError as e:
            return f"Command failed: {e}"
        except FileNotFoundError as e:
            return f"Command not found (is git/gh installed?): {e}"


class LLMConsensusToolInput(BaseModel):
    """Input schema for LLMConsensusTool."""
    prompt: str = Field(description="The prompt to send to the LLM consensus system")
    include_scores: bool = Field(default=True, description="Include quality scores")
    normalize_output: bool = Field(default=False, description="Normalize output format")


class LLMConsensusTool(BaseTool):
    """Tool for querying the LLM consensus system."""
    
    name: str = "llm_consensus"
    description: str = "Query multiple LLMs and get consensus-based results"
    args_schema: type[BaseModel] = LLMConsensusToolInput
    
    def __init__(self, consensus_config: ConsensusConfig, **data):
        super().__init__(**data)
        # Store as private attribute to avoid Pydantic validation
        object.__setattr__(self, '_consensus_client', LLMConsensusClient(consensus_config))
    
    def _run(
        self,
        prompt: str,
        include_scores: bool = True,
        normalize_output: bool = False,
    ) -> str:
        """Query the LLM consensus system."""
        try:
            consensus_client = object.__getattribute__(self, '_consensus_client')
            result = consensus_client.query(
                prompt=prompt,
                include_scores=include_scores,
                normalize_output=normalize_output,
            )
            
            output = f"Winner: {result['winner']}\n"
            output += f"Confidence: {result['confidence']:.2f}\n"
            output += f"Method: {result['method']}\n"
            
            if result.get('score_stats'):
                stats = result['score_stats']
                output += f"\nQuality Scores:\n"
                output += f"  Mean: {stats['mean']:.2f}\n"
                output += f"  Min: {stats['min']:.2f}\n"
                output += f"  Max: {stats['max']:.2f}\n"
            
            # Get winner content
            for response in result.get('responses', []):
                if response['model'] == result['winner']:
                    output += f"\nWinner Content:\n{response['content']}\n"
                    break
            
            return output
        
        except Exception as e:
            return f"Error querying consensus system: {str(e)}"


class CodeGenerationToolInput(BaseModel):
    """Input schema for CodeGenerationTool."""
    prompt: str = Field(description="Description of the code to generate")
    project_name: str = Field(description="Name of the project")
    file_path: str = Field(description="Relative path for the generated file")


class CodeGenerationTool(BaseTool):
    """Tool for generating code using LLM consensus."""
    
    name: str = "code_generation"
    description: str = "Generate code files using LLM consensus and save to project (automatically extracts files from JSON response)"
    args_schema: type[BaseModel] = CodeGenerationToolInput
    
    def __init__(self, consensus_config: ConsensusConfig, project_config: Optional[ProjectConfig] = None, **data):
        super().__init__(**data)
        # Store as private attributes to avoid Pydantic validation
        object.__setattr__(self, '_consensus_client', LLMConsensusClient(consensus_config))
        object.__setattr__(self, '_project_config', project_config or ProjectConfig())
    
    def _decode_escapes(self, code: str) -> str:
        """Décode les échappements dans le code (\\n -> newline, etc.)."""
        try:
            return code.encode('utf-8').decode('unicode_escape')
        except Exception:
            return code
    
    def _extract_files_from_json(self, content: str) -> tuple[list, str]:
        """
        Extrait les fichiers depuis le JSON retourné par le consensus.
        
        Format attendu:
        {
          "files": [
            {"filename": "...", "code": "..."},
            ...
          ],
          "description": "..."
        }
        
        Returns:
            (files, description)
        """
        import json
        
        try:
            data = json.loads(content)
            files = data.get("files", [])
            description = data.get("description", "")
            return files, description
        except json.JSONDecodeError:
            # Si ce n'est pas du JSON, traiter comme du code simple
            return [], ""
    
    def _run(self, prompt: str, project_name: str, file_path: str) -> str:
        """Generate code and save to file."""
        try:
            consensus_client = object.__getattribute__(self, '_consensus_client')
            project_config = object.__getattribute__(self, '_project_config')
            
            # Get code from consensus
            content = consensus_client.get_winner_content(
                prompt=prompt,
                include_scores=True,
                normalize_output=False,
            )
            
            # Tenter d'extraire les fichiers du JSON
            files, description = self._extract_files_from_json(content)
            
            project_config.ensure_workspace()
            project_path = project_config.get_project_path(project_name)
            
            if files:
                # Format JSON avec plusieurs fichiers - extraire chacun
                created_files = []
                for file_info in files:
                    if not isinstance(file_info, dict):
                        continue
                    
                    filename = file_info.get("filename")
                    code = file_info.get("code")
                    
                    if not filename or not code:
                        continue
                    
                    # Décoder les échappements
                    decoded_code = self._decode_escapes(code)
                    
                    # Créer le fichier
                    target_path = project_path / filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(decoded_code)
                    created_files.append(str(target_path))
                
                if created_files:
                    result = f"✅ Extracted and created {len(created_files)} files from consensus:\n"
                    for fp in created_files:
                        result += f"  - {fp}\n"
                    if description:
                        result += f"\nDescription: {description}\n"
                    return result
                else:
                    # Fallback: sauvegarder le JSON brut
                    target_path = project_path / file_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content)
                    return f"⚠️  No files extracted from JSON. Saved raw response to: {target_path}"
            else:
                # Pas de format JSON - sauvegarder tel quel
                target_path = project_path / file_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content)
                return f"Generated code saved to: {target_path}"
        
        except Exception as e:
            return f"Error generating code: {str(e)}"


# --- BDAM helper -----------------------------------------------------------------

def bdam_guidance(project_description: str) -> str:
    """
    KISS/YAGNI-friendly BDAM frame used by the agent to plan projects.

    B = Brief      : reformulate the goal, constraints, success criteria.
    D = Decompose  : list minimal deliverables and steps.
    A = Act        : execute steps (code gen, files) defensively; fail soft where possible.
    M = Measure    : define quick checks (tests, lint, file existence) to validate output.
    """
    return (
        "Apply the BDAM method:\n"
        "B/Brief: restate the objective and constraints succinctly.\n"
        "D/Decompose: list the smallest steps/files needed (avoid gold plating).\n"
        "A/Act: execute steps in order, use defensive defaults, and keep outputs minimal.\n"
        "M/Measure: propose quick checks (tests or file presence) confirming success.\n"
        f"Project: {project_description}\n"
    )


def create_consensus_agent(
    consensus_config: Optional[ConsensusConfig] = None,
    project_config: Optional[ProjectConfig] = None,
) -> Agent:
    """
    Create a CrewAI agent with LLM consensus integration.
    
    Args:
        consensus_config: Configuration for LLM consensus API
        project_config: Configuration for project workspace
        
    Returns:
        Configured CrewAI Agent
    
    Note:
        Requires OPENROUTER_API_KEY environment variable for the agent's LLM.
        The agent uses this LLM for planning, while using the consensus system for code generation.
    """
    if consensus_config is None:
        consensus_config = ConsensusConfig()
    
    if project_config is None:
        project_config = ProjectConfig()
    
    # Create tools
    tools = [
        FileSystemTool(project_config=project_config),
        GitHubTool(project_config=project_config),
        LLMConsensusTool(consensus_config=consensus_config),
        CodeGenerationTool(
            consensus_config=consensus_config,
            project_config=project_config,
        ),
    ]
    
    # Configure LLM via OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if not openrouter_key:
        raise ValueError(
            "OPENROUTER_API_KEY is required for the CrewAI agent.\n\n"
            "Please set the environment variable:\n"
            "  export OPENROUTER_API_KEY='sk-or-v1-...'\n\n"
            "Get your free key at: https://openrouter.ai/keys\n\n"
            "Note: This is for the agent's planning LLM. Your consensus system\n"
            "can use free models, but the agent needs a capable model for coordination.\n\n"
            "Recommended models for the agent:\n"
            "  - anthropic/claude-3.5-sonnet (best quality)\n"
            "  - openai/gpt-4o-mini (good balance)\n"
            "  - google/gemini-pro-1.5 (alternative)\n"
        )
    
    # Use OpenRouter with a good model for the agent
    # The agent needs a capable model for planning and coordination
    agent_model = "tngtech/deepseek-r1t2-chimera:free" #os.getenv("AGENT_MODEL", "anthropic/claude-3.5-sonnet")
    
    # LiteLLM format for OpenRouter: "openrouter/provider/model"
    # Set OpenRouter API key as OPENROUTER_API_KEY environment variable
    os.environ["OPENROUTER_API_KEY"] = openrouter_key
    
    from crewai import LLM
    
    # Use LiteLLM's OpenRouter integration
    agent_llm = LLM(
        model=f"{agent_model}",
    )
    
    agent = Agent(
        role="Senior Software Engineer with LLM Consensus",
        goal="Create high-quality software projects using consensus from multiple LLMs",
        backstory="""You are an expert software engineer who leverages the wisdom of 
        multiple AI models to make informed decisions. You create projects in the 
        ~/workspace directory, manage GitHub repositories, and ensure all code meets 
        high quality standards through consensus-based development.""",
        tools=tools,
        verbose=True,
        allow_delegation=False,
        llm=agent_llm,
    )
    
    return agent


def create_project_crew(
    agent: Agent,
    project_description: str,
    project_name: str,
) -> Crew:
    """
    Create a CrewAI crew for project generation.
    
    Args:
        agent: The consensus agent
        project_description: Description of the project to create
        project_name: Name of the project
        
    Returns:
        Configured CrewAI Crew
    """
    bdam = bdam_guidance(project_description)

    tasks = [
        Task(
            description=f"""
            Create a new software project: {project_description}
            Project name: {project_name}

            {bdam}

            Operational constraints:
            - Always initialize git on branch 'main' and set remote origin via gh.
            - Copy any available .github/ISSUE_TEMPLATE/ into the new repo.
            - Use the code_generation tool for files; keep outputs minimal (KISS/YAGNI).
            - Prefer defensive checks; if a step fails, continue with best-effort and report.
            """,
            agent=agent,
            expected_output=f"Project created in ~/workspace/{project_name} with git on main, remote origin set, and issue templates present.",
        ),
    ]
    
    crew = Crew(
        agents=[agent],
        tasks=tasks,
        verbose=True,
    )
    
    return crew
