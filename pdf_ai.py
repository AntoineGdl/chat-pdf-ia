import os
import fitz  # PyMuPDF
import ollama
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import re


class PDFAI:
    """IA spécialisée dans l'apprentissage et l'interaction avec un seul fichier PDF"""

    def __init__(self, pdf_path: str = None, model_name: str = "mistral"):
        """Initialise l'IA avec un PDF spécifique"""
        self.pdf_path = pdf_path
        self.model_name = model_name
        self.document_content = ""
        self.sections = []
        self.embedding_model = SentenceTransformer('distiluse-base-multilingual-cased-v2')
        self.section_embeddings = []

        if pdf_path and os.path.exists(pdf_path):
            self.learn_pdf(pdf_path)

    def learn_pdf(self, pdf_path: str) -> bool:
        """Apprend le contenu complet d'un fichier PDF"""
        if not os.path.exists(pdf_path):
            print(f"Erreur: Le fichier {pdf_path} n'existe pas.")
            return False

        self.pdf_path = pdf_path
        print(f"Apprentissage du PDF: {os.path.basename(pdf_path)}")

        try:
            # Extraction du contenu
            self.document_content = self._extract_text_from_pdf(pdf_path)

            # Division en sections
            self.sections = self._split_into_sections(self.document_content)
            print(f"Document divisé en {len(self.sections)} sections")

            # Création des embeddings
            self._create_embeddings()
            print("Embeddings créés avec succès")

            return True
        except Exception as e:
            print(f"Erreur lors de l'apprentissage du PDF: {str(e)}")
            return False

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrait le texte d'un fichier PDF avec PyMuPDF"""
        content = ""
        try:
            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc):
                    text = page.get_text("text")
                    content += text + "\n\n"
                    print(f"Page {page_num + 1}/{doc.page_count} extraite: {len(text)} caractères")
        except Exception as e:
            print(f"Erreur extraction PDF: {str(e)}")

        return content

    def _split_into_sections(self, content: str) -> List[Dict[str, str]]:
        """Divise le contenu en sections intelligentes"""
        sections = []

        # Patterns pour détecter les titres dans différents formats
        title_patterns = [
            r'\n(\d+\.\d*\s+[A-Z].+?)\n+',  # Format numéroté (1.2 Titre)
            r'\n([A-Z][A-Z0-9 .:]{2,30})\n+',  # TITRES EN MAJUSCULES
            r'\n([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5}:)',  # Titre Avec Deux-Points:
        ]

        title_positions = []
        titles = []

        # Trouver tous les titres potentiels
        for pattern in title_patterns:
            matches = re.finditer(pattern, '\n' + content)
            for match in matches:
                title = match.group(1).strip()
                position = match.start()
                title_positions.append(position)
                titles.append(title)

        # Trier par position
        title_data = sorted(zip(title_positions, titles), key=lambda x: x[0])

        # Créer les sections basées sur les titres
        if title_data:
            positions = [pos for pos, _ in title_data]
            titles = [title for _, title in title_data]

            for i in range(len(titles)):
                start_pos = positions[i] + len(titles[i])
                end_pos = positions[i + 1] if i < len(titles) - 1 else len(content)
                section_content = content[start_pos:end_pos].strip()

                if len(section_content) > 50:
                    sections.append({
                        'title': titles[i],
                        'content': section_content
                    })

        # Si pas assez de sections, découpage par blocs
        if len(sections) < 3:
            chunk_size = 1500
            chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

            for i, chunk in enumerate(chunks):
                first_line = chunk.strip().split('\n')[0][:50]
                sections.append({
                    'title': f"Section {i + 1}: {first_line}...",
                    'content': chunk
                })

        return sections

    def _create_embeddings(self):
        """Crée des embeddings pour toutes les sections"""
        self.section_embeddings = []

        for section in self.sections:
            # Combiner titre et contenu pour l'embedding
            text_to_embed = section['title'] + "\n" + section['content']
            embedding = self.embedding_model.encode(text_to_embed)
            self.section_embeddings.append(embedding)

    def search_relevant_sections(self, query: str, top_k: int = 3) -> List[Dict]:
        """Recherche les sections les plus pertinentes"""
        if not self.sections:
            return []

        # Créer l'embedding de la requête
        query_embedding = self.embedding_model.encode(query)

        # Calculer les similarités
        similarities = []
        for i, section_embedding in enumerate(self.section_embeddings):
            similarity = np.dot(query_embedding, section_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(section_embedding))
            similarities.append((i, similarity))

        # Trier par similarité
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_sections = []
        for i, similarity in similarities[:top_k]:
            section = self.sections[i].copy()
            section['similarity'] = similarity
            top_sections.append(section)
        return top_sections

    def ask(self, question: str) -> str:
        """Répond à une question basée sur le PDF appris"""
        if not self.document_content:
            return "Aucun document chargé. Veuillez charger un PDF."

        # Rechercher les sections pertinentes
        relevant_sections = self.search_relevant_sections(question)

        if not relevant_sections:
            return "Je n'ai pas trouvé d'information pertinente dans le PDF appris."

        # Construire le contexte à partir des sections pertinentes
        context = "\n\n".join([
            f"--- {section['title']} (pertinence: {section['similarity']:.2f}) ---\n{section['content']}"
            for section in relevant_sections
        ])

        # Générer une réponse avec le modèle
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un assistant expert qui répond uniquement à partir des informations "
                                   "contenues dans le document PDF. Si la réponse n'est pas dans le contexte fourni, "
                                   "indique-le clairement. Sois précis et concis."
                                    "indique les étapes à suite dans le logiciel."
                    },
                    {"role": "user", "content": f"CONTEXTE:\n{context}\n\nQUESTION: {question}"}
                ]
            )
            return response['message']['content']
        except Exception as e:
            print(f"Erreur lors de la génération de la réponse: {str(e)}")
            return "Erreur lors de la génération de la réponse."

    def get_document_summary(self) -> str:
        """Retourne un résumé du document chargé"""
        if not self.document_content:
            return "Aucun document chargé."

        pdf_name = os.path.basename(self.pdf_path) if self.pdf_path else "Document inconnu"
        return f"Document: {pdf_name}\nNombre de sections: {len(self.sections)}\nTitres des sections principales:\n" + \
            "\n".join([f"- {section['title']}" for section in self.sections[:10]])

    def start_interactive_mode(self):
        """Démarre un mode interactif pour dialoguer avec l'IA"""
        if not self.document_content:
            print("Aucun document n'est chargé. Veuillez d'abord charger un PDF.")
            return

        print("\n" + "=" * 50)
        print("MODE DIALOGUE AVEC L'IA PDF")
        print("=" * 50)
        print(f"Document chargé: {os.path.basename(self.pdf_path)}")
        print(f"Nombre de sections: {len(self.sections)}")
        print("Tapez 'quit', 'exit' ou 'q' pour quitter")
        print("Tapez 'summary' pour voir un résumé du document")
        print("-" * 50)

        while True:
            question = input("\nVotre question: ")
            question_lower = question.lower()

            if question_lower in ['quit', 'exit', 'q']:
                print("Au revoir!")
                break
            elif question_lower in ['summary', 'résumé', 'resume']:
                print("\nRésumé du document:")
                print("-" * 50)
                print(self.get_document_summary())
                print("-" * 50)
            else:
                print("\nRecherche dans le document...")
                answer = self.ask(question)
                print("\nRéponse:")
                print("-" * 50)
                print(answer)
                print("-" * 50)

    def close(self):
        """Ferme les ressources utilisées par l'IA"""
        self.document_content = ""
        self.sections = []
        self.section_embeddings = []
        print("Ressources fermées.")


if __name__ == "__main__":
    # Vérifier si un dossier 'documentation' existe et contient des PDFs
    documentation_dir = "documentation"

    if not os.path.exists(documentation_dir):
        os.makedirs(documentation_dir)
        print(f"Le dossier '{documentation_dir}' a été créé. Veuillez y ajouter vos fichiers PDF.")
        exit(0)

    # Chercher les PDFs disponibles
    pdf_files = [f for f in os.listdir(documentation_dir) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"Aucun fichier PDF trouvé dans le dossier '{documentation_dir}'.")
        print("Veuillez ajouter des PDF à ce dossier puis relancer le programme.")
        exit(0)

    # S'il y a plusieurs PDFs, laisser l'utilisateur choisir
    selected_pdf = None
    if len(pdf_files) == 1:
        selected_pdf = os.path.join(documentation_dir, pdf_files[0])
    else:
        print("Plusieurs PDFs disponibles. Choisissez un fichier:")
        for i, pdf in enumerate(pdf_files):
            print(f"{i + 1}. {pdf}")

        try:
            choice = int(input("\nVotre choix (numéro): ")) - 1
            if 0 <= choice < len(pdf_files):
                selected_pdf = os.path.join(documentation_dir, pdf_files[choice])
            else:
                print("Choix invalide.")
                exit(1)
        except ValueError:
            print("Entrée invalide. Veuillez entrer un numéro.")
            exit(1)

    # Initialiser l'IA avec le PDF sélectionné
    pdf_ai = PDFAI(pdf_path=selected_pdf, model_name="mistral")

    # Démarrer le mode interactif
    pdf_ai.start_interactive_mode()

    # Nettoyer les ressources à la fin
    pdf_ai.close()