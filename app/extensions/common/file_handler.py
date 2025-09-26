
import os
import json
import yaml
import shutil
from flask import jsonify
from pathlib import Path

class FileHandler:
    """Enhanced file handler with support for multiple file types"""
    
    def handle_yaml_save(self, filepath, content):
        """Handle YAML file saving with validation"""
        try:
            # Validate YAML syntax
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            return jsonify({
                'success': False,
                'message': f'Invalid YAML syntax: {str(e)}'
            }), 400
        
        return self._write_file(filepath, content)
    
    def handle_json_save(self, filepath, content):
        """Handle JSON file saving with validation"""
        try:
            # Validate JSON syntax
            json.loads(content)
        except json.JSONDecodeError as e:
            return jsonify({
                'success': False,
                'message': f'Invalid JSON syntax: {str(e)}'
            }), 400
        
        return self._write_file(filepath, content)
    
    def handle_generic_save(self, filepath, content):
        """Handle generic text file saving"""
        return self._write_file(filepath, content)
    
    def _write_file(self, filepath, content):
        """Write content to file with error handling"""
        try:
            # Create backup
            backup_path = f"{filepath}.backup"
            if filepath.exists():
                shutil.copy2(filepath, backup_path)
            
            # Write new content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Remove backup on successful write
            if Path(backup_path).exists():
                os.unlink(backup_path)
            
            return jsonify({
                'success': True,
                'message': 'File saved successfully'
            })
        
        except (OSError, IOError) as e:
            return jsonify({
                'success': False,
                'message': f'Error saving file: {str(e)}'
            }), 500
        except UnicodeEncodeError as e:
            return jsonify({
                'success': False,
                'message': f'Encoding error: {str(e)}'
            }), 400