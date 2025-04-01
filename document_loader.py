import os
import PyPDF2
from utils import logger

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