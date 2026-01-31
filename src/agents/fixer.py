"""
Fixer Agent - Corrects code based on identified issues.
Uses Google Gemini LLM to generate fixed code.
"""
import sys
from pathlib import Path
from typing import Dict
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.file_manager import read_file, write_file
from src.utils.logger import log_experiment, ActionType
from src.utils.config import GOOGLE_API_KEY, DEFAULT_MODEL

from langchain_google_genai import ChatGoogleGenerativeAI


class FixerAgent:
    """
    Agent responsible for fixing code issues.
    """
    
    def __init__(self):
        """Initialize the Fixer agent."""
        self.name = "Fixer"
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.2
        )
        
        # Load system prompt
        self.system_prompt = self._load_prompt()
        
        print(f"✅ {self.name} agent initialized")
    
    def _load_prompt(self) -> str:
        """Load the system prompt for the Fixer."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "fixer_prompt.txt"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback
            return """You are an expert Python developer.
Fix code based on identified issues.
Return the COMPLETE fixed file.
Preserve functionality, fix bugs, add docstrings, improve naming.
Output ONLY the corrected code, no explanations."""
    
    def fix(self, file_path: str, audit_result: Dict) -> Dict:
        """
        Fix a Python file based on audit results.
        
        Args:
            file_path: Path to Python file to fix
            audit_result: Dictionary from Auditor containing issues
            
        Returns:
            Dictionary containing:
            - success: bool
            - fixed_code: str
            - changes_made: str
        """
        print(f"🔧 {self.name}: Fixing {file_path}...")
        
        try:
            # Step 1: Read current code
            original_code = read_file(file_path)
            
            # Step 2: Extract issues
            issues = audit_result.get("issues", [])
            quality_score = audit_result.get("quality_score", 0.0)
            summary = audit_result.get("summary", "")
            
            # If no issues and good quality, skip
            if not issues and quality_score >= 8.0:
                print(f"   ℹ️  Code quality is good, no fixes needed")
                return {
                    "success": True,
                    "fixed_code": original_code,
                    "changes_made": "No changes needed"
                }
            
            # Step 3: Format issues for prompt
            issues_text = self._format_issues(issues)
            
            # Step 4: Construct prompt
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

REQUIREMENTS:
1. Fix ALL listed issues
2. Add proper docstrings (Google style) for all functions and classes
3. Use snake_case for functions and variables
4. Improve code readability
5. Ensure code is syntactically correct
6. Return the COMPLETE corrected code

OUTPUT FORMAT:
Return ONLY the fixed Python code wrapped in ```python``` code blocks.
Do NOT include any explanations or comments about what you changed.
"""

            # Step 5: Call LLM
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.llm.invoke(user_prompt)
            llm_response = response.content
            
            # Step 6: Extract code from response
            fixed_code = self._extract_code_from_response(llm_response)
            
            # If extraction failed, use response as-is
            if not fixed_code or len(fixed_code) < 10:
                fixed_code = original_code
                print(f"   ⚠️  Could not extract fixed code from LLM, keeping original")
            
            # Step 7: Write fixed code back
            write_file(file_path, fixed_code)
            
            # Step 8: Log
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.FIX,
                details={
                    "file_fixed": file_path,
                    "input_prompt": user_prompt,
                    "output_response": llm_response,
                    "issues_addressed": len(issues),
                    "original_score": quality_score,
                    "code_length_before": len(original_code),
                    "code_length_after": len(fixed_code)
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
        """Format issues list for prompt."""
        if not issues:
            return "No specific issues identified"
        
        lines = []
        for idx, issue in enumerate(issues[:15], 1):
            severity = issue.get("severity", "unknown")
            issue_type = issue.get("type", "general")
            line = issue.get("line", "?")
            message = issue.get("message", "")
            
            lines.append(f"{idx}. [{severity.upper()}] {issue_type} (Line {line}): {message}")
        
        if len(issues) > 15:
            lines.append(f"... and {len(issues) - 15} more issues")
        
        return "\n".join(lines)
    
    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract Python code from LLM response.
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted Python code
        """
        # Try to extract from ```python``` blocks
        pattern = r'```python\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Try just ``` blocks
        pattern = r'```\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, return whole response
        return response.strip()


if __name__ == "__main__":
    print("🧪 Testing Fixer Agent...\n")
    
    from src.tools.file_manager import write_file, delete_file
    
    test_code = """
def calculate(x,y):
    result=x+y
    return result
"""
    
    write_file("test_fix.py", test_code)
    
    mock_audit = {
        "success": True,
        "issues": [
            {"severity": "minor", "type": "style", "line": 2, "message": "Missing docstring"},
            {"severity": "minor", "type": "style", "line": 2, "message": "Bad spacing"}
        ],
        "quality_score": 4.5,
        "summary": "Function needs docstring and formatting"
    }
    
    agent = FixerAgent()
    result = agent.fix("test_fix.py", mock_audit)
    
    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Changes: {result.get('changes_made', 'N/A')}")
    
    delete_file("test_fix.py")
    
    print("\n✅ Fixer test complete!")