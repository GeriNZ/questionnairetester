import os
import streamlit as st
import openai
from openai import OpenAI
from docx import Document
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
import re

# Initialize the OpenAI client using an environment variable for the API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_questions_from_docx(file):
    document = Document(file)
    text = "\n".join([p.text for p in document.paragraphs if p.text.strip()])
    return extract_questions(text)

def extract_questions_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page_num in range(doc.page_count):
        page_text = doc.load_page(page_num).get_text()
        text += page_text
    return extract_questions(text)

def extract_questions(text):
    # Split the text into sentences based on common punctuation
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    
    # Combine follow-up questions with their preceding questions
    questions = []
    current_question = ""

    for sentence in sentences:
        clean_sentence = sentence.strip()

        # If it's a continuation like "If yes, how?", merge it with the current question
        if re.match(r'^(if yes,|why or why not|if so,|how|why|explain)$', clean_sentence.lower()):
            if current_question:
                current_question += " " + clean_sentence
        # If it's a new question, add the previous question (if any) to the list
        elif clean_sentence.endswith('?'):
            if current_question:
                questions.append(current_question.strip())
            current_question = clean_sentence
        # Add any remaining question after the loop ends
    if current_question:
        questions.append(current_question.strip())

    return questions

def assess_questions(questions):
    results = []
    for question in questions:
        # Use ChatCompletion to assess each question
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert in questionnaire design. Your role is to critically evaluate whether the question is well-formulated or if it needs improvement. Be very rigorous and identify any potential issues, including bias, ambiguity, or leading language. You should not be overly critically though as this is for master level student projects."},
                {"role": "user", "content": f"Question: '{question}'\n\nPlease classify this question as either 'Well Formulated' or 'Needs Improvement'. If it needs improvement, describe in detail what is wrong and suggest an improvement."}
            ],
            model="gpt-3.5-turbo",
        )

        # Correctly extract the content from the response
        response_message = response.choices[0].message.content.strip()
        results.append(response_message)

    return results

st.title("Questionnaire Quality Assessment Tool")

uploaded_file = st.file_uploader("Upload your questionnaire (PDF or Word)", type=["pdf", "docx"])
if uploaded_file is not None:
    if uploaded_file.type == "application/pdf":
        questions = extract_questions_from_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        questions = extract_questions_from_docx(uploaded_file)

    if questions:
        st.write("Extracted Questions:")
        for i, question in enumerate(questions, start=1):
            st.write(f"{i}. {question}")

        if st.button("Assess Questions"):
            with st.spinner("Assessing questions..."):
                assessments = assess_questions(questions)

            well_formulated = 0
            needs_work = 0
            for assessment in assessments:
                if "Well Formulated" in assessment:
                    well_formulated += 1
                else:
                    needs_work += 1

            # Display results
            st.write("Assessment Report:")
            for i, (question, assessment) in enumerate(zip(questions, assessments), start=1):
                st.write(f"**Q{i}:** {question}")
                st.write(f"_Assessment:_ {assessment}")

            # Plotting the statistics
            fig, ax = plt.subplots()
            labels = ["Well Formulated", "Needs Work"]
            sizes = [well_formulated, needs_work]
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
