"""
Code Change Analyzer using Google Gemini
Analyzes code files for outdated syntax and suggests modern updates.
"""

import os
import argparse
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
import json
import google.generativeai as genai

load_dotenv()

# Configure Gemini with API key from environment (SECURE!)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables!")

genai.configure(api_key=GEMINI_API_KEY)


class CodeChange(BaseModel):
    path: str
    old_content: str
    new_content: str
    reason: str


def get_all_files_recursively(root_directory):
    """
    Recursively collect all file paths under the specified directory.
    """
    all_files = []
    for root, dirs, files in os.walk(root_directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            all_files.append(file_path)
    return all_files


def analyze_file_with_llm(file_path):
    """
    Reads file content and queries Gemini to determine if it's out of date
    and what changes might be necessary. Returns a CodeChange object if applicable.
    """
    try:
        with open(file_path, 'r', encoding="utf-8", errors="ignore") as f:
            file_content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    # Create a user prompt for Gemini
    user_prompt = (
        "Analyze the following code and determine if the syntax is out of date. "
        "If it is out of date, respond with a JSON object in this exact format:\n\n"
        "{\n"
        '  "path": "relative/file/path",\n'
        '  "old_content": "The entire content of the file, before any changes are made.",\n'
        '  "new_content": "The updated content with modern syntax.",\n'
        '  "reason": "A short explanation of why the code is out of date."\n'
        "}\n\n"
        "If the code is already modern and up to date, respond with: {\"modern\": true}\n\n"
        f"Code to analyze:\n\n{file_content}"
    )

    try:
        # Use Gemini Flash for fast analysis
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        
        # Parse the JSON response
        response_text = response.text
        data = json.loads(response_text)
        
        # Check if code is already modern
        if data.get("modern"):
            return None
        
        # Validate and create CodeChange object
        code_change = CodeChange(**data)
        return code_change
        
    except json.JSONDecodeError as parse_error:
        print(f"Error parsing Gemini JSON response for {file_path}: {parse_error}")
        print(f"Response was: {response.text[:200]}...")
        return None
    except ValidationError as val_error:
        print(f"Invalid CodeChange format for {file_path}: {val_error}")
        return None
    except Exception as e:
        print(f"Error analyzing {file_path} with Gemini: {e}")
        return None


def fetch_updates(directory):
    """
    Fetches updates for all files in directory.
    Used by containers.py in Dependify.
    """
    analysis_results = []
    all_files = get_all_files_recursively(directory)
    
    for filepath in all_files:
        # Skip hidden files, config files, and git directory
        if (
            os.path.basename(filepath).startswith(".") or
            filepath.endswith((".css", ".json", ".md", ".svg", ".ico", ".mjs", ".gitignore", ".env", ".lock")) or
            ".git/" in filepath or
            "node_modules/" in filepath
        ):
            continue
        
        print(f"Analyzing: {filepath}")
        response = analyze_file_with_llm(filepath)
        
        if response is None:
            continue
            
        response.path = filepath
        analysis_results.append(response)
    
    return analysis_results


def main():
    """Command-line interface for analyzing code files."""
    parser = argparse.ArgumentParser(description="Analyze code files for outdated syntax using Gemini.")
    parser.add_argument("directory", type=str, help="Directory to analyze")

    args = parser.parse_args()
    directory_to_analyze = args.directory

    print(f"🔍 Analyzing directory: {directory_to_analyze}")
    print("=" * 50)
    
    analysis_results = fetch_updates(directory_to_analyze)

    if not analysis_results:
        print("\n✅ No files were found to be out of date.")
    else:
        print("\n" + "=" * 50)
        print("📝 FILES NEEDING UPDATES:")
        print("=" * 50)
        
        for result in analysis_results:
            print(f"\n📄 File: {result.path}")
            print(f"💡 Reason: {result.reason}")
            print("-" * 50)
        
        print(f"\n✅ Total files needing updates: {len(analysis_results)}")


if __name__ == "__main__":
    main()
