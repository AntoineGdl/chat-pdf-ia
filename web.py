from flask import Flask, render_template, request, jsonify
from document_ai import DocumentAI
import os

app = Flask(__name__)
doc_ai = DocumentAI()  # Initialiser l'IA de document

@app.route('/')
def index():
    """Page principale avec interface de chat"""
    return render_template('index.html')

@app.route('/api/reload', methods=['POST'])
def reload_documents():
    """Recharger tous les documents"""
    docs_count = doc_ai.reload_all_documents()
    sections_count = doc_ai.db.get_sections_count()

    return jsonify({
        'success': True,
        'documents_count': docs_count,
        'sections_count': sections_count
    })

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Poser une question à l'IA"""
    data = request.json
    question = data.get('question', '')

    if not question:
        return jsonify({
            'success': False,
            'error': 'Question vide'
        })

    answer = doc_ai.ask(question)

    return jsonify({
        'success': True,
        'answer': answer
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtenir les statistiques sur la documentation chargée"""
    sections_count = doc_ai.db.get_sections_count()

    return jsonify({
        'success': True,
        'sections_count': sections_count
    })

if __name__ == '__main__':
    # Initialiser la base de données et charger les documents
    print("Chargement initial de la documentation...")
    doc_ai.reload_all_documents()

    print("Démarrage de l'interface web sur http://127.0.0.1:5000/")
    app.run(debug=True)