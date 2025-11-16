import os
import argparse
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
import json
import instructor

load_dotenv()  # Loads your GROQ_API_KEY from .env file

GROQ_API_KEY = "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"
client = instructor.from_groq(Groq(api_key=GROQ_API_KEY), mode=instructor.Mode.JSON)


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
    Reads file content and queries the LLM to determine if it's out of date
    and what changes might be necessary. Returns a CodeChange object if applicable.
    """
    with open(file_path, 'r', encoding="utf-8", errors="ignore") as f:
        file_content = f.read()

    # Create a user prompt for the LLM
    user_prompt = (
        "Analyze the following code and determine if the syntax is out of date. "
        "If it is out of date, specify what changes need to be made in the following JSON format:\n\n"
        "{\n"
        '  "path": "relative/file/path",\n'
        '  "old_content": "The entire content of the file, before any changes are made.",\n'
        '  "new_content": "The updated content with modern syntax.",\n'
        '  "reason": "A short explanation of why the code is out of date."\n'
        "}\n\n"
        f"{file_content}"
    )

    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes code and returns a JSON object with the path, old content, new content, and reason. Your goal is to identify outdated syntax in code and suggest modern updates."},
                {"role": "user", "content": user_prompt}
            ],
            response_model=CodeChange,
        )
        return chat_completion
    except (ValidationError, json.JSONDecodeError) as parse_error:
        print(f"Error parsing LLM response for {file_path}: {parse_error}")
        return None
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return None

def fetch_updates(directory):
    """Fetches updates for all files in directory."""
    analysis_results = []
    all_files = get_all_files_recursively(directory)
    
    for filepath in all_files:
        if (
            os.path.basename(filepath).startswith(".") or
            filepath.endswith((".css", ".json", ".md", ".svg", ".ico", ".mjs", ".gitignore", ".env"))
            or ".git/" in filepath
        ):
            continue
            
        response = analyze_file_with_llm(filepath)
        if response is None:
            continue
        response.path = filepath
        analysis_results.append(response)
    
    return analysis_results

def main():
    parser = argparse.ArgumentParser(description="Analyze code files for outdated syntax.")
    parser.add_argument("directory", type=str, help="Directory to analyze")

    args = parser.parse_args()
    directory_to_analyze = args.directory

    analysis_results = []
    all_files = get_all_files_recursively(directory_to_analyze)
    
    for filepath in all_files:
        if (
            os.path.basename(filepath).startswith(".") or
            filepath.endswith((".css", ".json", ".md", ".svg", ".ico", ".mjs", ".gitignore", ".env"))
            or ".git/" in filepath
        ):
            continue

        response = analyze_file_with_llm(filepath)
        if response is None:
            continue
        response.path = filepath
        analysis_results.append(response)

    if not analysis_results:
        print("No files were found to be out of date.")
    else:
        print("=UPDATED=")
        for result in analysis_results:
            print(f"File PATH: {result.path}")
            print(f"Reason: {result.reason}")
            print("-" * 40)

if __name__ == "__main__":
    main()
