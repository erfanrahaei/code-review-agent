import typer
from git_utils import GitChangeAnalyzer

app = typer.Typer(help="CLI tool to run local code reviews before pushing code.")

@app.command()
def analyze(repo_path: str = typer.Option(".", help="Path to the git repository")):
    """
    Scans the repository for changes that are ready to be pushed but are not yet on the remote.
    """
    typer.echo("Searching for unpushed changes...")
    
    try:
        analyzer = GitChangeAnalyzer(repo_path)
        changes = analyzer.get_unpushed_diff()
        
        if not changes:
            typer.echo("No unpushed or modified source files detected. Nothing to review.")
            raise typer.Exit()
            
        typer.echo(f"Found {len(changes)} modified file(s) to analyze:\n")
        for file_path, diff_content in changes.items():
            typer.echo(f"File: {file_path}")
            typer.echo("-" * len(file_path))
            # Display a truncated version of the diff for visual clarity in CLI
            lines = diff_content.splitlines()
            for line in lines[:10]:
                typer.echo(line)
            if len(lines) > 10:
                typer.echo(f"... ({len(lines) - 10} more lines)")
            typer.echo("\n")
            
    except Exception as e:
        typer.secho(f"Error: {str(e)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()