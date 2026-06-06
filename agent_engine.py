import asyncio
from openai import AsyncOpenAI
from config import config
from context_retriever import PythonContextRetriever

class CriticAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

    async def review_diff(self, client: AsyncOpenAI, file_path: str, diff_content: str, context: str) -> str:
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


class SynthesizerAgent:
    def __init__(self):
        self.name = "Synthesizer"
        self.system_prompt = (
            "You are a professional Lead Software Engineer. Your task is to analyze raw critiques "
            "provided by separate Security, Logic, and Performance reviewers, and synthesize them into a single, "
            "cohesive, high-quality final review.\n\n"
            "Guidelines:\n"
            "1. Deduplicate: If multiple critics flag the same issue, merge their feedback into a single, comprehensive point.\n"
            "2. Filter: Discard trivial, stylistic, or highly subjective observations. Focus on correctness, reliability, and security.\n"
            "3. Actionable Code: For any logical corrections, provide the exact corrected code block in standard markdown "
            "format using ```suggestion ... ``` tags so the developer can easily read or copy it.\n"
            "4. Tone: Keep your review objective, polite, helpful, and concise.\n"
            "5. If there are no valuable issues to report after your synthesis, respond with only the word: 'NO_ISSUES'."
        )

    async def synthesize(self, client: AsyncOpenAI, file_path: str, diff_content: str, raw_feedbacks: list[dict[str, str]]) -> str:
        # Format the critics inputs to clearly show who commented what
        critique_summary = ""
        for idx, item in enumerate(raw_feedbacks, start=1):
            critique_summary += f"[{idx}] {item['critic']} feedback:\n{item['feedback']}\n\n"

        user_content = (
            f"File Path: {file_path}\n\n"
            f"--- Original Diff ---\n{diff_content}\n\n"
            f"--- Raw Critics Input ---\n{critique_summary}"
        )

        try:
            response = await client.chat.completions.create(
                model=config.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.2, # Slightly elevated temperature for better summarization flow
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"Error executing synthesis on {file_path}: {str(e)}"


class ReviewEngine:
    def __init__(self):
        if not config.api_key:
            raise ValueError("API key is missing. Please set the OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_base)
        self.context_retriever = PythonContextRetriever()
        
        # Instantiate the final synthesis agent
        self.synthesizer = SynthesizerAgent()
        
        # Critics
        self.security_critic = CriticAgent(
            name="Security Critic",
            system_prompt=(
                "You are an expert security engineer. Review the provided git diff for security risks, "
                "such as credential exposure, OWASP Top 10 vulnerabilities, and unsafe practices. "
                "Be direct and highly technical. If there are no issues, respond with 'NO_ISSUES'."
            )
        )
        self.logic_critic = CriticAgent(
            name="Logic Critic",
            system_prompt=(
                "You are a meticulous software engineer. Review the provided git diff for logical bugs, "
                "off-by-one errors, edge cases, concurrency issues, or potential unhandled errors. "
                "If there are no logic issues, respond with 'NO_ISSUES'."
            )
        )
        self.performance_critic = CriticAgent(
            name="Performance Critic",
            system_prompt=(
                "You are a systems performance engineer. Review the provided git diff for bottlenecks, "
                "poor runtime complexity, excessive object allocation, or unoptimized database operations. "
                "If there are no performance issues, respond with 'NO_ISSUES'."
            )
        )

    async def run_review(self, changes: dict[str, str]) -> dict[str, str]:
        """
        Runs the critics concurrently, then synthesizes their output sequentially into a unified report.
        """
        compiled_reviews = {}
        critics = [self.security_critic, self.logic_critic, self.performance_critic]
        
        for file_path, diff_content in changes.items():
            context = self.context_retriever.retrieve_context(file_path, diff_content)
            
            # Step 1: Run specialized reviews concurrently
            tasks = [critic.review_diff(self.client, file_path, diff_content, context) for critic in critics]
            outputs = await asyncio.gather(*tasks)
            
            raw_feedbacks = []
            for critic, output in zip(critics, outputs):
                if output.strip() != "NO_ISSUES":
                    raw_feedbacks.append({
                        "critic": critic.name,
                        "feedback": output
                    })
            
            # Step 2: If there are raw critiques, pass them to the Synthesizer
            if raw_feedbacks:
                synthesis_result = await self.synthesizer.synthesize(
                    self.client, file_path, diff_content, raw_feedbacks
                )
                compiled_reviews[file_path] = synthesis_result
            else:
                compiled_reviews[file_path] = "NO_ISSUES"
                    
        return compiled_reviews