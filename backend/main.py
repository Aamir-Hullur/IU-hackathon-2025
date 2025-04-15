import json
import re
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.cloud import firestore
from prompt_template import IDEA_EVALUATION_PROMPT

load_dotenv()

def evaluate_idea(event, context):

    API_KEY = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")

    # Initialize Firestore
    db = firestore.Client()

    # Get newly added document
    idea_id = context.resource.split('/')[-1]
    idea_doc = db.collection("ideas_input").document(idea_id).get()
    if not idea_doc.exists:
        print("Idea not found.")
        return

    idea = idea_doc.to_dict()

    input_json = json.dumps([idea], indent=2)
    prompt = IDEA_EVALUATION_PROMPT.format(input_json=input_json)
    response = model.generate_content(prompt)

    print("\n--- Gemini Response Start ---\n")
    print(response.text)
    print("\n--- Gemini Response End ---\n")

    updated_json = response.text.strip()
    try:
        updated_ideas = json.loads(updated_json)
    except json.JSONDecodeError:
        print("Could not parse AI response as valid JSON. Attempting regex fallback.")
        match = re.search(r'\[.*\]', updated_json, re.DOTALL)
        if match:
            try:
                updated_ideas = json.loads(match.group(0))
            except json.JSONDecodeError:
                print("Regex extraction failed to parse.")
                updated_ideas = []
        else:
            updated_ideas = []

    for idea in updated_ideas:
        doc_ref = db.collection("ideas_output").document(str(idea.get("id", idea["title"])))
        doc_ref.set(idea)

    with open("output_ideas.txt", "w") as outfile:
        json.dump(updated_ideas, outfile, indent=2)

    print("New idea evaluated and added to ideas_output collection and output_ideas.txt")