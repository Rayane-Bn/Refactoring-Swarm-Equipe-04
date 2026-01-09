"""
workflow.py - Gestion du workflow d'orchestration
Rôle: Orchestrateur
Description: Coordonne l'exécution séquentielle des agents (Auditor → Fixer → Judge)
             et gère la boucle de self-healing
"""

import os
import time
from typing import List, Dict, Optional
from src.utils.logger import log_experiment, ActionType

class RefactoringOrchestrator:
    """
    Orchestrateur principal du système Refactoring Swarm.
    
    Responsabilités:
    - Découvrir les fichiers Python à traiter
    - Coordonner l'exécution des agents dans le bon ordre
    - Gérer la boucle de correction (Self-Healing Loop)
    - Respecter la limite d'itérations pour éviter les boucles infinies
    - Logger toutes les décisions importantes
    """
    
    def __init__(self, target_dir: str, max_iterations: int, api_key: str):
        """
        Initialise l'orchestrateur.
        
        Args:
            target_dir: Chemin vers le dossier contenant le code à refactorer
            max_iterations: Nombre maximum d'itérations par fichier
            api_key: Clé API Google Gemini
        """
        self.target_dir = os.path.abspath(target_dir)
        self.max_iterations = max_iterations
        self.api_key = api_key
        
        # Ces agents seront créés par les autres membres de l'équipe
        # Pour l'instant, on initialise à None
        self.auditor = None
        self.fixer = None
        self.judge = None
        
        # Statistiques de l'exécution
        self.stats = {
            "total_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_iterations": 0
        }
    
    def discover_python_files(self) -> List[str]:
        """
        Découvre tous les fichiers Python (.py) dans le dossier cible.
        
        Returns:
            Liste des chemins absolus des fichiers Python trouvés
        """
        python_files = []
        
        print(f"\n🔍 Recherche de fichiers Python dans: {self.target_dir}")
        
        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    python_files.append(file_path)
                    print(f"  📄 Trouvé: {file}")
        
        self.stats["total_files"] = len(python_files)
        
        log_experiment(
            agent_name="Orchestrator",
            model_used="system",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": f"Scan du dossier {self.target_dir} pour trouver les fichiers Python",
                "output_response": f"Trouvé {len(python_files)} fichier(s) Python",
                "files_found": [os.path.basename(f) for f in python_files]
            },
            status="SUCCESS"
        )
        
        return python_files
    
    def should_continue_iteration(self, iteration: int, file_path: str) -> bool:
        """
        Décide si on doit continuer à itérer ou arrêter.
        
        Args:
            iteration: Numéro de l'itération actuelle
            file_path: Chemin du fichier en cours de traitement
            
        Returns:
            True si on doit continuer, False sinon
        """
        if iteration >= self.max_iterations:
            print(f"\n⚠️ LIMITE D'ITÉRATIONS atteinte pour {os.path.basename(file_path)}")
            print(f"   Maximum autorisé: {self.max_iterations} itérations")
            
            log_experiment(
                agent_name="Orchestrator",
                model_used="system",
                action=ActionType.DEBUG,
                details={
                    "input_prompt": f"Vérification limite itérations pour {file_path}",
                    "output_response": f"Limite atteinte: {iteration}/{self.max_iterations}",
                    "file": os.path.basename(file_path),
                    "reason": "max_iterations_reached"
                },
                status="FAILURE"
            )
            return False
        
        return True
    
    def process_single_file(self, file_path: str) -> bool:
        """
        Traite un seul fichier Python à travers le pipeline complet.
        
        Pipeline:
        1. Auditor analyse le fichier et crée un plan de refactoring
        2. Fixer applique les corrections selon le plan
        3. Judge exécute les tests
        4. Si tests échouent: retour au Fixer avec les erreurs (Self-Healing Loop)
        5. Si tests passent: succès, on passe au fichier suivant
        
        Args:
            file_path: Chemin du fichier à traiter
            
        Returns:
            True si le fichier a été corrigé avec succès, False sinon
        """
        file_name = os.path.basename(file_path)
        print(f"\n{'=' * 60}")
        print(f"📝 TRAITEMENT: {file_name}")
        print(f"{'=' * 60}")
        
        iteration = 0
        
        # Boucle de self-healing
        while self.should_continue_iteration(iteration, file_path):
            iteration += 1
            self.stats["total_iterations"] += 1
            
            print(f"\n🔄 Itération {iteration}/{self.max_iterations}")
            
            # ÉTAPE 1: AUDITOR - Analyse du code
            print(f"  1️⃣ Auditor: Analyse du code...")
            log_experiment(
                agent_name="Orchestrator",
                model_used="system",
                action=ActionType.ANALYSIS,
                details={
                    "input_prompt": f"Lancement de l'Auditor sur {file_name}, itération {iteration}",
                    "output_response": "Auditor en cours d'exécution",
                    "file": file_name,
                    "iteration": iteration,
                    "phase": "audit"
                },
                status="SUCCESS"
            )
            
            # TODO: Appeler l'agent Auditor ici
            # audit_result = self.auditor.analyze(file_path)
            audit_result = {"issues": [], "plan": "Plan de refactoring simulé"}
            
            # Pause pour respecter les rate limits de l'API
            time.sleep(2)
            
            # ÉTAPE 2: FIXER - Application des corrections
            print(f"  2️⃣ Fixer: Application des corrections...")
            log_experiment(
                agent_name="Orchestrator",
                model_used="system",
                action=ActionType.FIX,
                details={
                    "input_prompt": f"Lancement du Fixer sur {file_name}, itération {iteration}",
                    "output_response": "Fixer en cours d'exécution",
                    "file": file_name,
                    "iteration": iteration,
                    "phase": "fix"
                },
                status="SUCCESS"
            )
            
            # TODO: Appeler l'agent Fixer ici
            # fix_result = self.fixer.fix(file_path, audit_result["plan"])
            
            time.sleep(2)
            
            # ÉTAPE 3: JUDGE - Validation par les tests
            print(f"  3️⃣ Judge: Exécution des tests...")
            log_experiment(
                agent_name="Orchestrator",
                model_used="system",
                action=ActionType.DEBUG,
                details={
                    "input_prompt": f"Lancement du Judge sur {file_name}, itération {iteration}",
                    "output_response": "Judge en cours d'exécution",
                    "file": file_name,
                    "iteration": iteration,
                    "phase": "judge"
                },
                status="SUCCESS"
            )
            
            # TODO: Appeler l'agent Judge ici
            # test_result = self.judge.run_tests(file_path)
            test_result = {"passed": True, "errors": []}  # Simulé
            
            time.sleep(2)
            
            # DÉCISION: Continuer ou arrêter?
            if test_result["passed"]:
                print(f"  ✅ Tests passés! Fichier corrigé avec succès.")
                log_experiment(
                    agent_name="Orchestrator",
                    model_used="system",
                    action=ActionType.GENERATION,
                    details={
                        "input_prompt": f"Validation finale du fichier {file_name}",
                        "output_response": f"Succès après {iteration} itération(s)",
                        "file": file_name,
                        "iterations_needed": iteration,
                        "final_status": "success"
                    },
                    status="SUCCESS"
                )
                return True
            else:
                print(f"  ❌ Tests échoués. Logs d'erreur:")
                for error in test_result.get("errors", []):
                    print(f"     • {error}")
                print(f"  🔁 Renvoi au Fixer pour correction...")
                
                log_experiment(
                    agent_name="Orchestrator",
                    model_used="system",
                    action=ActionType.DEBUG,
                    details={
                        "input_prompt": f"Tests échoués pour {file_name}, itération {iteration}",
                        "output_response": "Relance de la boucle de correction",
                        "file": file_name,
                        "iteration": iteration,
                        "errors": test_result.get("errors", []),
                        "decision": "retry"
                    },
                    status="FAILURE"
                )
        
        # Si on arrive ici, on a dépassé le nombre max d'itérations
        print(f"  ⚠️ Impossible de corriger le fichier après {self.max_iterations} itérations")
        return False
    
    def run(self) -> bool:
        """
        Lance le workflow complet sur tous les fichiers du dossier cible.
        
        Returns:
            True si tous les fichiers ont été traités avec succès, False sinon
        """
        start_time = time.time()
        
        # Découverte des fichiers
        python_files = self.discover_python_files()
        
        if not python_files:
            print("\n⚠️ Aucun fichier Python trouvé dans le dossier cible.")
            return False
        
        print(f"\n📊 {len(python_files)} fichier(s) à traiter\n")
        
        # Traitement de chaque fichier
        for idx, file_path in enumerate(python_files, 1):
            print(f"\n[{idx}/{len(python_files)}] Traitement de {os.path.basename(file_path)}")
            
            success = self.process_single_file(file_path)
            
            if success:
                self.stats["successful_files"] += 1
            else:
                self.stats["failed_files"] += 1
        
        # Rapport final
        elapsed_time = time.time() - start_time
        self.print_final_report(elapsed_time)
        
        # Retourner True seulement si tous les fichiers ont réussi
        return self.stats["failed_files"] == 0
    
    def print_final_report(self, elapsed_time: float):
        """
        Affiche un rapport final des statistiques d'exécution.
        
        Args:
            elapsed_time: Temps total d'exécution en secondes
        """
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL")
        print("=" * 60)
        print(f"⏱️  Temps d'exécution: {elapsed_time:.2f} secondes")
        print(f"📁 Fichiers traités: {self.stats['total_files']}")
        print(f"✅ Succès: {self.stats['successful_files']}")
        print(f"❌ Échecs: {self.stats['failed_files']}")
        print(f"🔄 Itérations totales: {self.stats['total_iterations']}")
        
        if self.stats["total_files"] > 0:
            success_rate = (self.stats["successful_files"] / self.stats["total_files"]) * 100
            print(f"📈 Taux de réussite: {success_rate:.1f}%")
        
        print("=" * 60)
        
        log_experiment(
            agent_name="Orchestrator",
            model_used="system",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": "Génération du rapport final",
                "output_response": "Rapport généré",
                "execution_time_seconds": elapsed_time,
                "statistics": self.stats
            },
            status="SUCCESS"
        )