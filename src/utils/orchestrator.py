"""
Orchestrator - Coordinates the refactoring workflow between agents.

This module manages the execution flow:
1. Auditor analyzes code
2. Fixer corrects issues
3. Judge validates with tests
4. Loop back if tests fail (max 10 iterations)
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import MAX_ITERATIONS, SANDBOX_DIR
from src.tools.file_manager import list_python_files, read_file, get_file_info
from src.tools.analyzer import run_pylint, analyze_code_quality
from src.tools.tester import run_pytest, check_tests_exist

# Import agents (will be implemented by team members)
from src.agents.auditor import AuditorAgent
from src.agents.fixer import FixerAgent
from src.agents.judge import JudgeAgent


class Orchestrator:
    """
    Main orchestrator that coordinates the refactoring swarm.
    """
    
    def __init__(self, target_dir: str):
        """
        Initialize the orchestrator.
        
        Args:
            target_dir: Path to directory containing code to refactor
        """
        self.target_dir = Path(target_dir)
        
        if not self.target_dir.exists():
            raise ValueError(f"Target directory does not exist: {target_dir}")
        
        # Initialize agents
        self.auditor = AuditorAgent()
        self.fixer = FixerAgent()
        self.judge = JudgeAgent()
        
        # Track results
        self.results = {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "files": {}
        }
        
        print(f"🚀 Orchestrator initialized for: {self.target_dir}")
    
    def find_python_files(self) -> List[str]:
        """
        Find all Python files to process (excluding test files).
        
        Returns:
            List of Python file paths relative to target_dir
        """
        # Get all Python files in target directory
        all_files = list_python_files(str(self.target_dir.relative_to(SANDBOX_DIR)))
        
        # Filter out test files (files starting with 'test_' or ending with '_test.py')
        code_files = [
            f for f in all_files 
            if not (Path(f).name.startswith('test_') or Path(f).name.endswith('_test.py'))
        ]
        
        print(f"📁 Found {len(code_files)} Python file(s) to process")
        for f in code_files:
            print(f"   - {f}")
        
        return code_files
    
    def find_test_file(self, code_file: str) -> Optional[str]:
        """
        Find the corresponding test file for a code file.
        
        Args:
            code_file: Path to code file
            
        Returns:
            Path to test file, or None if not found
        """
        code_path = Path(code_file)
        
        # Try common test file naming patterns
        possible_names = [
            f"test_{code_path.name}",  # test_module.py
            f"{code_path.stem}_test.py"  # module_test.py
        ]
        
        for test_name in possible_names:
            test_path = code_path.parent / test_name
            full_test_path = self.target_dir / test_path
            
            if full_test_path.exists():
                return str(test_path)
        
        return None
    
    def process_all_files(self) -> Dict:
        """
        Process all Python files in the target directory.
        
        Returns:
            Summary dictionary with results for all files
        """
        print("\n" + "="*70)
        print("🔧 STARTING REFACTORING SWARM")
        print("="*70 + "\n")
        
        start_time = time.time()
        
        # Find all Python files to process
        code_files = self.find_python_files()
        self.results["total_files"] = len(code_files)
        
        if len(code_files) == 0:
            print("⚠️  No Python files found to process!")
            return self.results
        
        # Process each file sequentially
        for idx, code_file in enumerate(code_files, 1):
            print(f"\n{'='*70}")
            print(f"📄 Processing File {idx}/{len(code_files)}: {code_file}")
            print(f"{'='*70}\n")
            
            result = self.refactor_single_file(code_file)
            self.results["files"][code_file] = result
            
            if result["status"] == "SUCCESS":
                self.results["successful"] += 1
            else:
                self.results["failed"] += 1
        
        # Print final summary
        elapsed_time = time.time() - start_time
        self._print_final_summary(elapsed_time)
        
        return self.results
    
    def refactor_single_file(self, file_path: str) -> Dict:
        """
        Refactor a single Python file using the agent workflow.
        
        Args:
            file_path: Path to Python file (relative to sandbox)
            
        Returns:
            Dictionary with refactoring results for this file
        """
        result = {
            "status": "UNKNOWN",
            "iterations": 0,
            "initial_score": 0.0,
            "final_score": 0.0,
            "score_improvement": 0.0,
            "test_file": None,
            "error": None
        }
        
        # Get initial code quality score
        initial_analysis = analyze_code_quality(file_path)
        result["initial_score"] = initial_analysis.get("score", 0.0)
        
        print(f"📊 Initial Pylint Score: {result['initial_score']:.2f}/10")
        
        # Find corresponding test file
        test_file = self.find_test_file(file_path)
        result["test_file"] = test_file
        
        if not test_file:
            print(f"⚠️  WARNING: No test file found for {file_path}")
            print(f"   Expected: test_{Path(file_path).name} or {Path(file_path).stem}_test.py")
            result["status"] = "NO_TESTS"
            result["error"] = "No test file found"
            return result
        
        print(f"✅ Found test file: {test_file}")
        
        # Main refactoring loop (max 10 iterations)
        for iteration in range(1, MAX_ITERATIONS + 1):
            result["iterations"] = iteration
            
            print(f"\n{'─'*70}")
            print(f"🔄 ITERATION {iteration}/{MAX_ITERATIONS}")
            print(f"{'─'*70}\n")
            
            # Step 1: Auditor analyzes the code
            print("🔍 Step 1: Auditor analyzing code...")
            try:
                audit_result = self.auditor.analyze(file_path)
                
                if not audit_result.get("success", False):
                    result["status"] = "AUDIT_FAILED"
                    result["error"] = audit_result.get("error", "Audit failed")
                    print(f"❌ Audit failed: {result['error']}")
                    break
                
                issues = audit_result.get("issues", [])
                print(f"   Found {len(issues)} issue(s)")
                
            except Exception as e:
                result["status"] = "AUDIT_ERROR"
                result["error"] = str(e)
                print(f"❌ Auditor error: {e}")
                break
            
            # Step 2: Fixer corrects the code
            print("\n🔧 Step 2: Fixer correcting code...")
            try:
                fix_result = self.fixer.fix(file_path, audit_result)
                
                if not fix_result.get("success", False):
                    result["status"] = "FIX_FAILED"
                    result["error"] = fix_result.get("error", "Fix failed")
                    print(f"❌ Fix failed: {result['error']}")
                    break
                
                print(f"   ✅ Code fixed and saved")
                
            except Exception as e:
                result["status"] = "FIX_ERROR"
                result["error"] = str(e)
                print(f"❌ Fixer error: {e}")
                break
            
            # Step 3: Judge validates with tests
            print("\n⚖️  Step 3: Judge running tests...")
            try:
                judge_result = self.judge.validate(file_path, test_file)
                
                tests_passed = judge_result.get("tests_passed", False)
                passed_count = judge_result.get("passed", 0)
                failed_count = judge_result.get("failed", 0)
                
                print(f"   Tests: {passed_count} passed, {failed_count} failed")
                
                if tests_passed:
                    # SUCCESS! All tests passed
                    result["status"] = "SUCCESS"
                    print(f"\n🎉 SUCCESS! All tests passed in iteration {iteration}")
                    break
                else:
                    # Tests failed, continue loop
                    print(f"\n⚠️  Tests failed. Continuing to iteration {iteration + 1}...")
                    
                    if iteration == MAX_ITERATIONS:
                        result["status"] = "MAX_ITERATIONS"
                        result["error"] = f"Failed after {MAX_ITERATIONS} iterations"
                        print(f"\n❌ Maximum iterations ({MAX_ITERATIONS}) reached")
                
            except Exception as e:
                result["status"] = "JUDGE_ERROR"
                result["error"] = str(e)
                print(f"❌ Judge error: {e}")
                break
        
        # Get final code quality score
        final_analysis = analyze_code_quality(file_path)
        result["final_score"] = final_analysis.get("score", 0.0)
        result["score_improvement"] = result["final_score"] - result["initial_score"]
        
        print(f"\n📊 Final Pylint Score: {result['final_score']:.2f}/10")
        print(f"📈 Improvement: {result['score_improvement']:+.2f}")
        
        return result
    
    def _print_final_summary(self, elapsed_time: float):
        """
        Print a final summary of all refactoring results.
        
        Args:
            elapsed_time: Total elapsed time in seconds
        """
        print("\n" + "="*70)
        print("📊 FINAL SUMMARY")
        print("="*70)
        
        print(f"\n⏱️  Total Time: {elapsed_time:.2f} seconds")
        print(f"📁 Total Files: {self.results['total_files']}")
        print(f"✅ Successful: {self.results['successful']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results["files"]:
            print("\n📋 Detailed Results:")
            print("-"*70)
            
            for file_path, result in self.results["files"].items():
                status_symbol = "✅" if result["status"] == "SUCCESS" else "❌"
                print(f"\n{status_symbol} {file_path}")
                print(f"   Status: {result['status']}")
                print(f"   Iterations: {result['iterations']}")
                print(f"   Score: {result['initial_score']:.2f} → {result['final_score']:.2f} ({result['score_improvement']:+.2f})")
                
                if result.get("error"):
                    print(f"   Error: {result['error']}")
        
        print("\n" + "="*70)
        
        # Overall result
        if self.results["failed"] == 0:
            print("🎉 ALL FILES SUCCESSFULLY REFACTORED!")
        else:
            print(f"⚠️  {self.results['failed']} file(s) could not be fully refactored")
        
        print("="*70 + "\n")


def main():
    """Test the orchestrator with a sample directory."""
    import sys
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        print("Usage: python orchestrator.py <target_dir>")
        print("Example: python orchestrator.py ./sandbox/test_dataset")
        return
    
    orchestrator = Orchestrator(target)
    results = orchestrator.process_all_files()
    
    # Exit with appropriate code
    if results["failed"] == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()