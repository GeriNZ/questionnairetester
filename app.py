import os
import streamlit as st
import openai
from openai import OpenAI
from docx import Document
import fitz  # PyMuPDF
import matplotlib.pyplot as plt

# Initialize the OpenAI client using an environment variable for the API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_questions_from_docx(file):
    document = Document(file)
    questions = [p.text for p in document.paragraphs if p.text.strip()]
    return questions

def extract_questions_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    questions = []
    for page_num in range(doc.page_count):
        page_text = doc.load_page(page_num).get_text()
        questions.extend([line for line in page_text.splitlines() if line.strip()])
    return questions

def assess_questions(questions):
    results = []
    for question in questions:
        # Use ChatCompletion to assess each question
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert in questionnaire assessment, able to identify issues and provide suggestions for better phrasing."},
                {"role": "user", "content": f"Evaluate the following question: '{question}'. Describe any potential misinterpretations or alternative readings, and suggest improvements if needed."}
            ],
            model="gpt-3.5-turbo",
        )

        # Correctly extract the content from the response
        response_message = response.choices[0].message.content
        results.append(response_message.strip())

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
                if "no issues" in assessment.lower():
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
