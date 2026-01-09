import subprocess
import os
import shutil
from typing import Optional, Tuple
from pathlib import Path
import tempfile
from datetime import datetime
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class NativeBackupService:
    """
    Service for handling native PostgreSQL backups (pg_dump/pg_restore).
    Provides "Full System" fidelity including all IDs, sequences, and constraints.
    """

    @staticmethod
    def _get_db_config() -> dict:
        """Parse database URL to get connection details."""
        # DATABASE_URL format: postgresql://user:password@host:port/dbname
        from sqlalchemy.engine.url import make_url
        url = make_url(settings.DATABASE_URL)
        return {
            'host': url.host,
            'port': str(url.port) if url.port else '5432',
            'user': url.username,
            'password': url.password,
            'dbname': url.database
        }

    @staticmethod
    def create_dump(output_path: Path) -> dict:
        """
        Create a native PostgreSQL dump file.
        
        Args:
            output_path: Path where the dump file should be saved
            
        Returns:
            Dictionary with stats (success, size, etc.)
        """
        config = NativeBackupService._get_db_config()
        
        # Set PGPASSWORD environment variable only for this process
        env = os.environ.copy()
        if config['password']:
            env['PGPASSWORD'] = config['password']
            
        cmd = [
            'pg_dump',
            '-h', config['host'],
            '-p', config['port'],
            '-U', config['user'],
            '-F', 'c',  # Custom format (compressed, allows re-ordering)
            '-b',       # Include large objects (blobs)
            '-v',       # Verbose
            '-f', str(output_path),
            config['dbname']
        ]
        
        try:
            logger.info(f"Starting native backup to {output_path}")
            result = subprocess.run(
                cmd, 
                env=env, 
                check=True, 
                capture_output=True, 
                text=True
            )
            
            size_bytes = output_path.stat().st_size
            return {
                'success': True,
                'path': str(output_path),
                'size_bytes': size_bytes,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"pg_dump failed: {e.stderr}")
            return {
                'success': False,
                'error': f"pg_dump failed: {e.stderr}"
            }
        except Exception as e:
            logger.error(f"Native backup failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def restore_dump(dump_path: Path, clean: bool = True) -> dict:
        """
        Restore a native PostgreSQL dump file.
        
        Args:
            dump_path: Path to the .dump file
            clean: If True, drop existing database objects before creating new ones
            
        Returns:
            Dictionary with result stats
        """
        config = NativeBackupService._get_db_config()
        
        env = os.environ.copy()
        if config['password']:
            env['PGPASSWORD'] = config['password']
            
        cmd = [
            'pg_restore',
            '-h', config['host'],
            '-p', config['port'],
            '-U', config['user'],
            '-d', config['dbname'],
            '-v',       # Verbose
            '-e',       # Exit on error
            '--no-owner', # Don't try to restore object ownership (often problematic in cloud/containers)
            '--no-privileges', # Don't restore access privileges (grant/revoke)
        ]
        
        if clean:
            cmd.append('--clean')     # Clean (drop) database objects before recreating
            cmd.append('--if-exists') # Use IF EXISTS when dropping objects
            
        cmd.append(str(dump_path))
        
        try:
            logger.info(f"Starting native restore from {dump_path}")
            # pg_restore often returns non-zero exit codes for harmless warnings
            # We capture output but handle errors carefully
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True
            )
            
            # pg_restore exit codes:
            # 0: Success
            # 1: Warning (but processed)
            # >1: Fatal error
            
            if result.returncode > 1:
                logger.error(f"pg_restore failed with code {result.returncode}: {result.stderr}")
                return {
                    'success': False,
                    'error': f"pg_restore failed (code {result.returncode}): {result.stderr}"
                }
                
            return {
                'success': True,
                'message': "Restore completed successfully",
                'warnings': result.stderr if result.returncode == 1 else None
            }
            
        except Exception as e:
            logger.error(f"Native restore failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
