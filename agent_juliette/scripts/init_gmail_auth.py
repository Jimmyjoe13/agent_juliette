"""
Script pour initialiser l'authentification Gmail OAuth2.

Exécute ce script une première fois pour générer le token.json :
    uv run python scripts/init_gmail_auth.py

Une fenêtre de navigateur s'ouvrira pour autoriser l'accès.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.gmail_service import GmailService, get_gmail_service


def main():
    print("=" * 50)
    print("🔐 Initialisation de l'authentification Gmail")
    print("=" * 50)
    
    gmail = get_gmail_service()
    
    if not gmail.is_configured():
        print("\n❌ Fichier credentials.json non trouvé !")
        print("   1. Allez sur https://console.cloud.google.com/")
        print("   2. Créez un projet et activez l'API Gmail")
        print("   3. Créez des identifiants OAuth2 (Application de bureau)")
        print("   4. Téléchargez credentials.json et placez-le à la racine")
        return
    
    print("\n✅ Fichier credentials.json trouvé")
    print("\n🌐 Ouverture du navigateur pour l'authentification...")
    print("   (Suivez les instructions dans le navigateur)")
    
    try:
        # Force l'authentification
        success = gmail._authenticate()
        
        if success:
            print("\n✅ Authentification réussie !")
            print(f"   Token sauvegardé: {gmail.token_path}")
            print("\n📧 Test d'envoi de brouillon...")
            
            # Test optionnel
            try:
                draft = gmail.create_draft(
                    to=gmail.sender_email,
                    subject="[TEST] Agent Juliette - Authentification réussie",
                    body_html="<h1>🎉 Félicitations !</h1><p>L'authentification Gmail fonctionne.</p>",
                )
                print(f"   ✅ Brouillon test créé: {draft['draft_id']}")
                print("   (Vérifiez vos brouillons Gmail)")
            except Exception as e:
                print(f"   ⚠️ Erreur lors du test: {e}")
        else:
            print("\n❌ Échec de l'authentification")
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        raise


if __name__ == "__main__":
    main()
