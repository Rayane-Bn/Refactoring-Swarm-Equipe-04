"""
Auditor Agent - Analyzes code and identifies issues.

This agent reads Python code, runs static analysis, and produces
a structured report of issues that need to be fixed.

RESPONSIBILITIES:
- Read and analyze Python code
- Use Pylint/analyzer tools to detect issues
- Use LLM to understand context and prioritize issues
- Return structured list of issues with descriptions

TODO: Team member needs to implement the analyze() method
"""
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.file_manager import read_file
from src.tools.analyzer import analyze_code_quality, get_top_issues
from src.utils.logger import log_experiment, ActionType
from src.utils.config import GOOGLE_API_KEY, DEFAULT_MODEL

# TODO: Import LangChain / Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI


class AuditorAgent:
    """
    Agent responsible for auditing code quality and identifying issues.
    """
    
    def __init__(self):
        """Initialize the Auditor agent."""
        self.name = "Auditor"
        
        # TODO: Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1  # Low temperature for consistent analysis
        )
        
        # TODO: Load prompt from src/prompts/auditor_prompt.txt
        self.system_prompt = self._load_prompt()
        
        print(f"✅ {self.name} agent initialized")
    
    def _load_prompt(self) -> str:
        """
        Load the system prompt for the Auditor.
        
        Returns:
            System prompt as string
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / "auditor_prompt.txt"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback default prompt if file doesn't exist yet
            return """You are an expert Python code auditor.

Your task is to analyze Python code and identify issues that need to be fixed.

Focus on:
1. Syntax errors
2. Logic bugs
3. Missing docstrings
4. Poor variable naming
5. Unused variables
6. Code quality issues

Provide a clear, structured list of issues with:
- Line number
- Issue type
- Description
- Suggested fix

Be specific and actionable."""
    
    def analyze(self, file_path: str) -> Dict:
        """
        Analyze a Python file and return issues found.
        
        Args:
            file_path: Path to Python file to analyze
            
        Returns:
            Dictionary containing:
            - success: bool
            - issues: list of issues found
            - quality_score: float (0-10)
            - summary: str
        """
        print(f"🔍 {self.name}: Analyzing {file_path}...")
        
        try:
            # Step 1: Read the code
            code_content = read_file(file_path)
            
            # Step 2: Run static analysis (Pylint)
            analysis = analyze_code_quality(file_path)
            pylint_score = analysis.get("score", 0.0)
            pylint_issues = analysis.get("issues_by_category", {})
            
            # Step 3: Use LLM to provide deeper analysis
            # TODO: Team member needs to implement this part
            # Construct prompt with code and Pylint results
            user_prompt = f"""Analyze this Python code and the Pylint results.

FILE: {file_path}
PYLINT SCORE: {pylint_score}/10

CODE:
```python
{code_content}
```

PYLINT ISSUES:
{self._format_pylint_issues(pylint_issues)}

Please provide:
1. A summary of the main problems
2. Prioritized list of issues to fix (most critical first)
3. Specific recommendations for improvement
"""

            # Call LLM
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # TODO: Implement actual LLM call
            # For now, this is a placeholder structure
            # response = self.llm.invoke(messages)
            # llm_analysis = response.content
            
            # PLACEHOLDER: Remove this when implementing real LLM call
            llm_analysis = f"Analysis of {file_path}: Found {len(self._extract_all_issues(pylint_issues))} issues based on Pylint scan."
            
            # Step 4: Combine results
            all_issues = self._extract_all_issues(pylint_issues)
            
            result = {
                "success": True,
                "issues": all_issues,
                "quality_score": pylint_score,
                "summary": llm_analysis,
                "file_path": file_path
            }
            
            # Step 5: Log the interaction
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": file_path,
                    "input_prompt": user_prompt,
                    "output_response": llm_analysis,
                    "pylint_score": pylint_score,
                    "issues_found": len(all_issues)
                },
                status="SUCCESS"
            )
            
            print(f"   ✅ Analysis complete: {len(all_issues)} issues found, score: {pylint_score:.2f}/10")
            
            return result
            
        except Exception as e:
            error_msg = f"Error analyzing {file_path}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            # Log the failure
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": file_path,
                    "input_prompt": "Failed before prompt creation",
                    "output_response": error_msg,
                    "error": str(e)
                },
                status="FAILURE"
            )
            
            return {
                "success": False,
                "error": error_msg,
                "issues": [],
                "quality_score": 0.0
            }
    
    def _format_pylint_issues(self, issues_by_category: Dict) -> str:
        """Format Pylint issues for display in prompt."""
        lines = []
        for category, issue_list in issues_by_category.items():
            if issue_list:
                lines.append(f"\n{category.upper()}:")
                for issue in issue_list[:5]:  # Limit to top 5 per category
                    lines.append(f"  Line {issue['line']}: {issue['message']}")
        return "\n".join(lines) if lines else "No major issues detected by Pylint"
    
    def _extract_all_issues(self, issues_by_category: Dict) -> List[Dict]:
        """Extract all issues into a flat list."""
        all_issues = []
        priority_order = ["fatal", "error", "warning", "refactor", "convention"]
        
        for category in priority_order:
            if category in issues_by_category:
                for issue in issues_by_category[category]:
                    all_issues.append({
                        "severity": category,
                        "line": issue.get("line", 0),
                        "message": issue.get("message", ""),
                        "symbol": issue.get("symbol", "")
                    })
        
        return all_issues


# Test the agent
if __name__ == "__main__":
    print("🧪 Testing Auditor Agent...\n")
    
    from src.tools.file_manager import write_file, delete_file
    
    # Create a test file
    test_code = """
def calculate(x,y):
    result=x+y
    return result

unused_var = 42
"""
    
    write_file("test_audit.py", test_code)
    
    # Test the agent
    agent = AuditorAgent()
    result = agent.analyze("test_audit.py")
    
    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Issues: {len(result['issues'])}")
    print(f"   Score: {result.get('quality_score', 0):.2f}/10")
    
    # Cleanup
    delete_file("test_audit.py")
    
    print("\n✅ Auditor test complete!")