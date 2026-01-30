"""
Code Analyzer Tool
Performs static analysis on Python code including:
- Syntax validation
- Code complexity metrics
- Style checking
- Security vulnerabilities detection
"""

import ast
import os
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess


class CodeAnalyzer:
    """Analyzes Python code for quality, complexity, and potential issues."""
    
    def __init__(self, file_path: str):
        """
        Initialize the analyzer with a Python file.
        
        Args:
            file_path: Path to the Python file to analyze
        """
        self.file_path = Path(file_path)
        self.code = self._read_file()
        self.tree = None
        self.analysis_results = {
            'syntax': {},
            'complexity': {},
            'style': {},
            'security': {},
            'metrics': {}
        }
    
    def _read_file(self) -> str:
        """Read the content of the file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except Exception as e:
            raise Exception(f"Error reading file: {e}")
    
    def check_syntax(self) -> Dict[str, Any]:
        """
        Check if the code has valid Python syntax.
        
        Returns:
            Dictionary with syntax validation results
        """
        try:
            self.tree = ast.parse(self.code)
            self.analysis_results['syntax'] = {
                'valid': True,
                'message': 'Syntax is valid',
                'errors': []
            }
        except SyntaxError as e:
            self.analysis_results['syntax'] = {
                'valid': False,
                'message': f'Syntax error at line {e.lineno}',
                'errors': [{
                    'line': e.lineno,
                    'offset': e.offset,
                    'message': e.msg,
                    'text': e.text
                }]
            }
        return self.analysis_results['syntax']
    
    def calculate_complexity(self) -> Dict[str, Any]:
        """
        Calculate code complexity metrics.
        
        Returns:
            Dictionary with complexity metrics
        """
        if not self.tree:
            self.check_syntax()
        
        if not self.tree:
            return {'error': 'Cannot calculate complexity due to syntax errors'}
        
        complexity_data = {
            'functions': [],
            'classes': [],
            'overall_complexity': 0
        }
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                complexity_data['functions'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'complexity': complexity,
                    'args_count': len(node.args.args)
                })
                complexity_data['overall_complexity'] += complexity
            
            elif isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                complexity_data['classes'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods_count': len(methods)
                })
        
        self.analysis_results['complexity'] = complexity_data
        return complexity_data
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity for a function.
        
        Args:
            node: AST node representing a function
            
        Returns:
            Cyclomatic complexity score
        """
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def check_style(self) -> Dict[str, Any]:
        """
        Check code style issues.
        
        Returns:
            Dictionary with style check results
        """
        issues = []
        
        lines = self.code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 79:
                issues.append({
                    'line': i,
                    'type': 'line_length',
                    'message': f'Line too long ({len(line)} > 79 characters)'
                })
            
            # Check trailing whitespace
            if line.rstrip() != line and line.strip():
                issues.append({
                    'line': i,
                    'type': 'trailing_whitespace',
                    'message': 'Trailing whitespace'
                })
            
            # Check multiple statements on one line
            if ';' in line and not line.strip().startswith('#'):
                issues.append({
                    'line': i,
                    'type': 'multiple_statements',
                    'message': 'Multiple statements on one line'
                })
        
        self.analysis_results['style'] = {
            'issues_count': len(issues),
            'issues': issues
        }
        
        return self.analysis_results['style']
    
    def check_security(self) -> Dict[str, Any]:
        """
        Check for common security vulnerabilities.
        
        Returns:
            Dictionary with security issues
        """
        issues = []
        
        # Check for eval/exec usage
        if re.search(r'\beval\s*\(', self.code):
            issues.append({
                'type': 'dangerous_function',
                'severity': 'high',
                'message': 'Use of eval() detected - potential security risk'
            })
        
        if re.search(r'\bexec\s*\(', self.code):
            issues.append({
                'type': 'dangerous_function',
                'severity': 'high',
                'message': 'Use of exec() detected - potential security risk'
            })
        
        # Check for hardcoded passwords/secrets
        password_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
        ]
        
        for pattern in password_patterns:
            matches = re.finditer(pattern, self.code, re.IGNORECASE)
            for match in matches:
                issues.append({
                    'type': 'hardcoded_secret',
                    'severity': 'medium',
                    'message': f'Possible hardcoded secret: {match.group()}'
                })
        
        # Check for SQL injection vulnerabilities
        if re.search(r'execute\s*\([^)]*%s[^)]*\)', self.code):
            issues.append({
                'type': 'sql_injection',
                'severity': 'high',
                'message': 'Possible SQL injection vulnerability'
            })
        
        self.analysis_results['security'] = {
            'issues_count': len(issues),
            'issues': issues
        }
        
        return self.analysis_results['security']
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate various code metrics.
        
        Returns:
            Dictionary with code metrics
        """
        lines = self.code.split('\n')
        
        metrics = {
            'total_lines': len(lines),
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'docstring_lines': 0
        }
        
        in_docstring = False
        docstring_char = None
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                metrics['blank_lines'] += 1
            elif stripped.startswith('#'):
                metrics['comment_lines'] += 1
            elif '"""' in stripped or "'''" in stripped:
                if not in_docstring:
                    in_docstring = True
                    docstring_char = '"""' if '"""' in stripped else "'''"
                    metrics['docstring_lines'] += 1
                else:
                    metrics['docstring_lines'] += 1
                    in_docstring = False
            elif in_docstring:
                metrics['docstring_lines'] += 1
            else:
                metrics['code_lines'] += 1
        
        self.analysis_results['metrics'] = metrics
        return metrics
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete analysis of the code.
        
        Returns:
            Dictionary with all analysis results
        """
        self.check_syntax()
        
        if self.analysis_results['syntax']['valid']:
            self.calculate_complexity()
            self.check_style()
            self.check_security()
            self.calculate_metrics()
        
        return self.analysis_results
    
    def generate_report(self) -> str:
        """
        Generate a human-readable report of the analysis.
        
        Returns:
            Formatted report string
        """
        if not self.analysis_results['syntax']:
            self.analyze()
        
        report = []
        report.append("=" * 60)
        report.append(f"CODE ANALYSIS REPORT: {self.file_path.name}")
        report.append("=" * 60)
        report.append("")
        
        # Syntax
        report.append("📝 SYNTAX CHECK:")
        if self.analysis_results['syntax']['valid']:
            report.append("  ✅ No syntax errors")
        else:
            report.append(f"  ❌ {self.analysis_results['syntax']['message']}")
            for error in self.analysis_results['syntax']['errors']:
                report.append(f"     Line {error['line']}: {error['message']}")
        report.append("")
        
        # Metrics
        if 'metrics' in self.analysis_results:
            metrics = self.analysis_results['metrics']
            report.append("📊 CODE METRICS:")
            report.append(f"  Total lines: {metrics['total_lines']}")
            report.append(f"  Code lines: {metrics['code_lines']}")
            report.append(f"  Comment lines: {metrics['comment_lines']}")
            report.append(f"  Blank lines: {metrics['blank_lines']}")
            report.append(f"  Docstring lines: {metrics['docstring_lines']}")
            report.append("")
        
        # Complexity
        if 'complexity' in self.analysis_results:
            complexity = self.analysis_results['complexity']
            if 'error' not in complexity:
                report.append("🔄 COMPLEXITY ANALYSIS:")
                report.append(f"  Overall complexity: {complexity['overall_complexity']}")
                report.append(f"  Functions: {len(complexity['functions'])}")
                report.append(f"  Classes: {len(complexity['classes'])}")
                
                if complexity['functions']:
                    report.append("  High complexity functions:")
                    for func in sorted(complexity['functions'], 
                                     key=lambda x: x['complexity'], 
                                     reverse=True)[:5]:
                        if func['complexity'] > 10:
                            report.append(f"    - {func['name']} (line {func['line']}): "
                                        f"complexity = {func['complexity']}")
                report.append("")
        
        # Style
        if 'style' in self.analysis_results:
            style = self.analysis_results['style']
            report.append(f"🎨 STYLE ISSUES: {style['issues_count']}")
            if style['issues_count'] > 0:
                for issue in style['issues'][:10]:  # Show first 10
                    report.append(f"  Line {issue['line']}: {issue['message']}")
                if style['issues_count'] > 10:
                    report.append(f"  ... and {style['issues_count'] - 10} more")
            else:
                report.append("  ✅ No style issues found")
            report.append("")
        
        # Security
        if 'security' in self.analysis_results:
            security = self.analysis_results['security']
            report.append(f"🔒 SECURITY ISSUES: {security['issues_count']}")
            if security['issues_count'] > 0:
                for issue in security['issues']:
                    severity_emoji = "🔴" if issue['severity'] == 'high' else "🟡"
                    report.append(f"  {severity_emoji} [{issue['severity'].upper()}] "
                                f"{issue['message']}")
            else:
                report.append("  ✅ No security issues found")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def analyze_file(file_path: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Convenience function to analyze a file.
    
    Args:
        file_path: Path to the Python file to analyze
        verbose: If True, print the report
        
    Returns:
        Analysis results dictionary
    """
    analyzer = CodeAnalyzer(file_path)
    results = analyzer.analyze()
    
    if verbose:
        print(analyzer.generate_report())
    
    return results


# Test the analyzer if run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Analyze this file as a test
        file_path = __file__
    
    print(f"\n🔍 Analyzing: {file_path}\n")
    analyze_file(file_path, verbose=True)