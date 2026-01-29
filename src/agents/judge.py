"""
Judge Agent - Validates code by running tests.

This agent runs pytest on the code and determines if the fixes
are acceptable or if more iterations are needed.

RESPONSIBILITIES:
- Run pytest on the test file
- Analyze test results
- If tests pass: confirm success
- If tests fail: extract error messages and send back to Fixer
- Use LLM to provide insights on failures

TODO: Team member needs to implement the validate() method
"""
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.tester import run_pytest, generate_test_report, extract_failure_messages
from src.utils.logger import log_experiment, ActionType
from src.utils.config import GOOGLE_API_KEY, DEFAULT_MODEL

# TODO: Import LangChain / Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI


class JudgeAgent:
    """
    Agent responsible for validating code with tests.
    """
    
    def __init__(self):
        """Initialize the Judge agent."""
        self.name = "Judge"
        
        # TODO: Initialize LLM (optional - for analyzing complex failures)
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1
        )
        
        # TODO: Load prompt from src/prompts/judge_prompt.txt
        self.system_prompt = self._load_prompt()
        
        print(f"✅ {self.name} agent initialized")
    
    def _load_prompt(self) -> str:
        """
        Load the system prompt for the Judge.
        
        Returns:
            System prompt as string
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / "judge_prompt.txt"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback default prompt
            return """You are an expert test validator and debugging assistant.

Your task is to analyze test results and provide clear feedback.

When tests PASS:
- Confirm that the code is working correctly
- Briefly summarize what was tested

When tests FAIL:
- Explain WHY the tests failed in simple terms
- Identify what needs to be fixed
- Suggest specific corrections

Be clear, concise, and actionable."""
    
    def validate(self, file_path: str, test_file: str) -> Dict:
        """
        Validate a Python file by running its tests.
        
        Args:
            file_path: Path to the code file being tested
            test_file: Path to the test file
            
        Returns:
            Dictionary containing:
            - success: bool (True if validation completed, not if tests passed)
            - tests_passed: bool (True if all tests passed)
            - passed: int (number of tests passed)
            - failed: int (number of tests failed)
            - feedback: str (feedback for Fixer if tests failed)
        """
        print(f"⚖️  {self.name}: Running tests for {file_path}...")
        
        try:
            # Step 1: Run pytest
            test_result = run_pytest(test_file, verbose=True)
            
            if not test_result.get("success") and test_result.get("error"):
                # pytest itself failed to run
                error_msg = test_result.get("error", "Unknown error")
                print(f"   ❌ Test execution error: {error_msg}")
                
                log_experiment(
                    agent_name=self.name,
                    model_used=DEFAULT_MODEL,
                    action=ActionType.DEBUG,
                    details={
                        "file_validated": file_path,
                        "test_file": test_file,
                        "input_prompt": "Test execution failed",
                        "output_response": error_msg,
                        "error": error_msg
                    },
                    status="FAILURE"
                )
                
                return {
                    "success": False,
                    "tests_passed": False,
                    "error": error_msg
                }
            
            # Step 2: Extract test statistics
            passed = test_result.get("passed", 0)
            failed = test_result.get("failed", 0)
            total = test_result.get("total", 0)
            raw_output = test_result.get("raw_output", "")
            
            tests_passed = (failed == 0 and passed > 0)
            
            print(f"   📊 Test Results: {passed}/{total} passed")
            
            # Step 3: Generate feedback
            if tests_passed:
                # All tests passed!
                feedback = f"✅ All {passed} tests passed successfully!"
                
                log_experiment(
                    agent_name=self.name,
                    model_used=DEFAULT_MODEL,
                    action=ActionType.DEBUG,
                    details={
                        "file_validated": file_path,
                        "test_file": test_file,
                        "input_prompt": f"Validating {file_path} with {test_file}",
                        "output_response": feedback,
                        "passed": passed,
                        "failed": failed,
                        "total": total
                    },
                    status="SUCCESS"
                )
                
                print(f"   {feedback}")
                
                return {
                    "success": True,
                    "tests_passed": True,
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                    "feedback": feedback
                }
            
            else:
                # Tests failed - need to provide feedback
                print(f"   ❌ {failed} test(s) failed")
                
                # Extract failure messages
                failure_messages = extract_failure_messages(raw_output)
                
                # TODO: Optionally use LLM to analyze failures
                # For complex failures, the LLM can provide insights
                if failed > 3 or not failure_messages:
                    # Use LLM for complex analysis
                    feedback = self._analyze_failures_with_llm(
                        file_path, test_file, raw_output, failure_messages
                    )
                else:
                    # Simple feedback for straightforward failures
                    feedback = self._format_simple_feedback(failure_messages, passed, failed)
                
                log_experiment(
                    agent_name=self.name,
                    model_used=DEFAULT_MODEL,
                    action=ActionType.DEBUG,
                    details={
                        "file_validated": file_path,
                        "test_file": test_file,
                        "input_prompt": f"Validating {file_path} with {test_file}",
                        "output_response": feedback,
                        "passed": passed,
                        "failed": failed,
                        "total": total,
                        "failure_messages": failure_messages
                    },
                    status="SUCCESS"  # Validation succeeded, even though tests failed
                )
                
                return {
                    "success": True,
                    "tests_passed": False,
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                    "feedback": feedback,
                    "failures": failure_messages
                }
            
        except Exception as e:
            error_msg = f"Error validating {file_path}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.DEBUG,
                details={
                    "file_validated": file_path,
                    "test_file": test_file,
                    "input_prompt": "Validation failed",
                    "output_response": error_msg,
                    "error": str(e)
                },
                status="FAILURE"
            )
            
            return {
                "success": False,
                "tests_passed": False,
                "error": error_msg
            }
    
    def _format_simple_feedback(self, failure_messages: list, passed: int, failed: int) -> str:
        """Format simple feedback for straightforward test failures."""
        feedback_lines = [
            f"❌ {failed} test(s) failed, {passed} passed.",
            "\nFailures:"
        ]
        
        for idx, msg in enumerate(failure_messages[:5], 1):  # Limit to 5
            feedback_lines.append(f"{idx}. {msg}")
        
        if len(failure_messages) > 5:
            feedback_lines.append(f"... and {len(failure_messages) - 5} more failures")
        
        feedback_lines.append("\nPlease fix these issues and try again.")
        
        return "\n".join(feedback_lines)
    
    def _analyze_failures_with_llm(self, file_path: str, test_file: str, 
                                    raw_output: str, failure_messages: list) -> str:
        """
        Use LLM to analyze complex test failures.
        
        Args:
            file_path: Path to code file
            test_file: Path to test file
            raw_output: Raw pytest output
            failure_messages: Extracted failure messages
            
        Returns:
            LLM-generated feedback
        """
        # TODO: Team member can implement this for more sophisticated analysis
        # For now, return formatted failures
        
        user_prompt = f"""Analyze these test failures and provide clear feedback.

CODE FILE: {file_path}
TEST FILE: {test_file}

TEST OUTPUT:
{raw_output[:1000]}  # Limit to first 1000 chars

FAILURES:
{chr(10).join(failure_messages[:5])}

Provide:
1. What went wrong (in simple terms)
2. What needs to be fixed in the code
3. Specific suggestions for the Fixer agent

Be concise and actionable.
"""
        
        # PLACEHOLDER: Implement actual LLM call if needed
        # messages = [
        #     {"role": "system", "content": self.system_prompt},
        #     {"role": "user", "content": user_prompt}
        # ]
        # response = self.llm.invoke(messages)
        # return response.content
        
        # For now, return simple formatted feedback
        return self._format_simple_feedback(failure_messages, 0, len(failure_messages))


# Test the agent
if __name__ == "__main__":
    print("🧪 Testing Judge Agent...\n")
    
    from src.tools.file_manager import write_file, delete_file
    
    # Create a simple code and test file
    code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
    
    test_code = """
from test_judge import add, subtract

def test_add():
    assert add(2, 3) == 5
    assert add(0, 0) == 0

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 0) == 0
"""
    
    write_file("test_judge.py", code)
    write_file("test_test_judge.py", test_code)
    
    # Test the agent
    agent = JudgeAgent()
    result = agent.validate("test_judge.py", "test_test_judge.py")
    
    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Tests Passed: {result.get('tests_passed', False)}")
    print(f"   Passed/Total: {result.get('passed', 0)}/{result.get('total', 0)}")
    
    # Cleanup
    delete_file("test_judge.py")
    delete_file("test_test_judge.py")
    
    print("\n✅ Judge test complete!")