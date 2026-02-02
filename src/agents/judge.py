"""
Judge Agent - Generates tests and validates code.

CRITICAL: This agent GENERATES test files using LLM to understand what code SHOULD do.
It does NOT assume tests already exist.
"""
import sys
from pathlib import Path
from typing import Dict
import subprocess
import re
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.file_manager import read_file, write_file
from src.utils.logger import log_experiment, ActionType
from src.utils.config import GOOGLE_API_KEY, DEFAULT_MODEL, SANDBOX_DIR

from langchain_google_genai import ChatGoogleGenerativeAI


class JudgeAgent:
    """
    Agent responsible for generating tests and validating code.
    
    WORKFLOW:
    1. Analyze code with LLM to understand what it SHOULD do
    2. Generate appropriate test file
    3. Run tests with pytest
    4. Report results
    """
    
    def __init__(self):
        """Initialize the Judge agent."""
        self.name = "Judge"
        
        # Initialize LLM for test generation
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3  # Some creativity for test generation
        )
        
        # Load system prompt
        self.system_prompt = self._load_prompt()
        
        print(f"✅ {self.name} agent initialized")
    
    def _load_prompt(self) -> str:
        """Load the system prompt for the Judge."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "judge_prompt.txt"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback
            return """You are an expert test validator and test generator.
Your task is to generate comprehensive unit tests that validate code behavior.
Generate tests that check what the code SHOULD do, not just what it does."""
    
    def validate(self, file_path: str, test_file: str) -> Dict:
        """
        Validate code by generating and running tests.
        
        Args:
            file_path: Path to the code file
            test_file: Path where test file should be created
            
        Returns:
            Dictionary with validation results
        """
        print(f"⚖️  {self.name}: Validating {file_path}...")
        
        try:
            # Step 1: Check if test file exists
            test_path = SANDBOX_DIR / test_file
            
            if not test_path.exists():
                print(f"   ℹ️  Test file not found, generating tests...")
                generation_result = self._generate_tests(file_path, test_file)
                
                if not generation_result.get("success", False):
                    return {
                        "success": False,
                        "tests_passed": False,
                        "error": f"Failed to generate tests: {generation_result.get('error', 'Unknown')}"
                    }
                
                print(f"   ✅ Tests generated: {test_file}")
            
            # Step 2: Run pytest
            print(f"   🧪 Running tests...")
            
            cmd = ["pytest", str(test_path), "-v", "--tb=short", "--color=no"]
            
            # Change to sandbox directory
            original_dir = os.getcwd()
            os.chdir(SANDBOX_DIR)
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            finally:
                os.chdir(original_dir)
            
            # Parse output
            output = result.stdout + result.stderr
            
            # Extract test counts
            passed, failed, total = self._parse_pytest_output(output)
            
            tests_passed = (result.returncode == 0 and failed == 0 and passed > 0)
            
            print(f"   📊 Test Results: {passed}/{total} passed")
            
            if tests_passed:
                # Success!
                feedback = f"✅ All {passed} tests passed!"
                
                log_experiment(
                    agent_name=self.name,
                    model_used="pytest",
                    action=ActionType.DEBUG,
                    details={
                        "file_validated": file_path,
                        "test_file": test_file,
                        "input_prompt": f"Running tests for {file_path}",
                        "output_response": feedback,
                        "passed": passed,
                        "failed": failed,
                        "total": total,
                        "exit_code": result.returncode
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
                # Tests failed
                print(f"   ❌ {failed} test(s) failed")
                
                # Extract failure messages
                failures = self._extract_failure_messages(output)
                
                # Create feedback
                feedback_lines = [
                    f"❌ {failed} test(s) failed, {passed} passed.",
                    "\nFailures:"
                ]
                
                for idx, msg in enumerate(failures[:5], 1):
                    feedback_lines.append(f"{idx}. {msg}")
                
                if len(failures) > 5:
                    feedback_lines.append(f"... and {len(failures) - 5} more")
                
                feedback_lines.append("\nPlease fix these issues and try again.")
                feedback = "\n".join(feedback_lines)
                
                log_experiment(
                    agent_name=self.name,
                    model_used="pytest",
                    action=ActionType.DEBUG,
                    details={
                        "file_validated": file_path,
                        "test_file": test_file,
                        "input_prompt": f"Running tests for {file_path}",
                        "output_response": feedback,
                        "passed": passed,
                        "failed": failed,
                        "total": total,
                        "failures": failures,
                        "exit_code": result.returncode
                    },
                    status="SUCCESS"
                )
                
                return {
                    "success": True,
                    "tests_passed": False,
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                    "feedback": feedback,
                    "failures": failures
                }
            
        except subprocess.TimeoutExpired:
            error_msg = "Tests timed out after 30 seconds"
            print(f"   ❌ {error_msg}")
            
            log_experiment(
                agent_name=self.name,
                model_used="pytest",
                action=ActionType.DEBUG,
                details={
                    "file_validated": file_path,
                    "test_file": test_file,
                    "input_prompt": f"Running tests for {file_path}",
                    "output_response": error_msg
                },
                status="FAILURE"
            )
            
            return {
                "success": False,
                "tests_passed": False,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"Error validating {file_path}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            log_experiment(
                agent_name=self.name,
                model_used="pytest",
                action=ActionType.DEBUG,
                details={
                    "file_validated": file_path,
                    "test_file": test_file,
                    "input_prompt": f"Running tests for {file_path}",
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
    
    def _generate_tests(self, file_path: str, test_file: str) -> Dict:
        """
        Generate test file using LLM based on code analysis.
        
        This is CRITICAL: The LLM must understand what code SHOULD do,
        not just what it does currently.
        
        Args:
            file_path: Path to code file
            test_file: Path where test should be created
            
        Returns:
            Dictionary with generation result
        """
        try:
            # Read the code
            code_content = read_file(file_path)
            
            # Get module name from file path
            module_name = Path(file_path).stem
            
            # Construct prompt for test generation
            user_prompt = f"""You are a test generation expert. Your task is to generate comprehensive unit tests.

CRITICAL INSTRUCTIONS:
CRITICAL - PRESERVE CODE STRUCTURE:
- If you see standalone functions like "def add(x, y):", import: from module import add
- If you see class methods like "class Calculator: def add(self, x, y):", use: obj = Calculator(); obj.add()
- DO NOT change standalone functions into class methods
- Match the EXACT structure of the code as it exists
1. Analyze the code and understand what each function/class SHOULD do based on:
   - Function names (e.g., "calculate_average" should compute average, not sum)
   - Parameter names and types
   - Return value expectations
   - Business logic inferred from context

2. Generate tests that validate CORRECT behavior, not current buggy behavior
3. Include edge cases (empty inputs, zero, negative numbers, etc.)
4. Test ALL functions and classes in the module

CODE TO TEST:
FILE: {module_name}.py

```python
{code_content}
```

EXAMPLE FORMAT:
```python
from {module_name} import function_name, ClassName

def test_function_name():
    # Test normal cases
    assert function_name(input) == expected_output
    
    # Test edge cases
    assert function_name(edge_case) == expected_edge_result

def test_class_method():
    obj = ClassName()
    assert obj.method(input) == expected_output
```

REQUIREMENTS:
1. Import ALL functions and classes from {module_name}
2. Create comprehensive test functions (test_*)
3. Use assert statements with expected CORRECT values
4. Cover normal cases and edge cases
5. Output ONLY the complete Python test code, no explanations

Generate the complete test file now:
"""

            # Call LLM
            response = self.llm.invoke(user_prompt)
            test_code = response.content
            
            # Extract code from response
            test_code = self._extract_code_from_response(test_code)
            
            # Validate we got actual test code
            if "def test_" not in test_code or "assert" not in test_code:
                return {
                    "success": False,
                    "error": "Generated code doesn't contain valid tests"
                }
            
            # Write test file
            write_file(test_file, test_code)
            
            # Log
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.GENERATION,
                details={
                    "file_tested": file_path,
                    "test_file": test_file,
                    "input_prompt": user_prompt,
                    "output_response": test_code,
                    "test_count": test_code.count("def test_")
                },
                status="SUCCESS"
            )
            
            return {
                "success": True,
                "test_file": test_file,
                "test_code": test_code
            }
            
        except Exception as e:
            error_msg = f"Error generating tests: {str(e)}"
            
            log_experiment(
                agent_name=self.name,
                model_used=DEFAULT_MODEL,
                action=ActionType.GENERATION,
                details={
                    "file_tested": file_path,
                    "test_file": test_file,
                    "input_prompt": "Test generation failed",
                    "output_response": error_msg,
                    "error": str(e)
                },
                status="FAILURE"
            )
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from LLM response."""
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
        
        # Return whole response
        return response.strip()
    
    def _parse_pytest_output(self, output: str) -> tuple:
        """Parse pytest output to extract test counts."""
        passed = 0
        failed = 0
        
        # Look for summary line
        match = re.search(r'(\d+) passed', output)
        if match:
            passed = int(match.group(1))
        
        match = re.search(r'(\d+) failed', output)
        if match:
            failed = int(match.group(1))
        
        total = passed + failed
        
        return passed, failed, total
    
    def _extract_failure_messages(self, output: str) -> list:
        """Extract failure messages from pytest output."""
        failures = []
        
        # Look for FAILED lines
        for line in output.split('\n'):
            if 'FAILED' in line or 'AssertionError' in line:
                failures.append(line.strip())
        
        # Look for assertion details
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'assert' in line.lower() and i > 0:
                # Get some context
                context = lines[max(0, i-1):min(len(lines), i+3)]
                failures.append(" | ".join(context))
        
        return list(set(failures))[:10]  # Unique, limit to 10


if __name__ == "__main__":
    print("🧪 Testing Judge Agent...\n")
    
    from src.tools.file_manager import write_file, delete_file
    
    # Create test code
    code = """
def add(a, b):
    '''Add two numbers'''
    return a + b

def subtract(a, b):
    '''Subtract b from a'''
    return a - b
"""
    
    write_file("test_judge_demo.py", code)
    
    agent = JudgeAgent()
    result = agent.validate("test_judge_demo.py", "test_test_judge_demo.py")
    
    print(f"\n📊 Result:")
    print(f"   Success: {result['success']}")
    print(f"   Tests Passed: {result.get('tests_passed', False)}")
    
    # Cleanup
    delete_file("test_judge_demo.py")
    if Path(SANDBOX_DIR / "test_test_judge_demo.py").exists():
        delete_file("test_test_judge_demo.py")
    
    print("\n✅ Judge test complete!")