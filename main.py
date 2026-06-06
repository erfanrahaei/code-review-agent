import typer
import asyncio
from dotenv import load_dotenv
from git_utils import GitChangeAnalyzer
from agent_engine import ReviewEngine

# Load local .env file variables if present
load_dotenv()

app = typer.Typer(help="CLI tool to run local code reviews before pushing code.")

async def run_analysis(repo_path: str):
    analyzer = GitChangeAnalyzer(repo_path)
    changes = analyzer.get_unpushed_diff()
    
    if not changes:
        typer.echo("No unpushed or modified source files detected. Nothing to review.")
        return

    typer.echo(f"Found {len(changes)} modified file(s) to analyze. Dispatching Critic Agents...")
    
    try:
        engine = ReviewEngine()
        review_results = await engine.run_review(changes)
        
        has_feedback = False
        for file_path, feedbacks in review_results.items():
            if not feedbacks:
                continue
            
            has_feedback = True
            typer.secho(f"\n[!] Review for: {file_path}", fg=typer.colors.CYAN, bold=True)
            typer.echo("=" * (17 + len(file_path)))
            
            for item in feedbacks:
                typer.secho(f"\n{item['critic']} feedback:", fg=typer.colors.YELLOW, bold=True)
                typer.echo(item['feedback'])
        
        if not has_feedback:
            typer.secho("\nAll critics cleared your changes! No issues found.", fg=typer.colors.GREEN)
            
    except ValueError as e:
        typer.secho(f"\nConfiguration Error: {str(e)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"\nExecution Error: {str(e)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@app.command()
def analyze(repo_path: str = typer.Option(".", help="Path to the git repository")):
    """
    Scans the repository and runs the multi-agent critic engine.
    """
    asyncio.run(run_analysis(repo_path))

if __name__ == "__main__":
    app()