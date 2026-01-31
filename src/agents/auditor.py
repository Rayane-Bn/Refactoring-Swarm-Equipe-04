"""
Auditor Agent - Analyzes code and identifies issues.
Uses the CodeAnalyzer tool and Google Gemini LLM.
"""
import sys
from pathlib import Path
from typing import Dict, List
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.analyzer import CodeAnalyzer
from src.tools.file_manager import read_file
from src.utils.logger import log_experiment, ActionType
from src.utils.config import GOOGLE_API_KEY, DEFAULT_MODEL

from langchain_google_genai import ChatGoogleGenerativeAI


class AuditorAgent:
    """
    Agent responsible for auditing code quality and identifying issues.
    """
    
    def __init__(self):
        """Initialize the Auditor agent."""
        self.name = "Auditor"
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1
        )
        
        # Load system prompt
        self.system_prompt = self._load_prompt()
        
        print(f"✅ {self.name} agent initialized")
    
    def _load_prompt(self) -> str:
        """Load the system prompt for the Auditor."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "auditor_prompt.txt"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback
            return """You are an expert Python code auditor.
Analyze code and identify issues that need fixing.
Focus on: bugs, missing docstrings, poor naming, unused variables, code quality.
Provide clear, actionable feedback."""
    
    def analyze(self, file_path: str) -> Dict:
        """
        Analyze a Python file and return issues found.
        
        Args:
            file_path: Path to Python file to analyze
            
        Returns:
            Dictionary containing:
            - success: bool
            - issues: list of issues
            - quality_score: float
            - summary: str
        """
        print(f"🔍 {self.name}: Analyzing {file_path}...")
        
        try:
            # Step 1: Read the code
            code_content = read_file(file_path)
            
            # Step 2: Run static analysis with CodeAnalyzer
            analyzer = CodeAnalyzer(file_path)
            analysis_results = analyzer.analyze()
            
            # Step 3: Generate report from analyzer
            report = analyzer.generate_report()
            
            # Step 4: Extract key information
            syntax_valid = analysis_results['syntax']['valid']
            
            if not syntax_valid:
                # Syntax error - critical issue
                print(f"   ❌ Syntax error detected!")
                issues = [{
                    "severity": "critical",
                    "type": "syntax",
                    "line": analysis_results['syntax']['errors'][0]['line'],
                    "message": analysis_results['syntax']['message']
                }]
                
                result = {
                    "success": True,
                    "issues": issues,
                    "quality_score": 0.0,
                    "summary": "Critical syntax error prevents execution",
                    "file_path": file_path
                }
                
                # Log
                log_experiment(
                    agent_name=self.name,
                    model_used="static_analysis",
                    action=ActionType.ANALYSIS,
                    details={
                        "file_analyzed": file_path,
                        "input_prompt": "Syntax check",
                        "output_response": analysis_results['syntax']['message'],
                        "syntax_valid": False
                    },
                    status="SUCCESS"
                )
                
                return result
            
            # Step 5: Use LLM to provide deeper analysis
            user_prompt = f"""Analyze this Python code file and provide a detailed assessment.

FILE: {file_path}

CODE:
```python
{code_content}
```

STATIC ANALYSIS REPORT:
{report}

Based on the code and static analysis, provide a JSON response with:
1. A brief summary of code quality
2. List of issues found (syntax, style, bugs, design problems)
3. Priority order for fixes

Format your response as valid JSON only, no markdown.
"""

            # Call LLM
            response = self.llm.invoke(user_prompt)
            llm_output = response.content
            
            # Try to parse LLM response as JSON
            try:
                # Remove markdown code blocks if present
                clean_output = llm_output.strip()
                if clean_output.startswith("```json"):
                    clean_output = clean_output[7:]
                if clean_output.startswith("```"):
                    clean_output = clean_output[3:]
                if clean_output.endswith("```"):
                    clean_output = clean_output[:-3]
                clean_output = clean_output.strip()
                
                llm_analysis = json.loads(clean_output)
                summary = llm_analysis.get("summary", "Code analyzed")
                llm_issues = llm_analysis.get("issues", [])
            except json.JSONDecodeError:
                # If LLM doesn't return JSON, use text summary
                summary = llm_output[:200]
                llm_issues = []
            
            # Step 6: Combine static analysis issues with LLM insights
            all_issues = []
            
            # Add style issues
            for issue in analysis_results.get('style', {}).get('issues', [])[:5]:
                all_issues.append({
                    "severity": "minor",
                    "type": "style",
                    "line": issue['line'],
                    "message": issue['message']
                })
            
            # Add security issues
            for issue in analysis_results.get('security', {}).get('issues', []):
                all_issues.append({
                    "severity": issue['severity'],
                    "type": "security",
                    "line": 0,
                    "message": issue['message']
                })
            
            # Add complexity issues
            complexity_data = analysis_results.get('complexity', {})
            for func in complexity_data.get('functions', []):
                if func['complexity'] > 10:
                    all_issues.append({
                        "severity": "major",
                        "type": "complexity",
                        "line": func['line'],
                        "message": f"Function '{func['name']}' has high complexity: {func['complexity']}"
                    })
            
            # Add LLM-identified issues
            all_issues.extend(llm_issues[:5])
            
            # Calculate a quality score (0-10)
            # Based on: syntax, style issues, security issues, complexity
            quality_score = 10.0
            quality_score -= len(analysis_results.get('style', {}).get('issues', [])) * 0.1
            quality_score -= len(analysis_results.get('security', {}).get('issues', [])) * 1.0
            quality_score -= (complexity_data.get('overall_complexity', 0) / 10) * 0.5
            quality_score = max(0.0, min(10.0, quality_score))
            
            result = {
                "success": True,
                "issues": all_issues,
                "quality_score": quality_score,
                "summary": summary,
                "file_path": file_path
            }
            
            # Log the interaction
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": file_path,
                    "input_prompt": user_prompt,
                    "output_response": llm_output,
                    "quality_score": quality_score,
                    "issues_found": len(all_issues)
                },
                status="SUCCESS"
            )
            
            print(f"   ✅ Analysis complete: {len(all_issues)} issues, score: {quality_score:.2f}/10")
            
            return result
            
        except Exception as e:
            error_msg = f"Error analyzing {file_path}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": file_path,
                    "input_prompt": "Failed before analysis",
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


if __name__ == "__main__":
    print("🧪 Testing Auditor Agent...\n")
    
    from src.tools.file_manager import write_file, delete_file
    
    test_code = """
def calculate(x,y):
    result=x+y
    return result

unused_var = 42
"""
    
    write_file("test_audit.py", test_code)
    
    agent = AuditorAgent()
    result = agent.analyze("test_audit.py")
    
    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Issues: {len(result['issues'])}")
    print(f"   Score: {result.get('quality_score', 0):.2f}/10")
    
    delete_file("test_audit.py")
    
    print("\n✅ Auditor test complete!")