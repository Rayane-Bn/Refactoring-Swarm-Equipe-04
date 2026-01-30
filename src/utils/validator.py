"""
Validator - Checks experiment_data.json for completeness and validity.
Data Officer: Responsible for ensuring log quality.
"""
import json
import os
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent.parent / "logs" / "experiment_data.json"

def validate_logs():
    """Validate the experiment logs file."""
    print("🔍 Validating experiment logs...\n")
    
    if not LOG_FILE.exists():
        print("❌ logs/experiment_data.json does not exist!")
        print("   → Run the system first to generate logs")
        return False
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            print("⚠️  Log file is empty!")
            return False
            
        print(f"✅ Valid JSON with {len(data)} entries\n")
        
        # Check required fields
        required_fields = ["id", "timestamp", "agent", "model", "action", "details", "status"]
        
        valid_count = 0
        error_count = 0
        
        for idx, entry in enumerate(data):
            missing = [f for f in required_fields if f not in entry]
            if missing:
                print(f"❌ Entry {idx}: Missing fields: {missing}")
                error_count += 1
                continue
            
            # Check prompts in details for LLM actions
            if "details" in entry:
                details = entry["details"]
                action = entry.get("action", "")
                
                # These actions MUST have prompts logged
                if action in ["CODE_ANALYSIS", "CODE_GEN", "DEBUG", "FIX"]:
                    if "input_prompt" not in details:
                        print(f"❌ Entry {idx} ({action}): Missing 'input_prompt'")
                        error_count += 1
                        continue
                    
                    if "output_response" not in details:
                        print(f"❌ Entry {idx} ({action}): Missing 'output_response'")
                        error_count += 1
                        continue
            
            valid_count += 1
        
        print(f"\n📊 Validation Summary:")
        print(f"   ✅ Valid entries: {valid_count}")
        print(f"   ❌ Invalid entries: {error_count}")
        
        if error_count == 0:
            print("\n✅ All entries have required fields")
            print("✅ All prompts are logged correctly")
            print("\n🎉 LOG FILE IS READY FOR SUBMISSION!")
            return True
        else:
            print("\n⚠️  LOG FILE HAS ISSUES - Fix before submission!")
            return False
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return False

if __name__ == "__main__":
    success = validate_logs()
    exit(0 if success else 1)