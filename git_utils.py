import os
from git import Repo, Exc
from config import config

class GitChangeAnalyzer:
    def __init__(self, repo_path: str = "."):
        try:
            self.repo = Repo(repo_path, search_parent_directories=True)
        except Exc.InvalidGitRepositoryError:
            raise RuntimeError(f"The path '{repo_path}' is not a valid Git repository.")

    def get_unpushed_diff(self) -> dict[str, str]:
        """
        Retrieves the diff of unpushed commits compared to the upstream (remote) tracking branch.
        If no remote is set, it falls back to comparing with the default comparison branch (e.g., main).
        """
        active_branch = self.repo.active_branch
        tracking_branch = active_branch.tracking_branch()

        if tracking_branch:
            # Compare current local branch HEAD to the tracked remote branch
            base_ref = tracking_branch.commit
        else:
            # Fallback if no tracking branch is configured
            try:
                base_ref = self.repo.heads[config.default_comparison_branch].commit
            except IndexError:
                # If even default branch is not found, compare against the first commit
                base_ref = None

        diffs = {}
        if base_ref:
            # Get the diff between the base reference and the current HEAD
            diff_index = base_ref.diff(self.repo.head.commit)
        else:
            # If no base can be determined, grab the current working tree changes
            diff_index = self.repo.index.diff(None)

        for diff in diff_index:
            # Filter out deleted files or unneeded files
            if diff.deleted_file:
                continue
            
            file_path = diff.a_path or diff.b_path
            
            if self._should_ignore(file_path):
                continue

            # Extract the raw diff string
            try:
                diff_text = diff.diff.decode('utf-8', errors='replace')
                if diff_text:
                    diffs[file_path] = diff_text
            except Exception:
                # Skip binary or unparseable diffs
                continue

        return diffs

    def _should_ignore(self, file_path: str) -> bool:
        """Helper to skip files defined in the ignore configuration."""
        filename = os.path.basename(file_path)
        if filename in config.ignored_files:
            return True
        
        _, ext = os.path.splitext(file_path)
        if ext.lower() in config.ignored_extensions:
            return True
            
        return False