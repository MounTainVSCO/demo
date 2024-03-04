import re
import time
import openai
from openai import OpenAI
from docx import Document
from dotenv import load_dotenv
import os, fitz
from flask_socketio import SocketIO

load_dotenv('config.env')
API_KEY = os.getenv('API_KEY')
client = OpenAI(api_key=API_KEY)

def split_into_paragraphs(file_path):
    doc = Document(file_path)
    return [(paragraph.text, paragraph.style) for paragraph in doc.paragraphs if paragraph.text.strip() != '']

def split_into_sentences(paragraph):
    return paragraph.split('. ')

def get_pdf_paragraphs(file_path):
    # Open the PDF file
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        # Extract text from the page
        page_text = page.get_text("text")
        paragraphs = page_text.split('\n')
        for paragraph in paragraphs:
            text += paragraph + "\n"
    doc.close()
    return text

def identify_entities(text, source_language, target_language):
    nlp = ner_models[source_language]
    doc = nlp(text)
    entities = {}

    for ent in doc.ents:
        if ent.text not in entities and ent.label_ in ['PERSON', 'GPE', 'LOC', 'ORG', 'FAC', 'EVENT', 'NORP', 'WORK_OF_ART', 'PRODUCT']:
            full_sentence = ent.sent.text
            entities[ent.text] = ner_translate(ent.text, full_sentence, source_language=source_language, target_language=target_language, client=client)
    return entities

def remove_footnote_markers(text):
    pattern = r'\[\d+\]|\d+\s?|\(\d+\)' 
    cleaned_text = re.sub(pattern, '', text)
    return cleaned_text

def translate_text(sentences, client, custom_prompt):
    context_messages = [{"role": "system", "content": f"{custom_prompt}"}]
    for sentence in sentences[-4:]:  # Keep the context of the last 3 sentences plus the current one
        context_messages.append({"role": "user", "content": sentence})

    while True:
        try:
            response = client.chat.completions.create(model="gpt-4",
                                                      messages=context_messages,
                                                      temperature=0,
                                                      max_tokens=6969)
            return response.choices[0].message.content.strip()

        except openai.RateLimitError:
            time.sleep(65)
        except openai.OpenAIError as e:
            raise e

def create_translated_document(paragraphs, client, output_file_path, socketio, custom_prompt):
    translated_doc = Document()

    for index, (paragraph, style) in enumerate(paragraphs):
        sentences = split_into_sentences(paragraph)
        translated_paragraph = []
        for i in range(len(sentences)):
            context_sentences = sentences[max(0, i-3):i+1] 
            translated_sentence = translate_text(context_sentences,  client, custom_prompt)
            translated_paragraph.append(translated_sentence.split('\n')[-1]) 
        
        # print(paragraph)
        
        progress = (index + 1) / len(paragraphs) * 100 
        socketio.emit('progress_update', {'progress': progress})
        p = translated_doc.add_paragraph(' '.join(translated_paragraph))
        p.style = style

    translated_doc.save(output_file_path)

def translate_given_text(text, source_language, target_language, client):
    context_messages = [{"role": "system", "content": f"Translate from {source_language} to {target_language}"}, 
                        {"role": "user", "content": text}]

    try:
        response = client.chat.completions.create(model="gpt-4",
                                                messages=context_messages,
                                                temperature=0,
                                                max_tokens=100)
        return response.choices[0].message.content.strip()

    except openai.RateLimitError:
        time.sleep(65)
    except openai.OpenAIError as e:
        raise e
