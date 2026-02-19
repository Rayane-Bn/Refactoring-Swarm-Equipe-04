"""
Orchestrator - Coordinates the refactoring workflow between agents.
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import MAX_ITERATIONS, SANDBOX_DIR
from src.tools.analyzer import CodeAnalyzer
from src.agents.auditor import AuditorAgent
from src.agents.fixer import FixerAgent
from src.agents.judge import JudgeAgent

# Rate-limit protection: pause between LLM calls
# Gemini free tier = 15 req/min, 20 req/day on gemini-2.5-flash
# Each iteration uses 2 LLM calls (Fixer + Judge).
# With 3s between agents we stay well under the per-minute limit.
INTER_AGENT_SLEEP = 4   # seconds between Fixer and Judge within one iteration
INTER_ITER_SLEEP  = 6   # seconds between full iterations


class Orchestrator:
    """Main orchestrator that coordinates the refactoring swarm."""

    def __init__(self, target_dir: str):
        """
        Initialize the orchestrator.

        Args:
            target_dir: Path to directory containing code to refactor.
        """
        self.target_dir = Path(target_dir).resolve()
        if not self.target_dir.exists():
            raise ValueError(f"Target directory does not exist: {target_dir}")

        self.auditor = AuditorAgent()
        self.fixer = FixerAgent()
        self.judge = JudgeAgent()

        self.results = {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "files": {}
        }
        print(f"🚀 Orchestrator initialized for: {self.target_dir}")

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def find_python_files(self) -> List[str]:
        """Find all non-test Python files in target_dir."""
        python_files = []
        for item in sorted(self.target_dir.rglob("*.py")):
            name = item.name
            if name.startswith("test_") or name.endswith("_test.py"):
                continue
            if any(part.startswith(".") or part == "__pycache__"
                   for part in item.parts):
                continue
            python_files.append(str(item.relative_to(self.target_dir)))

        print(f"📁 Found {len(python_files)} Python file(s) to process")
        for f in python_files:
            print(f"   - {f}")
        return python_files

    def find_test_file(self, code_file: str) -> Optional[str]:
        """Return absolute path of existing test file, or None."""
        code_path = Path(code_file)
        for test_name in [f"test_{code_path.name}", f"{code_path.stem}_test.py"]:
            candidate = self.target_dir / code_path.parent / test_name
            if candidate.exists():
                return str(candidate)
        return None

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    def process_all_files(self) -> Dict:
        """Process every Python file in target_dir."""
        print("\n" + "="*70)
        print("🔧 STARTING REFACTORING SWARM")
        print("="*70 + "\n")

        start_time = time.time()
        code_files = self.find_python_files()
        self.results["total_files"] = len(code_files)

        if not code_files:
            print("⚠️  No Python files found to process!")
            return self.results

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

        self._print_final_summary(time.time() - start_time)
        return self.results

    def refactor_single_file(self, file_path: str) -> Dict:
        """
        Run the Audit → Fix → Judge loop on one file.

        file_path is relative to target_dir.
        All agents receive absolute paths.
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

        abs_code = self.target_dir / file_path
        result["initial_score"] = self._quality_score(abs_code)
        print(f"📊 Initial Quality Score: {result['initial_score']:.2f}/10")

        existing_test = self.find_test_file(file_path)
        abs_test = Path(existing_test) if existing_test else (
            self.target_dir / f"test_{Path(file_path).name}"
        )
        result["test_file"] = str(abs_test)

        if existing_test:
            print(f"ℹ️  Found existing test file: {abs_test.name}")
        else:
            print(f"ℹ️  No test file found — Judge will generate: {abs_test.name}")

        previous_test_feedback = None

        for iteration in range(1, MAX_ITERATIONS + 1):
            result["iterations"] = iteration

            print(f"\n{'─'*70}")
            print(f"🔄 ITERATION {iteration}/{MAX_ITERATIONS}")
            print(f"{'─'*70}\n")

            # ── Step 1: Audit (no LLM, free) ──────────────────────────
            print("🔍 Step 1: Auditor analyzing code...")
            try:
                audit_result = self.auditor.analyze(str(abs_code))
                if not audit_result.get("success", False):
                    result["status"] = "AUDIT_FAILED"
                    result["error"] = audit_result.get("error", "Audit failed")
                    print(f"❌ Audit failed: {result['error']}")
                    break

                issues = audit_result.get("issues", [])
                quality_score = audit_result.get("quality_score", 0.0)
                print(f"   Found {len(issues)} issue(s), score: {quality_score:.2f}/10")

                # Early exit: if no issues and high score and tests already passed
                if not issues and quality_score >= 8.0 and not previous_test_feedback:
                    print("   ✨ Code looks clean — jumping straight to Judge to verify")

            except Exception as e:
                result["status"] = "AUDIT_ERROR"
                result["error"] = str(e)
                print(f"❌ Auditor error: {e}")
                break

            # ── Step 2: Fix (uses 1 LLM call) ─────────────────────────
            # Skip fixer if code is clean AND no previous test failure
            skip_fixer = (
                not issues
                and quality_score >= 8.0
                and not previous_test_feedback
                and iteration == 1
            )

            if not skip_fixer:
                print("\n🔧 Step 2: Fixer correcting code...")
                try:
                    combined = audit_result.copy()
                    if previous_test_feedback:
                        combined.setdefault("issues", []).append({
                            "severity": "critical",
                            "type": "test_failure",
                            "line": 0,
                            "message": previous_test_feedback
                        })
                        combined["test_failures"] = previous_test_feedback

                    fix_result = self.fixer.fix(str(abs_code), combined)
                    if not fix_result.get("success", False):
                        result["status"] = "FIX_FAILED"
                        result["error"] = fix_result.get("error", "Fix failed")
                        print(f"❌ Fix failed: {result['error']}")
                        break

                    print(f"   ✅ Code fixed and saved")
                    time.sleep(INTER_AGENT_SLEEP)

                except Exception as e:
                    result["status"] = "FIX_ERROR"
                    result["error"] = str(e)
                    print(f"❌ Fixer error: {e}")
                    break
            else:
                print("\n🔧 Step 2: Skipping Fixer (code already clean)")

            # ── Step 3: Judge (uses 1 LLM call) ───────────────────────
            print("\n⚖️  Step 3: Judge running tests...")
            try:
                judge_result = self.judge.validate(str(abs_code), str(abs_test))

                passed  = judge_result.get("passed", 0)
                failed  = judge_result.get("failed", 0)
                passed_all = judge_result.get("tests_passed", False)

                print(f"   Tests: {passed} passed, {failed} failed")

                if passed_all:
                    result["status"] = "SUCCESS"
                    print(f"\n🎉 SUCCESS! All tests passed in iteration {iteration}")
                    break
                else:
                    previous_test_feedback = judge_result.get("feedback", "Tests failed")
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

            if iteration < MAX_ITERATIONS:
                print(f"   💤 Waiting {INTER_ITER_SLEEP}s before next iteration...")
                time.sleep(INTER_ITER_SLEEP)

        result["final_score"] = self._quality_score(abs_code)
        result["score_improvement"] = result["final_score"] - result["initial_score"]
        print(f"\n📊 Final Quality Score: {result['final_score']:.2f}/10")
        print(f"📈 Improvement: {result['score_improvement']:+.2f}")
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _quality_score(self, abs_path: Path) -> float:
        """Compute simple quality score from static analysis."""
        try:
            a = CodeAnalyzer(str(abs_path))
            a.analyze()
            style = a.analysis_results.get('style', {}).get('issues_count', 0)
            sec   = a.analysis_results.get('security', {}).get('issues_count', 0)
            return max(0.0, 10.0 - style * 0.2 - sec * 1.0)
        except Exception:
            return 0.0

    def _print_final_summary(self, elapsed: float):
        """Print summary of all results."""
        print("\n" + "="*70)
        print("📊 FINAL SUMMARY")
        print("="*70)
        print(f"\n⏱️  Total Time: {elapsed:.2f}s")
        print(f"📁 Total Files: {self.results['total_files']}")
        print(f"✅ Successful:  {self.results['successful']}")
        print(f"❌ Failed:      {self.results['failed']}")

        if self.results["files"]:
            print("\n📋 Detailed Results:")
            print("-"*70)
            for fp, r in self.results["files"].items():
                sym = "✅" if r["status"] == "SUCCESS" else "❌"
                print(f"\n{sym} {fp}")
                print(f"   Status:     {r['status']}")
                print(f"   Iterations: {r['iterations']}")
                print(f"   Score:      {r['initial_score']:.2f} → {r['final_score']:.2f} ({r['score_improvement']:+.2f})")
                if r.get("error"):
                    print(f"   Error:      {r['error']}")

        print("\n" + "="*70)
        if self.results["failed"] == 0:
            print("🎉 ALL FILES SUCCESSFULLY REFACTORED!")
        else:
            print(f"⚠️  {self.results['failed']} file(s) could not be fully refactored")
        print("="*70 + "\n")


def main():
    if len(sys.argv) > 1:
        Orchestrator(sys.argv[1]).process_all_files()
    else:
        print("Usage: python orchestrator.py <target_dir>")

if __name__ == "__main__":
    main()