"""
Système de backup automatique de la base de données
Permet la sauvegarde quotidienne avec rotation automatique

Fonctionnalités:
- Backup manuel ou automatique
- Compression gzip
- Rotation des backups (garde les N derniers)
- Export au format SQLite standard
"""

import os
import shutil
import gzip
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    """Gestionnaire de backups de la base de données"""
    
    def __init__(self, db_path='instance/dj_prestations.db', backup_dir='backups', max_backups=30):
        """
        Args:
            db_path: Chemin de la base de données à sauvegarder
            backup_dir: Dossier où stocker les backups
            max_backups: Nombre maximum de backups à conserver
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        
        # Créer le dossier de backups s'il n'existe pas
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, compress=True):
        """
        Créer un backup de la base de données
        
        Args:
            compress: Si True, compresse le backup avec gzip
        
        Returns:
            dict: {
                'success': bool,
                'backup_file': str (chemin du fichier créé),
                'size': int (taille en octets),
                'error': str (si erreur)
            }
        """
        try:
            # Vérifier que la base existe
            if not os.path.exists(self.db_path):
                return {
                    'success': False,
                    'error': f'Base de données introuvable: {self.db_path}'
                }
            
            # Générer le nom du fichier de backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'backup_{timestamp}.db'
            
            if compress:
                backup_filename += '.gz'
            
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copier la base de données
            logger.info(f"Création du backup: {backup_path}")
            
            if compress:
                # Compression avec gzip
                with open(self.db_path, 'rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Copie simple
                shutil.copy2(self.db_path, backup_path)
            
            # Taille du fichier
            size = os.path.getsize(backup_path)
            size_mb = size / (1024 * 1024)
            
            logger.info(f"✅ Backup créé: {backup_filename} ({size_mb:.2f} MB)")
            
            # Rotation des backups
            self._rotate_backups()
            
            return {
                'success': True,
                'backup_file': backup_path,
                'size': size,
                'size_mb': size_mb,
                'compressed': compress,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du backup: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _rotate_backups(self):
        """
        Supprimer les anciens backups pour garder seulement les N derniers
        """
        try:
            # Lister tous les backups
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('backup_') and (filename.endswith('.db') or filename.endswith('.db.gz')):
                    filepath = os.path.join(self.backup_dir, filename)
                    backups.append({
                        'path': filepath,
                        'mtime': os.path.getmtime(filepath),
                        'name': filename
                    })
            
            # Trier par date (plus récent en premier)
            backups.sort(key=lambda x: x['mtime'], reverse=True)
            
            # Supprimer les plus anciens si > max_backups
            if len(backups) > self.max_backups:
                for backup in backups[self.max_backups:]:
                    try:
                        os.remove(backup['path'])
                        logger.info(f"🗑️ Backup supprimé (rotation): {backup['name']}")
                    except Exception as e:
                        logger.error(f"Erreur suppression backup {backup['name']}: {e}")
            
            logger.info(f"📦 Rotation terminée: {len(backups)} backup(s) conservé(s)")
            
        except Exception as e:
            logger.error(f"Erreur lors de la rotation des backups: {e}")
    
    def list_backups(self):
        """
        Lister tous les backups disponibles
        
        Returns:
            list: Liste de dict avec les infos de chaque backup
        """
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('backup_') and (filename.endswith('.db') or filename.endswith('.db.gz')):
                    filepath = os.path.join(self.backup_dir, filename)
                    size = os.path.getsize(filepath)
                    mtime = os.path.getmtime(filepath)
                    
                    backups.append({
                        'filename': filename,
                        'path': filepath,
                        'size': size,
                        'size_mb': size / (1024 * 1024),
                        'date': datetime.fromtimestamp(mtime),
                        'compressed': filename.endswith('.gz')
                    })
            
            # Trier par date (plus récent en premier)
            backups.sort(key=lambda x: x['date'], reverse=True)
            
        except Exception as e:
            logger.error(f"Erreur listage backups: {e}")
        
        return backups
    
    def restore_backup(self, backup_filename):
        """
        Restaurer un backup (ATTENTION: écrase la base actuelle)
        
        Args:
            backup_filename: Nom du fichier de backup à restaurer
        
        Returns:
            dict: {'success': bool, 'error': str}
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return {'success': False, 'error': 'Backup introuvable'}
            
            # Créer un backup de sécurité de la base actuelle
            security_backup = f'backup_before_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            security_path = os.path.join(self.backup_dir, security_backup)
            shutil.copy2(self.db_path, security_path)
            logger.info(f"Backup de sécurité créé: {security_backup}")
            
            # Restaurer le backup
            if backup_filename.endswith('.gz'):
                # Décompresser
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Copie simple
                shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"✅ Backup restauré: {backup_filename}")
            
            return {
                'success': True,
                'restored_from': backup_filename,
                'security_backup': security_backup
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la restauration: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def delete_backup(self, backup_filename):
        """
        Supprimer un backup spécifique
        
        Args:
            backup_filename: Nom du fichier à supprimer
        
        Returns:
            dict: {'success': bool, 'error': str}
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return {'success': False, 'error': 'Backup introuvable'}
            
            os.remove(backup_path)
            logger.info(f"🗑️ Backup supprimé: {backup_filename}")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Erreur suppression backup: {e}")
            return {'success': False, 'error': str(e)}


# Instance globale
backup_manager = BackupManager()


def create_daily_backup():
    """
    Fonction à appeler quotidiennement pour créer un backup automatique
    Peut être appelée depuis un cron job ou un scheduler
    """
    logger.info("🔄 Démarrage du backup quotidien...")
    result = backup_manager.create_backup(compress=True)
    
    if result['success']:
        logger.info(f"✅ Backup quotidien terminé: {result['backup_file']} ({result['size_mb']:.2f} MB)")
    else:
        logger.error(f"❌ Échec du backup quotidien: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    # Test
    logger.info("Test du système de backup...")
    result = create_daily_backup()

    if result['success']:
        logger.info(f"Backup créé: {result['backup_file']}")
        logger.info(f"Taille: {result['size_mb']:.2f} MB")

        # Lister les backups
        backups = backup_manager.list_backups()
        logger.info(f"{len(backups)} backup(s) disponible(s):")
        for backup in backups:
            logger.info(f"  - {backup['filename']} ({backup['size_mb']:.2f} MB) - {backup['date'].strftime('%d/%m/%Y %H:%M')}")
    else:
        logger.error(f"Erreur: {result.get('error')}")


