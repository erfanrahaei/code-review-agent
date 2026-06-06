import asyncio
from openai import AsyncOpenAI
from config import config
from context_retriever import PythonContextRetriever  # New import

class CriticAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

    async def review_diff(self, client: AsyncOpenAI, file_path: str, diff_content: str, context: str) -> str:
        # Build prompt that separates the diff from the surrounding codebase context
        user_content = f"File Path: {file_path}\n\n"
        if context:
            user_content += f"--- Surrounding Code Context ---\n{context}\n\n"
        user_content += f"--- Git Diff (Changes to Review) ---\n{diff_content}"
        
        try:
            response = await client.chat.completions.create(
                model=config.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error executing {self.name} on {file_path}: {str(e)}"

class ReviewEngine:
    def __init__(self):
        if not config.api_key:
            raise ValueError("API key is missing. Please set the OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_base)
        self.context_retriever = PythonContextRetriever()  # Instantiate retriever
        
        # Critics remain unchanged, focusing on their specialized reviews
        self.security_critic = CriticAgent(
            name="Security Critic",
            system_prompt=(
                "You are an expert security engineer. Review the provided git diff for security risks, "
                "such as credential exposure, OWASP Top 10 vulnerabilities, and unsafe practices. "
                "Use the provided surrounding context to avoid false positives. "
                "Be direct and highly technical. If there are no issues, respond with 'NO_ISSUES'."
            )
        )
        
        self.logic_critic = CriticAgent(
            name="Logic Critic",
            system_prompt=(
                "You are a meticulous software engineer. Review the provided git diff for logical bugs, "
                "off-by-one errors, edge cases, concurrency issues, or potential unhandled errors. "
                "Use the provided surrounding context to trace variables and function scopes. "
                "If there are no logic issues, respond with 'NO_ISSUES'."
            )
        )

        self.performance_critic = CriticAgent(
            name="Performance Critic",
            system_prompt=(
                "You are a systems performance engineer. Review the provided git diff for bottlenecks, "
                "poor runtime complexity, excessive object allocation, or unoptimized database operations. "
                "Use the surrounding context to evaluate if external helper functions affect performance. "
                "If there are no performance issues, respond with 'NO_ISSUES'."
            )
        )

    async def run_review(self, changes: dict[str, str]) -> dict[str, list[dict[str, str]]]:
        """
        Processes each modified file by retrieving its context and running critics concurrently.
        """
        results = {}
        critics = [self.security_critic, self.logic_critic, self.performance_critic]
        
        for file_path, diff_content in changes.items():
            results[file_path] = []
            
            # Retrieve surrounding context if possible
            context = self.context_retriever.retrieve_context(file_path, diff_content)
            
            # Run reviews concurrently with context included
            tasks = [critic.review_diff(self.client, file_path, diff_content, context) for critic in critics]
            outputs = await asyncio.gather(*tasks)
            
            for critic, output in zip(critics, outputs):
                if output.strip() != "NO_ISSUES":
                    results[file_path].append({
                        "critic": critic.name,
                        "feedback": output
                    })
                    
        return results