#!/usr/bin/env python3
"""
Main Entry Point for the Refactoring Swarm
Parses command-line arguments and launches the orchestrator.
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.orchestrator import Orchestrator
from src.utils.config import SANDBOX_DIR


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Refactoring Swarm - Autonomous Code Refactoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --target_dir ./sandbox/test_dataset
  python main.py --target_dir /path/to/buggy/code

The system will:
1. Find all Python files in the target directory
2. For each file:
   - Auditor analyzes and identifies issues
   - Fixer corrects the code
   - Judge validates with tests
   - Loop up to 10 iterations if tests fail
3. Generate a summary report
        """
    )
    
    parser.add_argument(
        '--target_dir',
        type=str,
        required=True,
        help='Directory containing Python files to refactor'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=10,
        help='Maximum iterations per file (default: 10)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Print banner
    print("\n" + "="*70)
    print("🤖 REFACTORING SWARM - Autonomous Code Refactoring System")
    print("="*70)
    print(f"Target Directory: {args.target_dir}")
    print(f"Max Iterations: {args.max_iterations}")
    print("="*70 + "\n")
    
    try:
        # Resolve target directory
        target_dir = Path(args.target_dir).resolve()
        
        # Check if directory exists
        if not target_dir.exists():
            print(f"❌ Error: Target directory does not exist: {target_dir}")
            print(f"   Please provide a valid directory path")
            return 1
        
        if not target_dir.is_dir():
            print(f"❌ Error: Target path is not a directory: {target_dir}")
            return 1
        
        # Initialize orchestrator
        orchestrator = Orchestrator(str(target_dir))
        
        # Update max iterations if specified
        if args.max_iterations != 10:
            from src.utils import config
            config.MAX_ITERATIONS = args.max_iterations
        
        # Run the refactoring process
        results = orchestrator.process_all_files()
        
        # Determine exit code based on results
        if results['failed'] == 0 and results['total_files'] > 0:
            print("\n🎉 SUCCESS: All files refactored successfully!")
            return 0
        elif results['total_files'] == 0:
            print("\n⚠️  WARNING: No Python files found to process")
            return 0
        else:
            print(f"\n⚠️  PARTIAL SUCCESS: {results['successful']}/{results['total_files']} files refactored")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)