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
from src.utils.config import GROQ_API_KEY, DEFAULT_MODEL, SANDBOX_DIR

from langchain_groq import ChatGroq


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

        self.llm = ChatGroq(
            model=DEFAULT_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=0.3
        )

        self.system_prompt = self._load_prompt()
        print(f"✅ {self.name} agent initialized")

    def _load_prompt(self) -> str:
        """Load the system prompt for the Judge."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "judge_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return """You are an expert test validator and test generator.
Your task is to generate comprehensive unit tests that validate code behavior.
Generate tests that check what the code SHOULD do, not just what it does."""

    def validate(self, file_path: str, test_file: str) -> Dict:
        """
        Validate code by generating and running tests.

        Args:
            file_path: Path to the code file (relative to sandbox)
            test_file: Path where test file should be created (relative to sandbox)

        Returns:
            Dictionary with validation results
        """
        print(f"⚖️  {self.name}: Validating {file_path}...")

        try:
            # Resolve absolute paths
            code_abs = SANDBOX_DIR / file_path
            test_abs = SANDBOX_DIR / test_file

            # Always regenerate tests to ensure they reflect the current code state
            # (avoids running stale tests from previous iterations)
            print(f"   🔄 Generating fresh tests for iteration...")
            generation_result = self._generate_tests(file_path, test_file)

            if not generation_result.get("success", False):
                # Fall back to existing test file if generation fails
                if not test_abs.exists():
                    return {
                        "success": False,
                        "tests_passed": False,
                        "error": f"Failed to generate tests: {generation_result.get('error', 'Unknown')}"
                    }
                print(f"   ⚠️  Generation failed, using existing test file")

            print(f"   🧪 Running tests...")

            # Run pytest with sandbox in sys.path so imports work correctly
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_abs),          # absolute path to test file
                "-v",
                "--tb=short",
                "--color=no",
                f"--rootdir={SANDBOX_DIR}",   # set rootdir to sandbox
            ]

            # Set PYTHONPATH so the test file can import from sandbox
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(SANDBOX_DIR) + (
                os.pathsep + existing_pythonpath if existing_pythonpath else ""
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                cwd=str(SANDBOX_DIR)   # run from sandbox so relative imports work
            )

            output = result.stdout + result.stderr

            # Detect "no tests collected" explicitly
            if "no tests ran" in output.lower() or "no tests collected" in output.lower() or \
               ("collected 0 items" in output):
                print(f"   ⚠️  No tests collected — test file may have import errors")
                print(f"   Pytest output:\n{output[:500]}")

                log_experiment(
                    agent_name=self.name,
                    model_used="pytest",
                    action=ActionType.DEBUG,
                    details={
                        "file_validated": file_path,
                        "test_file": test_file,
                        "input_prompt": f"Running tests for {file_path}",
                        "output_response": output[:1000],
                        "issue": "no_tests_collected"
                    },
                    status="FAILURE"
                )

                return {
                    "success": True,
                    "tests_passed": False,
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "feedback": (
                        "❌ No tests were collected by pytest. "
                        "The test file likely has an import error. "
                        f"Pytest output:\n{output[:500]}"
                    ),
                    "failures": ["No tests collected - possible import error in test file"]
                }

            passed, failed, total = self._parse_pytest_output(output)
            tests_passed = (result.returncode == 0 and failed == 0 and passed > 0)

            print(f"   📊 Test Results: {passed}/{total} passed")

            if tests_passed:
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
                print(f"   ❌ {failed} test(s) failed")
                failures = self._extract_failure_messages(output)

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
            error_msg = "Tests timed out after 60 seconds"
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
            return {"success": False, "tests_passed": False, "error": error_msg}

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
            return {"success": False, "tests_passed": False, "error": error_msg}

    def _generate_tests(self, file_path: str, test_file: str) -> Dict:
        """
        Generate test file using LLM based on code analysis.

        Args:
            file_path: Path to code file (relative to sandbox)
            test_file: Path where test should be created (relative to sandbox)

        Returns:
            Dictionary with generation result
        """
        try:
            code_content = read_file(file_path)
            module_name = Path(file_path).stem

            user_prompt = f"""You are a test generation expert. Generate comprehensive pytest unit tests.

CRITICAL INSTRUCTIONS:
1. Analyze the code and understand what each function/class SHOULD do based on:
   - Function/method names (semantics)
   - Parameter names and types
   - Return value expectations
   - Business logic inferred from context

2. Generate tests that validate CORRECT behavior, NOT current buggy behavior.
3. Include edge cases (empty inputs, zero, negative numbers, boundary values).
4. Test ALL public functions and classes in the module.
5. Use ONLY pytest-style functions (def test_*), NOT unittest.TestCase.
6. DO NOT use unittest at all.

CRITICAL - MATCH THE CODE STRUCTURE EXACTLY:
- If the code has standalone functions like "def add(x, y):", import them directly:
  from {module_name} import add
- If the code has classes, instantiate them properly:
  obj = MyClass(); result = obj.method()
- DO NOT convert standalone functions into class methods

CODE TO TEST (file: {module_name}.py):
```python
{code_content}
```

REQUIRED OUTPUT FORMAT - return ONLY this, no explanations:
```python
import pytest
from {module_name} import <list all functions and classes here>

def test_function_normal_case():
    assert function(input) == expected_correct_output

def test_function_edge_case():
    assert function(edge_input) == expected_correct_output

# ... more tests covering all functions
```

Generate the complete test file now:
"""

            response = self.llm.invoke(user_prompt)
            test_code = response.content
            test_code = self._extract_code_from_response(test_code)

            if "def test_" not in test_code or "assert" not in test_code:
                return {
                    "success": False,
                    "error": "Generated code doesn't contain valid pytest tests"
                }

            # Remove any unittest imports/usage that might have slipped in
            # and ensure no __name__ == "__main__" blocks that confuse pytest
            test_code = self._clean_test_code(test_code, module_name)

            write_file(test_file, test_code)

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

            print(f"   ✅ Generated {test_code.count('def test_')} test(s) → {test_file}")

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
            return {"success": False, "error": error_msg}

    def _clean_test_code(self, test_code: str, module_name: str) -> str:
        """
        Clean generated test code:
        - Remove unittest imports and TestCase usage
        - Remove if __name__ == '__main__' blocks
        - Ensure pytest import is present
        """
        lines = test_code.split('\n')
        cleaned = []
        skip_block = False

        for line in lines:
            # Skip unittest imports
            if 'import unittest' in line:
                continue
            # Skip class definitions that extend unittest.TestCase
            if 'unittest.TestCase' in line:
                skip_block = True
                continue
            # Skip __main__ block
            if line.strip().startswith("if __name__"):
                skip_block = True
                continue
            # End of a skipped indented block
            if skip_block and line and not line[0].isspace():
                skip_block = False

            if not skip_block:
                cleaned.append(line)

        result = '\n'.join(cleaned)

        # Ensure pytest is imported
        if 'import pytest' not in result:
            result = 'import pytest\n' + result

        return result

    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from LLM response."""
        pattern = r'```python\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        pattern = r'```\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        return response.strip()

    def _parse_pytest_output(self, output: str) -> tuple:
        """Parse pytest output to extract test counts."""
        passed = 0
        failed = 0

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

        for line in output.split('\n'):
            if 'FAILED' in line or 'AssertionError' in line:
                failures.append(line.strip())

        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'assert' in line.lower() and i > 0:
                context = lines[max(0, i-1):min(len(lines), i+3)]
                failures.append(" | ".join(context))

        return list(set(failures))[:10]