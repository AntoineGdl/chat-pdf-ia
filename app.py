from document_ai import DocumentAI

def main():
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

if __name__ == "__main__":
    main()