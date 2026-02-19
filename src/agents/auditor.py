"""
Auditor Agent - Analyzes code using static analysis only (no LLM calls).
Saves API quota for Fixer and Judge which need LLM.
"""
import sys
import ast
import subprocess
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.analyzer import CodeAnalyzer
from src.utils.logger import log_experiment, ActionType


class AuditorAgent:
    """Agent responsible for auditing code quality using static analysis."""

    def __init__(self):
        """Initialize the Auditor agent."""
        self.name = "Auditor"
        print(f"✅ {self.name} agent initialized")

    def analyze(self, file_path: str) -> Dict:
        """
        Analyze a Python file using static analysis tools only.

        Args:
            file_path: Absolute path to the Python file to analyze.

        Returns:
            Dictionary with keys: success, issues, quality_score, summary, file_path
        """
        abs_path = Path(file_path).resolve()
        display_name = abs_path.name
        print(f"🔍 {self.name}: Analyzing {display_name}...")

        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                code_content = f.read()

            analyzer = CodeAnalyzer(str(abs_path))
            analysis_results = analyzer.analyze()
            report = analyzer.generate_report()

            syntax_valid = analysis_results['syntax']['valid']

            if not syntax_valid:
                print(f"   ❌ Syntax error detected!")
                issues = [{
                    "severity": "critical",
                    "type": "syntax",
                    "line": analysis_results['syntax']['errors'][0]['line'],
                    "message": analysis_results['syntax']['message']
                }]
                log_experiment(
                    agent_name=self.name,
                    model_used="static_analysis",
                    action=ActionType.ANALYSIS,
                    details={
                        "file_analyzed": file_path,
                        "input_prompt": f"Static analysis of {display_name}",
                        "output_response": analysis_results['syntax']['message'],
                        "syntax_valid": False
                    },
                    status="SUCCESS"
                )
                return {
                    "success": True,
                    "issues": issues,
                    "quality_score": 0.0,
                    "summary": "Critical syntax error prevents execution",
                    "file_path": file_path
                }

            all_issues = []

            # Style issues
            for issue in analysis_results.get('style', {}).get('issues', [])[:10]:
                all_issues.append({
                    "severity": "minor",
                    "type": "style",
                    "line": issue['line'],
                    "message": issue['message']
                })

            # Security issues
            for issue in analysis_results.get('security', {}).get('issues', []):
                all_issues.append({
                    "severity": issue['severity'],
                    "type": "security",
                    "line": 0,
                    "message": issue['message']
                })

            # Complexity issues
            for func in analysis_results.get('complexity', {}).get('functions', []):
                if func['complexity'] > 5:
                    all_issues.append({
                        "severity": "major",
                        "type": "complexity",
                        "line": func['line'],
                        "message": f"Function '{func['name']}' complexity={func['complexity']}"
                    })

            # Missing docstrings via AST
            try:
                tree = ast.parse(code_content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        has_doc = (
                            node.body
                            and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        )
                        if not has_doc:
                            all_issues.append({
                                "severity": "minor",
                                "type": "documentation",
                                "line": node.lineno,
                                "message": f"Missing docstring in '{node.name}'"
                            })
            except Exception:
                pass

            # Pylint (no network, no LLM)
            pylint_summary = self._run_pylint(str(abs_path))

            quality_score = 10.0
            quality_score -= len(analysis_results.get('style', {}).get('issues', [])) * 0.1
            quality_score -= len(analysis_results.get('security', {}).get('issues', [])) * 1.0
            quality_score -= (
                analysis_results.get('complexity', {}).get('overall_complexity', 0) / 10
            ) * 0.5
            quality_score = max(0.0, min(10.0, quality_score))

            summary = (
                f"Static analysis: {len(all_issues)} issues found. "
                f"Pylint: {pylint_summary}. "
                f"Estimated score: {quality_score:.1f}/10"
            )

            log_experiment(
                agent_name=self.name,
                model_used="static_analysis+pylint",
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": file_path,
                    "input_prompt": f"Static analysis of {display_name}",
                    "output_response": report,
                    "quality_score": quality_score,
                    "issues_found": len(all_issues),
                    "pylint_summary": pylint_summary
                },
                status="SUCCESS"
            )

            print(f"   ✅ Analysis complete: {len(all_issues)} issues, score: {quality_score:.2f}/10")
            return {
                "success": True,
                "issues": all_issues,
                "quality_score": quality_score,
                "summary": summary,
                "file_path": file_path
            }

        except Exception as e:
            error_msg = f"Error analyzing {file_path}: {str(e)}"
            print(f"   ❌ {error_msg}")
            log_experiment(
                agent_name=self.name,
                model_used="static_analysis",
                action=ActionType.ANALYSIS,
                details={
                    "file_analyzed": file_path,
                    "input_prompt": f"Static analysis of {file_path}",
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

    def _run_pylint(self, file_path: str) -> str:
        """Run pylint and return a short summary string."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pylint", file_path,
                 "--output-format=text", "--score=yes",
                 "--disable=C0301"],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.splitlines():
                if "Your code has been rated" in line:
                    return line.strip()
            return result.stdout[-300:] if result.stdout else "pylint ok"
        except Exception as e:
            return f"pylint skipped: {e}"