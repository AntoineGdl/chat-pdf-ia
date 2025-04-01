import os
import re
from typing import List, Tuple
from document_loader import DocumentLoader
from database import Database
from utils import logger

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