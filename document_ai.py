import os
import ollama
from database import Database
from document_processor import DocumentProcessor
from utils import logger

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
                                   "Tu ne dois répondre qu'en utilisant les les fichiers fournis en documentation."
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