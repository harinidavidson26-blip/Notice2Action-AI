
from flask import Flask, send_from_directory, request, jsonify
from pypdf import PdfReader
from google import genai
import os
import time

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Home page
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


# Health check
@app.route("/health")
def health():
    return jsonify({
        "status": "success",
        "message": "Notice2Action AI Backend is running!"
    })


# Gemini retry function
def generate_with_retry(client, prompt):

    for attempt in range(3):

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

            return response.text

        except Exception as e:

            error_message = str(e).upper()

            temporary_errors = [
                "503",
                "UNAVAILABLE",
                "OVERLOADED",
                "HIGH DEMAND",
                "429",
                "RESOURCE_EXHAUSTED"
            ]

            is_temporary = any(
                error in error_message
                for error in temporary_errors
            )

            if is_temporary and attempt < 2:
                wait_time = 5 * (attempt + 1)
                print(
                    f"Gemini busy. Retrying in {wait_time} seconds..."
                )
                time.sleep(wait_time)

            else:
                raise e


# Analyze notice
@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        # Check uploaded file
        if "file" not in request.files:
            return jsonify({
                "status": "error",
                "message": "Please upload a PDF file."
            }), 400

        file = request.files["file"]

        # Check file selection
        if not file or file.filename == "":
            return jsonify({
                "status": "error",
                "message": "Please select a PDF file."
            }), 400

        # IMPORTANT: Validate file extension FIRST
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({
                "status": "error",
                "message": "Please upload a PDF file only."
            }), 400

        # Read PDF
        try:
            pdf_reader = PdfReader(file.stream)

            if pdf_reader.is_encrypted:
                return jsonify({
                    "status": "error",
                    "message": "This PDF is password protected. Please upload an unlocked PDF."
                }), 400

            pdf_text = ""

            for page in pdf_reader.pages:
                page_text = page.extract_text()

                if page_text:
                    pdf_text += page_text + "\n"

        except Exception:
            return jsonify({
                "status": "error",
                "message": "Invalid or damaged PDF file. Please upload a valid PDF."
            }), 400

        # Check readable text
        if not pdf_text.strip():
            return jsonify({
                "status": "error",
                "message": "No readable text found in this PDF."
            }), 400

        # Limit text length
        pdf_text = pdf_text[:25000]

        # Get language
        language = request.form.get("language", "English")

        if language not in ["English", "Tamil"]:
            language = "English"

        # Check Gemini API key
        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            return jsonify({
                "status": "error",
                "message": "Gemini API key not configured. Please check your environment settings."
            }), 500

        # Gemini client
        client = genai.Client(api_key=api_key)

        # Main AI analysis prompt
        prompt = f"""
You are Notice2Action AI, a smart student assistant.

Analyze the following college or student notice.

Respond in {language}.

Organize the answer into exactly these five numbered sections:

1. Notice Summary
Give a simple summary of the notice.

2. Important Dates and Deadlines
Mention actual deadlines and important dates.
Clearly distinguish notice issue date from submission deadlines.

3. Important Instructions
List the important instructions students must follow.

4. Student Action Points
Give clear, practical tasks students need to complete.
Write each task on a separate line.

5. Scholarship or Application Details
Extract scholarship names, eligibility, application links,
required documents and other application details if available.

IMPORTANT RULES:
- Never invent dates, links or information.
- If a deadline is not mentioned, clearly say:
  "No deadline mentioned in the notice."
- Keep the response simple and student-friendly.
- Use the requested language.

NOTICE TEXT:
{pdf_text}
"""

        # Separate deadline extraction prompt
        deadline_prompt = f"""
You are a Smart Deadline Tracker.

Read the notice carefully.

Respond in {language}.

Find only actual deadlines and future important dates.

For each date, mention:
- Date
- Event or task
- What the student must do

IMPORTANT:
- Do not confuse the notice issue date with a deadline.
- Do not invent any date.
- If no actual deadline is mentioned, say:
  "No deadline mentioned in the notice."

NOTICE TEXT:
{pdf_text}
"""

        # Generate AI analysis
        ai_analysis = generate_with_retry(client, prompt)

        # Generate deadline analysis
        deadline_analysis = generate_with_retry(
            client,
            deadline_prompt
        )

        # Send successful response
        return jsonify({
            "status": "success",
            "message": "Notice analyzed successfully!",
            "extracted_text": pdf_text,
            "ai_analysis": ai_analysis,
            "deadline_analysis": deadline_analysis
        })

    except Exception as e:

        print("Analysis Error:", str(e))

        return jsonify({
            "status": "error",
            "message": "Unable to analyze the notice right now. Please try again."
        }), 500


# Run application
if __name__ == "__main__":
    app.run(debug=True)ain."  
        }), 500


# Run application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
