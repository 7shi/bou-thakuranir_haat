"""
Generate RAG (Retrieval-Augmented Generation) evaluation questions from a text file.

This script reads a source text file (e.g., a story in Markdown), sends it to a
language model, and asks it to generate a set of questions, answers, and the rationale
for each answer based on the text. The output is saved as a structured JSON file.
"""
import argparse
import json
import mimetypes
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel, Field
from llm7shi import config_from_schema, generate_content_retry, upload_file, delete_file

# --- Pydantic Schemas for Structured Output ---

class RagQuestion(BaseModel):
    """
    A model for a single question, its answer, and the rationale based on the source text.
    """
    question: str = Field(
        ...,
        description="A specific question about the story's content, characters, or plot.",
        example="What was the comprehensive plan orchestrated by Sitaram to help Udayaditya escape from prison?"
    )
    answer: str = Field(
        ...,
        description="A concise and accurate answer to the question.",
        example="Sitaram's plan was a multi-stage deception. First, he and his accomplices started a fire in the guards' living quarters to create a major diversion and draw all personnel away from the prison. During this chaos, Sitaram freed Udayaditya from his cell and led him to a pre-arranged boat where Basanta Ray was waiting. To cover up the escape, Sitaram's men then set fire to Udayaditya's now-empty prison cell. To make the death seem convincing, Sitaram planted bones, a skull, and Udayaditya's burnt sword in the ruins, intending to spread the rumor that the Yubaraj had perished in the fire."
    )
    chapters: List[int] = Field(
        ...,
        description="The chapter numbers where the evidence for this answer is found.",
        example=[29, 30, 31]
    )
    rationale: str = Field(
        ...,
        description="The justification for the answer, citing or summarizing relevant parts of the source text.",
        example="The plan's initiation is seen in Chapter 29 with the sudden fire alarm, which Sitaram uses as a pretext to get Udayaditya out of his cell. Chapter 30 shows him leading Udayaditya to the boat where Basanta Ray is waiting, confirming the escape part of the plan. The cover-up is detailed in Chapter 31, where it's revealed that Sitaram's men started the initial fire as a diversion and then \"set fire to Udayaditya's empty prison cell.\" The chapter explicitly states Sitaram's thought process: \"'I can spread the news that the Yubaraj has died in the fire and remain untroubled for some time,'\" and describes him throwing \"some bones, a skull, and Udayaditya's sword into that room\" to create false evidence."
    )

class RagQuestionSet(BaseModel):
    """
    A model to hold a collection of RAG evaluation questions.
    """
    questions: List[RagQuestion] = Field(
        ...,
        description="A list of generated questions for RAG evaluation."
    )

# --- Core Functions ---

def create_generation_prompt(count: int, language: str) -> str:
    """
    Creates the prompt to instruct the LLM on how to generate RAG questions.
    """
    return f"""
# Task

You are an AI assistant tasked with generating a set of questions and answers for evaluating a RAG (Retrieval-Augmented Generation) system. Use the provided story text to create {count} high-quality questions.

# Rules

1.  **Language:** Generate all questions, answers, and rationales in {language}. Use the original language of the source text when appropriate.

2.  **Diverse Questions:** Generate questions that cover the following aspects:
    *   **Character Motivation:** Why a character acted in a certain way.
    *   **Cause and Effect:** How one event led to another.
    *   **Plot Turning Points:** Key events that changed the story's direction.
    *   **Character Psychology:** A character's feelings or thoughts in a specific situation.
    *   **Plan/Strategy:** The details of a plan or scheme described in the story.

3.  **High-Quality Questions:** The questions should require a deep understanding of the context and not be answerable by a simple keyword search.

4.  **Answer and Rationale:** For each question, provide a concise answer and a `rationale` that explains the basis for the answer by citing information from the text.

5.  **Output Format:** Structure your entire response according to the provided Pydantic JSON schema.
""".strip()

def generate_questions(story_path: Path, output_path: Path, model: str, count: int, language: str) -> int:
    """
    Sends the story text to the LLM and generates a structured set of questions.

    Args:
        story_text: The full text of the story.

    Returns:
        A RagQuestionSet object containing the generated questions.
    """
    # Generate content using the schema
    file = None
    try:
        mimetype, _ = mimetypes.guess_type(story_path)
        file = upload_file(story_path, mimetype or "text/plain")
        questions_generated = 0
        
        # Prepare output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        while questions_generated < count:
            num_questions_to_generate = min(count - questions_generated, 10)
            prompt = create_generation_prompt(num_questions_to_generate, language)
            response = generate_content_retry(
                [file, prompt],
                model=model,
                config=config_from_schema(RagQuestionSet),
                show_params=False
            )
            questions = json.loads(response.text)["questions"]
            
            # Append to JSONL file
            with open(output_path, 'a', encoding='utf-8') as f:
                for question in questions:
                    f.write(json.dumps(question, ensure_ascii=False) + '\n')
            
            questions_generated += len(questions)
            print(f"Generated {questions_generated}/{count} questions...")
        
        return questions_generated
    finally:
        if file:
            delete_file(file)


def main():
    """
    Main function to run the script.
    """
    parser = argparse.ArgumentParser(description='Generate RAG evaluation questions from a text file.')
    parser.add_argument('input_file', type=Path, help='Input text or markdown file path.')
    parser.add_argument('-m', '--model', type=str, required=True, help='Model name to use for generation.')
    parser.add_argument('-c', '--count', type=int, required=True, help='Number of questions to generate.')
    parser.add_argument('-l', '--language', type=str, required=True, help='Language for questions and answers.')
    parser.add_argument('-o', '--output', type=Path, required=True, help='Output JSON file path.')
    
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Error: Input file '{args.input_file}' not found.")
        return 1
    
    # Count existing questions in output file if it exists
    existing_count = 0
    if args.output.exists():
        with open(args.output, 'r', encoding='utf-8') as f:
            existing_count = sum(1 for line in f if line.strip())
    
    remaining_count = max(0, args.count - existing_count)
    
    if remaining_count == 0:
        print(f"Target count ({args.count}) already reached. No new questions to generate.")
        return 0
    
    print(f"Existing questions: {existing_count}")
    print(f"Generating {remaining_count} additional RAG questions with the language model...")
    print(f"Saving questions to: {args.output}")
    
    total_questions = generate_questions(args.input_file, args.output, args.model, remaining_count, args.language)
    
    print("\nSuccessfully generated and saved questions.")
    print(f"Total questions created: {total_questions}")
    return 0


if __name__ == "__main__":
    exit(main())
