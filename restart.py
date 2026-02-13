#!/usr/bin/env python3
"""
Script de redémarrage complet de Planify
Tue toutes les instances et relance l'application
"""

import os
import sys
import signal
import subprocess
import time
import psutil
import socket
import logging
logger = logging.getLogger(__name__)

def print_colored(text, color='green'):
    """Afficher texte coloré"""
    colors = {
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'reset': '\033[0m'
    }
    logger.info(f"{colors.get(color, '')}{text}{colors['reset']}")

def find_planify_processes():
    """Trouver tous les processus Planify"""
    processes = []
    current_pid = os.getpid()
    
    print_colored("\n🔍 Recherche des processus Planify en cours...", 'blue')
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Ignorer le processus actuel
            if proc.info['pid'] == current_pid:
                continue
            
            cmdline = proc.info['cmdline']
            if cmdline:
                cmdline_str = ' '.join(cmdline)
                
                # Chercher les processus Python exécutant app.py, run.py, etc.
                if ('python' in cmdline_str.lower() and 
                    any(script in cmdline_str for script in ['app.py', 'run.py', 'start.py', 'run_production.py'])):
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline_str
                    })
                    print_colored(f"  ✓ Trouvé: PID {proc.info['pid']} - {cmdline_str[:80]}...", 'yellow')
        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return processes

def kill_process(pid):
    """Tuer un processus"""
    try:
        process = psutil.Process(pid)
        process.terminate()
        
        # Attendre jusqu'à 3 secondes
        try:
            process.wait(timeout=3)
            print_colored(f"  ✓ Processus {pid} terminé proprement", 'green')
            return True
        except psutil.TimeoutExpired:
            # Force kill si nécessaire
            process.kill()
            print_colored(f"  ⚠️  Processus {pid} tué de force", 'red')
            return True
            
    except psutil.NoSuchProcess:
        print_colored(f"  ℹ️  Processus {pid} déjà terminé", 'blue')
        return True
    except psutil.AccessDenied:
        print_colored(f"  ❌ Accès refusé pour PID {pid}", 'red')
        return False
    except Exception as e:
        print_colored(f"  ❌ Erreur lors de l'arrêt de {pid}: {e}", 'red')
        return False

def kill_processes_on_ports(ports=[5000, 5001, 5002, 5003, 8000, 8080]):
    """Tuer les processus qui utilisent les ports"""
    print_colored(f"\n🔌 Libération des ports {ports}...", 'blue')
    
    killed = []
    for port in ports:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    print_colored(f"  ⚠️  Port {port} utilisé par PID {conn.pid} ({proc.name()})", 'yellow')
                    if kill_process(conn.pid):
                        killed.append(port)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    
    if killed:
        print_colored(f"  ✓ Ports libérés: {killed}", 'green')
        time.sleep(1)  # Attendre que les ports soient vraiment libérés
    else:
        print_colored("  ✓ Tous les ports sont disponibles", 'green')

def check_port_available(port):
    """Vérifier si un port est disponible"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('', port))
        sock.close()
        return True
    except OSError:
        return False

def kill_all_planify():
    """Tuer toutes les instances Planify"""
    print_colored("\n" + "="*60, 'blue')
    print_colored("🛑  ARRÊT DE TOUTES LES INSTANCES PLANIFY", 'red')
    print_colored("="*60 + "\n", 'blue')
    
    # 1. Trouver et tuer les processus Planify
    processes = find_planify_processes()
    
    if not processes:
        print_colored("\n✓ Aucune instance Planify en cours d'exécution", 'green')
    else:
        print_colored(f"\n⚠️  {len(processes)} instance(s) trouvée(s). Arrêt en cours...", 'yellow')
        
        for proc in processes:
            kill_process(proc['pid'])
        
        # Attendre un peu
        time.sleep(1)
        
        # Vérifier qu'ils sont bien morts
        still_running = []
        for proc in processes:
            if psutil.pid_exists(proc['pid']):
                still_running.append(proc['pid'])
        
        if still_running:
            print_colored(f"\n⚠️  {len(still_running)} processus toujours actifs. Force kill...", 'red')
            for pid in still_running:
                try:
                    os.kill(pid, signal.SIGKILL)
                except:
                    pass
            time.sleep(0.5)
    
    # 2. Libérer les ports
    kill_processes_on_ports()
    
    print_colored("\n✅ Toutes les instances ont été arrêtées !", 'green')

def start_planify():
    """Démarrer Planify"""
    print_colored("\n" + "="*60, 'blue')
    print_colored("🚀  DÉMARRAGE DE PLANIFY v3.0", 'green')
    print_colored("="*60 + "\n", 'blue')
    
    # Vérifier que le port 5000 est disponible
    if not check_port_available(5000):
        print_colored("❌ Le port 5000 est toujours occupé. Nouvelle tentative de libération...", 'red')
        kill_processes_on_ports([5000])
        time.sleep(1)
        
        if not check_port_available(5000):
            print_colored("❌ Impossible de libérer le port 5000. Utilisez un autre port.", 'red')
            return False
    
    print_colored("✓ Port 5000 disponible", 'green')
    print_colored("\n🔧 Lancement de l'application...\n", 'blue')
    
    # Lancer l'application
    try:
        # Déterminer quel script utiliser
        if os.path.exists('app.py'):
            script = 'app.py'
        elif os.path.exists('run.py'):
            script = 'run.py'
        elif os.path.exists('start.py'):
            script = 'start.py'
        else:
            print_colored("❌ Aucun script de démarrage trouvé", 'red')
            return False
        
        print_colored(f"📝 Exécution de: python3 {script}\n", 'blue')
        
        # Lancer en mode production
        env = os.environ.copy()
        env['FLASK_ENV'] = 'production'
        
        # Lancer le processus
        subprocess.Popen(
            ['python3', script],
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        print_colored("\n" + "="*60, 'green')
        print_colored("✅  PLANIFY v3.0 DÉMARRÉ AVEC SUCCÈS !", 'green')
        print_colored("="*60, 'green')
        print_colored("\n📱 Accédez à l'application sur:", 'blue')
        print_colored("   → http://localhost:5000", 'green')
        print_colored("   → http://127.0.0.1:5000", 'green')
        
        # Obtenir l'IP locale
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print_colored(f"   → http://{local_ip}:5000 (réseau local)", 'green')
        except:
            pass
        
        print_colored("\n💡 Fonctionnalités v3.0:", 'blue')
        print_colored("   ✨ IA intelligente activée", 'green')
        print_colored("   📱 Interface mobile optimisée", 'green')
        print_colored("   🔌 Mode offline (PWA)", 'green')
        print_colored("   🤖 Automatisations activées", 'green')
        
        print_colored("\n⌨️  Appuyez sur Ctrl+C pour arrêter\n", 'yellow')
        
        return True
        
    except Exception as e:
        print_colored(f"\n❌ Erreur lors du démarrage: {e}", 'red')
        return False

def main():
    """Fonction principale"""
    print_colored("\n" + "="*60, 'blue')
    print_colored("    🔄  REDÉMARRAGE COMPLET DE PLANIFY v3.0", 'blue')
    print_colored("="*60 + "\n", 'blue')
    
    try:
        # 1. Tuer toutes les instances
        kill_all_planify()
        
        # 2. Attendre un peu
        print_colored("\n⏳ Attente de 2 secondes...", 'yellow')
        time.sleep(2)
        
        # 3. Redémarrer
        success = start_planify()
        
        if not success:
            print_colored("\n❌ Le redémarrage a échoué", 'red')
            sys.exit(1)
        
        # 4. Garder le script actif
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print_colored("\n\n⚠️  Arrêt demandé...", 'yellow')
            kill_all_planify()
            print_colored("\n✅ Planify arrêté proprement", 'green')
            sys.exit(0)
            
    except Exception as e:
        print_colored(f"\n❌ Erreur: {e}", 'red')
        sys.exit(1)

if __name__ == '__main__':
    # Vérifier qu'on a les droits
    if os.geteuid() == 0:
        print_colored("⚠️  Ne pas exécuter ce script en root (sudo)", 'yellow')
    
    main()

