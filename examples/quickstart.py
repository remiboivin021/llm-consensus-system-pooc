#!/usr/bin/env python3
"""
Quick start script for CrewAI Consensus Agent

This script helps you get started quickly by:
1. Checking prerequisites
2. Setting up the environment
3. Running a simple test project
"""

import os
import subprocess
import sys
from pathlib import Path


def print_header(message):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80 + "\n")


def check_command(command, name, required=True):
    """Check if a command exists."""
    try:
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        print(f"✅ {name} is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        if required:
            print(f"❌ {name} is NOT installed (required)")
        else:
            print(f"⚠️  {name} is NOT installed (optional)")
        return False


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version >= (3, 10):
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (required: 3.10+)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (required: 3.10+)")
        return False


def check_api_running():
    """Skip API check; library ships without an HTTP server."""
    print("ℹ️  No bundled HTTP API. Build your own FastAPI app and import src.")
    return True


def setup_environment():
    """Set up environment variables."""
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file from template...")
        example_file = Path(".env.example")
        if example_file.exists():
            env_file.write_text(example_file.read_text())
            print("✅ .env file created")
        else:
            # Create basic .env
            env_file.write_text("CONSENSUS_API_URL=http://localhost:8000/v1/consensus\n")
            print("✅ .env file created with default values")
    else:
        print("✅ .env file already exists")


def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
        )
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def create_workspace():
    """Create workspace directory."""
    workspace = Path.home() / "workspace"
    if not workspace.exists():
        print(f"📁 Creating workspace directory: {workspace}")
        workspace.mkdir(parents=True, exist_ok=True)
        print("✅ Workspace created")
    else:
        print(f"✅ Workspace already exists: {workspace}")


def run_simple_test():
    """Run a simple test to verify everything works."""
    print("🧪 Running simple test...")
    
    test_code = '''
from pathlib import Path
from crewai_consensus_agent import ConsensusConfig, ProjectConfig, create_consensus_agent
from crewai import Task, Crew

# Configure
config = ConsensusConfig(api_url="http://localhost:8000/v1/consensus")
project_config = ProjectConfig(workspace_root=Path.home() / "workspace")

# Create agent
agent = create_consensus_agent(consensus_config=config, project_config=project_config)

# Create a simple task
task = Task(
    description="""
    Create a simple hello world project:
    1. Use file_system tool to create directory 'hello-world-test'
    2. Use file_system tool to create file 'main.py' with content: print('Hello from CrewAI!')
    3. Use file_system tool to list the project
    """,
    agent=agent,
    expected_output="Project created with main.py",
)

# Run
crew = Crew(agents=[agent], tasks=[task], verbose=False)
result = crew.kickoff()
print(f"\\n✅ Test completed successfully!")
print(f"Result: {result}")
'''
    
    try:
        exec(test_code)
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Main function."""
    print_header("CrewAI Consensus Agent - Quick Start")
    
    # Step 1: Check prerequisites
    print_header("Step 1: Checking Prerequisites")
    
    checks = {
        "Python 3.10+": check_python_version(),
        "git": check_command("git", "Git", required=True),
        "gh": check_command("gh", "GitHub CLI", required=False),
    }
    
    if not all([checks["Python 3.10+"], checks["git"]]):
        print("\n❌ Missing required prerequisites. Please install them and try again.")
        sys.exit(1)
    
    print("\n✅ All required prerequisites are installed!")
    
    # Step 2: Check API
    print_header("Step 2: Checking Consensus API")
    api_running = check_api_running()
    
    if not api_running:
        print("\n⚠️  Please start the consensus API before continuing:")
        print("   cd /path/to/your/consensus/project")
        print("   uvicorn sample.adapters.api.app:app --reload")
        
        response = input("\nStart the API and press Enter to continue (or 'q' to quit): ")
        if response.lower() == 'q':
            print("Exiting...")
            sys.exit(0)
        
        # Check again
        if not check_api_running():
            print("❌ API still not running. Exiting...")
            sys.exit(1)
    
    # Step 3: Setup
    print_header("Step 3: Setting Up Environment")
    setup_environment()
    
    # Step 4: Install dependencies
    print_header("Step 4: Installing Dependencies")
    if not install_dependencies():
        sys.exit(1)
    
    # Step 5: Create workspace
    print_header("Step 5: Creating Workspace")
    create_workspace()
    
    # Step 6: Run test
    print_header("Step 6: Running Test Project")
    response = input("Run a test project? (y/n): ")
    if response.lower() == 'y':
        if run_simple_test():
            print("\n🎉 Everything is working!")
            print(f"\nCheck your workspace: {Path.home() / 'workspace' / 'hello-world-test'}")
    
    # Next steps
    print_header("Next Steps")
    print("1. Run examples:")
    print("   python examples.py")
    print("")
    print("2. Create your own projects:")
    print("   - Edit examples.py or crewai_consensus_agent.py")
    print("   - Create custom agents and tasks")
    print("")
    print("3. Read the documentation:")
    print("   cat README.md")
    print("")
    print("Happy coding! 🚀")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
