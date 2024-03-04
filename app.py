from flask import Flask, request, redirect, url_for, render_template, session
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import os
import translationengine

app = Flask(__name__, template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def translate_document():
    print(request.form['custom_prompt'])
    print(request.form['source_language'])
    print(request.form['target_language'])
    print(request.form['custom_prompt'])

    source_language = request.form["source_language"]
    target_language = request.form["target_language"]

    temp_directory = os.path.join(app.root_path, 'temp')
    os.makedirs(temp_directory, exist_ok=True)
    
    uploaded_file = request.files.get('file')
    if uploaded_file:
        filename = secure_filename(uploaded_file.filename)
        temp_path = os.path.join(temp_directory, filename)
        uploaded_file.save(temp_path)


        output_file_name = f"{source_language}_to_{target_language}_{filename}"
        output_file_path = os.path.join(temp_directory, output_file_name)

        # Start entity mapping process
        
        entire_text = translationengine.get_docx_text(temp_path)
        entity_mapping_dictionary = translationengine.identify_entities(entire_text, request.form['source_language'], request.form['target_language'])
        mapped_text_with_entites = translationengine.replace_entities(entity_mapping_dictionary)
        text_without_footnote = translationengine.remove_footnote_markers(mapped_text_with_entites)
        paragraphs = translationengine.split_into_paragraphs(text_without_footnote)
        translationengine.create_translated_document(paragraphs, translationengine.client, output_file_path, socketio, request.form['custom_prompt'])

        
        static_file_path = os.path.join(app.static_folder, output_file_name)
        os.rename(output_file_path, static_file_path)
        translated_file_url = url_for('static', filename=output_file_name)
        os.remove(temp_path)

        return {'translated_file_url': translated_file_url}
    else:
        return {'error': 'No file uploaded.'}

if __name__ == '__main__':
    
    socketio.run(app, debug=False)