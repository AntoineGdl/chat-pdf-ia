import sqlite3
import hashlib
from typing import List, Tuple, Dict
from utils import logger

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