"""
Fixer Agent - Corrects code based on identified issues.

This agent receives a list of issues from the Auditor and fixes
the code accordingly. It must return the COMPLETE corrected file.

RESPONSIBILITIES:
- Read the current code
- Read the audit report (issues list)
- Use LLM to generate fixed code
- Write the corrected code back to file
- Ensure code is syntactically correct

TODO: Team member needs to implement the fix() method
"""
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.file_manager import read_file, write_file
from src.utils.logger import log_experiment, ActionType
from src.utils.config import GOOGLE_API_KEY, DEFAULT_MODEL

# TODO: Import LangChain / Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI


class FixerAgent:
    """
    Agent responsible for fixing code issues.
    """
    
    def __init__(self):
        """Initialize the Fixer agent."""
        self.name = "Fixer"
        
        # TODO: Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2  # Low temperature for consistent fixes
        )
        
        # TODO: Load prompt from src/prompts/fixer_prompt.txt
        self.system_prompt = self._load_prompt()
        
        print(f"✅ {self.name} agent initialized")
    
    def _load_prompt(self) -> str:
        """
        Load the system prompt for the Fixer.
        
        Returns:
            System prompt as string
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / "fixer_prompt.txt"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback default prompt
            return """You are an expert Python developer specializing in code refactoring.

Your task is to fix Python code based on identified issues.

CRITICAL REQUIREMENTS:
1. Return the COMPLETE fixed file, not just snippets
2. Fix ALL issues mentioned in the audit report
3. Preserve existing functionality - do not break working code
4. Add docstrings where missing
5. Improve code quality (naming, formatting, structure)
6. Ensure the code is syntactically correct

Output ONLY the corrected Python code, no explanations."""
    
    def fix(self, file_path: str, audit_result: Dict) -> Dict:
        """
        Fix a Python file based on audit results.
        
        Args:
            file_path: Path to Python file to fix
            audit_result: Dictionary from Auditor containing issues
            
        Returns:
            Dictionary containing:
            - success: bool
            - fixed_code: str (the corrected code)
            - changes_made: str (summary of changes)
        """
        print(f"🔧 {self.name}: Fixing {file_path}...")
        
        try:
            # Step 1: Read the current code
            original_code = read_file(file_path)
            
            # Step 2: Extract issues from audit
            issues = audit_result.get("issues", [])
            quality_score = audit_result.get("quality_score", 0.0)
            summary = audit_result.get("summary", "")
            
            if not issues and quality_score >= 8.0:
                print(f"   ℹ️  No significant issues found, code quality is good")
                return {
                    "success": True,
                    "fixed_code": original_code,
                    "changes_made": "No changes needed - code quality is acceptable"
                }
            
            # Step 3: Construct prompt with code and issues
            # TODO: Team member needs to implement this part
            issues_text = self._format_issues(issues)
            
            user_prompt = f"""Fix the following Python code based on the audit report.

FILE: {file_path}
CURRENT QUALITY SCORE: {quality_score}/10

ISSUES TO FIX:
{issues_text}

AUDIT SUMMARY:
{summary}

ORIGINAL CODE:
```python
{original_code}
```

Requirements:
1. Fix ALL issues listed above
2. Return the COMPLETE corrected code (not snippets)
3. Add docstrings where missing
4. Improve variable naming and code structure
5. Ensure code is syntactically correct
6. Do NOT add any explanations, ONLY output the fixed Python code

IMPORTANT: Output ONLY the corrected Python code wrapped in ```python``` code blocks.
"""

            # Step 4: Call LLM to generate fixed code
            # TODO: Implement actual LLM call
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # PLACEHOLDER: Remove this when implementing real LLM call
            # response = self.llm.invoke(messages)
            # fixed_code = self._extract_code_from_response(response.content)
            
            # For now, just return original code as placeholder
            fixed_code = original_code
            llm_response = "PLACEHOLDER: LLM response would go here"
            
            # Step 5: Write the fixed code back to file
            write_file(file_path, fixed_code)
            
            # Step 6: Log the interaction
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.FIX,
                details={
                    "file_fixed": file_path,
                    "input_prompt": user_prompt,
                    "output_response": llm_response,
                    "issues_addressed": len(issues),
                    "original_score": quality_score
                },
                status="SUCCESS"
            )
            
            print(f"   ✅ Code fixed and saved")
            
            return {
                "success": True,
                "fixed_code": fixed_code,
                "changes_made": f"Fixed {len(issues)} issues"
            }
            
        except Exception as e:
            error_msg = f"Error fixing {file_path}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            # Log the failure
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.FIX,
                details={
                    "file_fixed": file_path,
                    "input_prompt": "Failed before prompt creation",
                    "output_response": error_msg,
                    "error": str(e)
                },
                status="FAILURE"
            )
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def _format_issues(self, issues: list) -> str:
        """Format issues list for display in prompt."""
        if not issues:
            return "No specific issues identified"
        
        lines = []
        for idx, issue in enumerate(issues[:10], 1):  # Limit to top 10
            severity = issue.get("severity", "unknown")
            line = issue.get("line", "?")
            message = issue.get("message", "")
            
            lines.append(f"{idx}. [{severity.upper()}] Line {line}: {message}")
        
        if len(issues) > 10:
            lines.append(f"... and {len(issues) - 10} more issues")
        
        return "\n".join(lines)
    
    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract Python code from LLM response.
        Handles responses that include markdown code blocks.
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted Python code
        """
        import re
        
        # Try to extract code from ```python``` blocks
        pattern = r'```python\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Try just ``` blocks
        pattern = r'```\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, return the whole response
        return response.strip()


# Test the agent
if __name__ == "__main__":
    print("🧪 Testing Fixer Agent...\n")
    
    from src.tools.file_manager import write_file, delete_file
    
    # Create a test file
    test_code = """
def calculate(x,y):
    result=x+y
    return result
"""
    
    write_file("test_fix.py", test_code)
    
    # Mock audit result
    mock_audit = {
        "success": True,
        "issues": [
            {"severity": "convention", "line": 2, "message": "Missing docstring"},
            {"severity": "convention", "line": 2, "message": "Bad function name"}
        ],
        "quality_score": 4.5,
        "summary": "Function needs docstring and better formatting"
    }
    
    # Test the agent
    agent = FixerAgent()
    result = agent.fix("test_fix.py", mock_audit)
    
    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Changes: {result.get('changes_made', 'N/A')}")
    
    # Cleanup
    delete_file("test_fix.py")
    
    print("\n✅ Fixer test complete!")