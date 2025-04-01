import os
import hashlib
import sqlite3
import ollama
import re
from typing import List, Tuple, Dict, Optional
import PyPDF2
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentLoader:
    """Classe pour charger des documents de différents formats"""

    @staticmethod
    def load_document(filepath: str) -> str:
        """Charge le contenu d'un document selon son type"""
        filename = os.path.basename(filepath)
        extension = os.path.splitext(filepath)[1].lower()

        try:
            if extension == '.pdf':
                return DocumentLoader._read_pdf(filepath)
            elif extension in ['.md', '.txt', '.rst']:
                return DocumentLoader._read_text(filepath)
            else:
                # logger.warning(f"Format non pris en charge : {extension}")
                return ""
        except Exception as e:
            # logger.error(f"Erreur lors de la lecture de {filename}: {str(e)}")
            return ""

    @staticmethod
    def _read_pdf(filepath: str) -> str:
        """Lit le contenu d'un fichier PDF"""
        content = ""
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                content += page.extract_text() + "\n\n"
        return content

    @staticmethod
    def _read_text(filepath: str) -> str:
        """Lit le contenu d'un fichier texte"""
        with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
            return file.read()

class Database:
    """Gestion de la base de données SQLite"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        # logger.info(f"Base de données initialisée : {db_path}")

    def _create_tables(self) -> None:
        """Crée les tables nécessaires"""
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            file_path TEXT UNIQUE
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            title TEXT,
            content TEXT,
            content_hash TEXT UNIQUE,
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
        ''')
        self.conn.commit()

    def document_exists(self, file_path: str) -> bool:
        """Vérifie si un document existe déjà"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM documents WHERE file_path = ?", (file_path,))
        return cursor.fetchone() is not None

    def store_document(self, filename: str, file_path: str) -> int:
        """Stocke un document et retourne son ID"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO documents (filename, file_path) VALUES (?, ?)",
            (filename, file_path)
        )
        self.conn.commit()
        return cursor.lastrowid

    def store_section(self, document_id: int, title: str, content: str) -> bool:
        """Stocke une section de document"""
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Vérifie si la section existe déjà
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM sections WHERE content_hash = ?", (content_hash,))
        if cursor.fetchone():
            return False

        # Stocke la nouvelle section
        cursor.execute(
            "INSERT INTO sections (document_id, title, content, content_hash) VALUES (?, ?, ?, ?)",
            (document_id, title, content, content_hash)
        )
        self.conn.commit()
        return True

    def get_all_documents(self) -> List[Tuple[int, str]]:
        """Récupère tous les documents (id, filename)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, filename FROM documents")
        return cursor.fetchall()

    def get_sections_count(self) -> int:
        """Retourne le nombre total de sections"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sections")
        return cursor.fetchone()[0]

    def search_sections(self, query: str, limit: int = 5) -> List[Dict]:
        """Recherche des sections pertinentes"""
        words = query.lower().split()
        results = []
        cursor = self.conn.cursor()

        # logger.info(f"Recherche avec {len(words)} mots-clés: {', '.join(words)}")

        for word in words:
            if len(word) < 3:  # Ignorer les mots trop courts
                continue

            # logger.info(f"Recherche du mot-clé '{word}'...")
            cursor.execute("""
                SELECT s.id, d.filename, s.title, s.content 
                FROM sections s
                JOIN documents d ON s.document_id = d.id
                WHERE lower(s.content) LIKE ? OR lower(s.title) LIKE ?
                """, (f'%{word}%', f'%{word}%'))

            found = cursor.fetchall()
            if found:
                # logger.info(f"Trouvé {len(found)} sections contenant '{word}'")
                for section_id, filename, title, content in found:
                    results.append({
                        'id': section_id,
                        'filename': filename,
                        'title': title,
                        'content': content,
                        'relevance': 1  # On pourrait améliorer avec un score de pertinence
                    })
            else:
                logger.info(f"Aucune section trouvée contenant '{word}'")

        # Déduplique et trie par pertinence
        unique_results = {}
        for result in results:
            if result['id'] not in unique_results:
                unique_results[result['id']] = result
            else:
                unique_results[result['id']]['relevance'] += 1

        # Trie par score de pertinence et limite les résultats
        sorted_results = sorted(
            unique_results.values(),
            key=lambda x: x['relevance'],
            reverse=True
        )[:limit]

        # logger.info(f"Total: {len(sorted_results)} sections pertinentes (limité à {limit})")
        return sorted_results

    def get_knowledge_summary(self) -> str:
        """Génère un résumé des connaissances disponibles dans la base de données"""
        cursor = self.conn.cursor()

        # Compter le nombre de documents
        cursor.execute("SELECT COUNT(DISTINCT document_id) FROM sections")
        doc_count = cursor.fetchone()[0]

        # Récupérer le nombre total de sections
        cursor.execute("SELECT COUNT(*) FROM sections")
        section_count = cursor.fetchone()[0]

        if section_count == 0:
            return "Je n'ai encore appris aucune information. Aucun document n'a été traité."

        # Récupérer les titres des sections
        cursor.execute("SELECT DISTINCT document_id, title FROM sections ORDER BY document_id")
        sections = cursor.fetchall()

        summary = f"J'ai appris {section_count} sections provenant de {doc_count} documents différents:\n\n"

        current_doc = None
        for doc_id, title in sections:
            if doc_id != current_doc:
                summary += f"\n📄 Document {doc_id}:\n"
                current_doc = doc_id
            summary += f"- {title}\n"

        return summary

    def close(self):
        """Ferme la connexion à la base de données"""
        self.conn.close()

class DocumentProcessor:
    """Traite les documents pour en extraire et stocker le contenu"""

    def __init__(self, db: Database):
        self.db = db
        self.loader = DocumentLoader()

    def process_document(self, filepath: str) -> bool:
        """Traite un document et stocke son contenu"""
        if not os.path.exists(filepath):
            # logger.error(f"Le fichier n'existe pas: {filepath}")
            return False

        filename = os.path.basename(filepath)
        # logger.info(f"Traitement du document: {filename}")

        # Vérifier si le document existe déjà
        if self.db.document_exists(filepath):
            # logger.warning(f"Document déjà traité: {filename}")
            return False

        # Charger le contenu
        content = self.loader.load_document(filepath)
        if not content.strip():
            # logger.error(f"Document vide ou non lisible: {filename}")
            return False

        # Stocker le document
        document_id = self.db.store_document(filename, filepath)

        # Découper et stocker les sections
        sections = self._split_into_sections(content)
        # logger.info(f"Document découpé en {len(sections)} sections")

        sections_stored = 0
        for title, section_content in sections:
            if self.db.store_section(document_id, title, section_content):
                sections_stored += 1

        # logger.info(f"{sections_stored} nouvelles sections stockées sur {len(sections)}")
        return sections_stored > 0

    def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
        """Divise le contenu en sections"""
        sections = []

        # Utiliser une regex plus simple sans look-behind à largeur variable
        import re
        pattern = r'\n(#{1,6}\s+.+?)(?=\n)'
        matches = re.finditer(pattern, content)

        # Collecter les positions des titres
        title_positions = []
        titles = []
        for match in matches:
            title = match.group(1).strip()
            title_positions.append(match.start())
            titles.append(title)

        # Si des titres sont trouvés, extraire les sections
        if titles:
            for i in range(len(titles)):
                start_pos = title_positions[i] + len(titles[i])
                end_pos = title_positions[i + 1] if i < len(titles) - 1 else len(content)
                section_content = content[start_pos:end_pos].strip()
                sections.append((titles[i].lstrip('#').strip(), section_content))
        else:
            # Pour les documents sans titres (comme les PDF), diviser par paragraphes
            paragraphs = [p for p in re.split(r'\n\s*\n', content) if p.strip()]

            if paragraphs:
                for i, paragraph in enumerate(paragraphs):
                    first_words = ' '.join(paragraph.strip().split()[:5]) + '...'
                    sections.append((f"Section {i + 1}: {first_words}", paragraph))
            else:
                # En dernier recours, diviser en blocs
                sections.append(("Document complet", content))

        print(f"Document découpé en {len(sections)} sections")
        return sections

class DocumentAI:
    """Classe principale qui coordonne l'apprentissage de documents et les requêtes"""

    def __init__(self, db_path: str = "documentation.sqlite", model_name: str = "mistral"):
        self.db = Database(db_path)
        self.processor = DocumentProcessor(self.db)
        self.model = model_name
        # logger.info(f"DocumentAI initialisé avec le modèle: {model_name}")

    def learn_folder(self, folder_path: str) -> int:
        """Apprend tous les documents d'un dossier"""
        if not os.path.exists(folder_path):
            # logger.error(f"Le dossier n'existe pas: {folder_path}")
            os.makedirs(folder_path)
            # logger.info(f"Dossier créé: {folder_path}")
            return 0

        count = 0
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath) and filename.lower().endswith(('.md', '.txt', '.pdf', '.rst')):
                try:
                    if self.processor.process_document(filepath):
                        count += 1
                except Exception as e:
                     logger.error(f"Erreur lors du traitement de {filename}: {str(e)}")

        return count

    def learn_document(self, filepath: str) -> bool:
        """Apprend un document spécifique"""
        return self.processor.process_document(filepath)

    def ask(self, question: str) -> str:
        """Répond à une question basée sur les documents appris"""
        # Vérifier si c'est une question sur les connaissances
        if self._is_knowledge_question(question):
            return self.db.get_knowledge_summary()

        # Rechercher les sections pertinentes
        sections = self.db.search_sections(question)

        if not sections:
            return "Je n'ai pas trouvé d'information pertinente dans la documentation apprise."

        # Construire le contexte à partir des sections pertinentes
        context = "\n\n".join([
            f"--- {section['title']} ---\n{section['content']}"
            for section in sections
        ])

        # Générer une réponse avec le modèle
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': "Tu es un assistant expert en documentation technique. "
                                 "Réponds uniquement en utilisant le contexte fourni. "
                                 "Si tu ne trouves pas l'information dans le contexte, dis-le clairement."
                    },
                    {
                        'role': 'user',
                        'content': f"CONTEXTE:\n{context}\n\nQUESTION: {question}\n\n"
                                 "Utilise uniquement le contexte ci-dessus pour répondre à la question."
                    }
                ]
            )
            return response['message']['content']
        except Exception as e:
            # logger.error(f"Erreur lors de l'interrogation du modèle: {str(e)}")
            return f"Erreur lors de la génération de la réponse: {str(e)}"

    def _is_knowledge_question(self, question: str) -> bool:
        """Détermine si la question porte sur les connaissances apprises"""
        question_lower = question.lower()
        # Paramètrage de l'IA
        patterns = [
            "qu'as-tu appris", "que sais-tu", "quelles informations",
            "quelles connaissances", "qu'avez-vous appris", "que contient",
            "connaissance", "apprises", "documentation disponible",
            "quelles données", "base de connaissances", "résumé des",
            "documentation chargée", "documents chargés"
        ]
        return any(pattern in question_lower for pattern in patterns)

    def reload_all_documents(self):
        """Force le rechargement de tous les documents"""
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM sections")
        cursor.execute("DELETE FROM documents")
        self.db.conn.commit()
        print("Chargement des documents...")
        return self.learn_folder("documentation/")

    def close(self):
        """Ferme proprement les ressources"""
        self.db.close()

# Programme principal
if __name__ == "__main__":
    print("=" * 50)
    print("ASSISTANT DE DOCUMENTATION IA")
    print("=" * 50)

    doc_ai = DocumentAI()
    doc_folder = "documentation/"

    print("\nRechargement complet de la documentation...")
    # Force le rechargement de tous les documents
    docs_count = doc_ai.reload_all_documents()

    # Afficher les statistiques
    sections_count = doc_ai.db.get_sections_count()
    if sections_count > 0:
        print(f"\n{sections_count} sections de documentation sont disponibles pour les questions.")
    else:
        print(
            f"\nAucune section chargée. Veuillez ajouter des documents (.md, .txt, .pdf, .rst) dans le dossier {doc_folder}")

    # Mode interactif
    print("\nMode interactif - posez vos questions sur la documentation")
    print("Tapez 'q' pour quitter")
    print("-" * 50)

    while True:
        question = input("\nVotre question: ")
        if question.lower() in ['q', 'quit', 'exit']:
            break

        print("\nRecherche dans la documentation...")
        answer = doc_ai.ask(question)
        print("\nRéponse:")
        print("-" * 50)
        print(answer)
        print("-" * 50)

    doc_ai.close()
    print("\nMerci d'avoir utilisé l'Assistant Documentation IA!")