"""
main.py - Point d'entrée principal du système Refactoring Swarm
Rôle: Orchestrateur
Description: Gère les arguments CLI et lance le workflow d'orchestration
"""

import argparse
import sys
import os
from dotenv import load_dotenv
from src.orchestrator.workflow import RefactoringOrchestrator
from src.utils.logger import log_experiment, ActionType

# Charger les variables d'environnement
load_dotenv()

def validate_environment():
    """Valide que l'environnement est correctement configuré."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERREUR: GOOGLE_API_KEY non trouvée dans le fichier .env")
        print("Veuillez créer un fichier .env avec votre clé API Google Gemini")
        sys.exit(1)
    return api_key

def main():
    """Point d'entrée principal du programme."""
    
    # Parser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(
        description="Refactoring Swarm - Système multi-agents pour le refactoring automatique"
    )
    parser.add_argument(
        "--target_dir",
        type=str,
        required=True,
        help="Chemin vers le dossier contenant le code à refactorer"
    )
    
    args = parser.parse_args()
    
    # HARDCODED: Maximum 10 iterations (requis par le sujet du TP)
    MAX_ITERATIONS = 10
    
    # Validation du dossier cible
    if not os.path.exists(args.target_dir):
        print(f"❌ ERREUR: Le dossier {args.target_dir} n'existe pas.")
        sys.exit(1)
    
    if not os.path.isdir(args.target_dir):
        print(f"❌ ERREUR: {args.target_dir} n'est pas un dossier.")
        sys.exit(1)
    
    # Validation de l'environnement
    api_key = validate_environment()
    
    # Log du démarrage
    print("=" * 60)
    print("🚀 REFACTORING SWARM - DÉMARRAGE")
    print("=" * 60)
    print(f"📁 Dossier cible: {args.target_dir}")
    print(f"🔄 Itérations max: {MAX_ITERATIONS} (limite stricte)")
    print("=" * 60)
    
    log_experiment(
        agent_name="System",
        model_used="system",
        action=ActionType.ANALYSIS,
        details={
            "input_prompt": f"Système démarré avec target_dir={args.target_dir}",
            "output_response": "Initialisation de l'orchestrateur",
            "target_dir": args.target_dir,
            "max_iterations": MAX_ITERATIONS
        },
        status="SUCCESS"
    )
    
    try:
        # Créer et lancer l'orchestrateur
        orchestrator = RefactoringOrchestrator(
            target_dir=args.target_dir,
            max_iterations=MAX_ITERATIONS,  # Toujours 10
            api_key=api_key
        )
        
        # Exécuter le workflow complet
        success = orchestrator.run()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ MISSION ACCOMPLIE - Refactoring terminé avec succès")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("⚠️ MISSION INCOMPLÈTE - Certains fichiers n'ont pas pu être corrigés")
            print("=" * 60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interruption utilisateur détectée")
        log_experiment(
            agent_name="System",
            model_used="system",
            action=ActionType.DEBUG,
            details={
                "input_prompt": "Interruption utilisateur",
                "output_response": "Arrêt du système",
                "error": "KeyboardInterrupt"
            },
            status="FAILURE"
        )
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {str(e)}")
        log_experiment(
            agent_name="System",
            model_used="system",
            action=ActionType.DEBUG,
            details={
                "input_prompt": "Erreur système critique",
                "output_response": str(e),
                "error_type": type(e).__name__
            },
            status="FAILURE"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
