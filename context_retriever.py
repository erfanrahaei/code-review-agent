import ast
import os

class PythonContextRetriever:
    """
    Analyzes local Python files using the built-in AST module.
    Identifies which functions or classes were modified in a diff 
    and extracts their complete source definitions to provide rich local context.
    """
    
    @staticmethod
    def get_modified_line_numbers(diff_content: str) -> set[int]:
        """
        Parses a unified git diff to determine which target file line numbers 
        were added or modified.
        """
        modified_lines = set()
        current_line = 0
        
        for line in diff_content.splitlines():
            if line.startswith('@@'):
                # Extract starting line number for the target file
                # Format: @@ -start,count +start,count @@
                try:
                    parts = line.split('+')
                    if len(parts) > 1:
                        target_part = parts[1].split(' ')[0]
                        if ',' in target_part:
                            current_line = int(target_part.split(',')[0])
                        else:
                            current_line = int(target_part)
                except (ValueError, IndexError):
                    pass
            elif line.startswith('+') and not line.startswith('+++'):
                modified_lines.add(current_line)
                current_line += 1
            elif line.startswith('-') or line.startswith('---'):
                # Deletions do not advance the target file line count
                continue
            else:
                # Unchanged context line in diff
                current_line += 1
                
        return modified_lines

    def retrieve_context(self, file_path: str, diff_content: str) -> str:
        """
        Reads the target file, parses its AST, maps modified lines to code blocks,
        and returns those full function/class strings.
        """
        # This implementation is currently tailored for Python source code
        if not file_path.endswith('.py') or not os.path.exists(file_path):
            return ""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                f.seek(0)
                lines = f.readlines()
        except Exception as e:
            return f"Context retrieval warning: Could not read file lines ({str(e)})."

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # Fallback if the local file currently contains invalid syntax during development
            return "Context retrieval notice: Skipping AST extraction due to a syntax error in the file."

        modified_lines = self.get_modified_line_numbers(diff_content)
        if not modified_lines:
            return ""

        context_blocks = []
        
        # Walk through AST nodes to locate code structures
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                node_start = node.lineno
                # end_lineno is supported in Python 3.8+
                node_end = getattr(node, 'end_lineno', len(lines))
                
                # Check if any modified lines intersect with this node's line range
                node_lines_range = set(range(node_start, node_end + 1))
                if modified_lines.intersection(node_lines_range):
                    block_code = "".join(lines[node_start - 1:node_end])
                    block_type = "Class" if isinstance(node, ast.ClassDef) else "Function"
                    context_blocks.append(
                        f"--- Local Context: {block_type} '{node.name}' (Lines {node_start}-{node_end}) ---\n"
                        f"{block_code.strip()}\n"
                    )

        if context_blocks:
            return "\n".join(context_blocks)
        return ""