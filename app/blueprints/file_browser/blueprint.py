"""
Flask file browser extension with proper app integration
Created as an object for reuse in other projects
"""

import os
import mimetypes
from pathlib import Path
from flask import (
    Blueprint,
    abort,
    current_app,
    render_template,
    request,
    Response,
    jsonify
) 
from werkzeug.exceptions import NotFound
from app.extensions.common.file_handler import FileHandler

class FileBrowser:
    """Flask file browser extension"""
    
    def __init__(self, app, base_directory:os.PathLike, url_prefix='/files'):
        self.app = app
        self.base_directory = base_directory
        self.url_prefix = url_prefix
        self.file_handler = FileHandler()
        self.blueprint = None
        self.base_directory = Path(base_directory).resolve()
        
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['file_browser'] = self
        
        app.config.setdefault('FILE_BROWSER_BASE_DIR', str(self.base_directory))
        app.config.setdefault('FILE_BROWSER_URL_PREFIX', self.url_prefix)
        
        # Update settings from config
        self.base_directory = Path(app.config['FILE_BROWSER_BASE_DIR']).resolve()
        self.url_prefix = app.config['FILE_BROWSER_URL_PREFIX']
        
        # Create and register blueprint
        self._create_blueprint()
        app.register_blueprint(self.blueprint, url_prefix=self.url_prefix)
        
        # Ensure base directory exists
        if not self.base_directory.exists():
            raise FileNotFoundError("Invalid file browser base directory")

        app.logger.info(f"File browser initialized with base directory: {self.base_directory}")
    
    def _create_blueprint(self) -> Blueprint:
        """Create Flask blueprint and routes"""
        self.blueprint = Blueprint(
            'file_browser',
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static")
        )
        
        self.blueprint.file_browser = self
        
        @self.blueprint.route('/')
        @self.blueprint.route('/index')
        @self.blueprint.route('/index/')
        @self.app.permission_required(self.app.models.PERMISSION_ENUM.ADMIN)
        def file_browser() -> Response:
            """Main file browser interface"""
            try:
                current_path = request.args.get('path', '').strip('/')
                return self._render_file_browser(current_path)
            except Exception as e:
                current_app.logger.error(f"Error in file browser: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.blueprint.route('/file/content')
        @self.app.permission_required(self.app.models.PERMISSION_ENUM.ADMIN)
        def file_content() -> Response:
            """Serve file content for viewing/downloading"""
            try:
                file_path = request.args.get('path', '')
                return self._serve_file_content(file_path)
            except Exception as e:
                current_app.logger.error(f"Error serving file content: {e}")
                return jsonify({'error': str(e)}), 404
        
        @self.blueprint.route('/file/save', methods=['POST'])
        @self.app.permission_required(self.app.models.PERMISSION_ENUM.ADMIN)
        def file_save() -> Response:
            """Save file content"""
            try:
                return self._save_file()
            except Exception as e:
                current_app.logger.error(f"Error saving file: {e}")
                return jsonify({'success': False, 'message': str(e)}), 500
        
        @self.blueprint.route('/file/info')
        @self.app.permission_required(self.app.models.PERMISSION_ENUM.ADMIN)
        def file_info() -> Response:
            """Get detailed file information"""
            try:
                file_path = request.args.get('path', '')
                return self._get_file_info(file_path)
            except Exception as e:
                current_app.logger.error(f"Error getting file info: {e}")
                return jsonify({'error': str(e)}), 404
        
        return self.blueprint
    
    def _render_file_browser(self, current_path:os.PathLike) -> Response:
        """Render the file browser template with directory contents"""
        # Construct full path and ensure it's within base directory
        full_path = self.base_directory / current_path if current_path else self.base_directory
        full_path = full_path.resolve()
        
        # Security check
        try:
            full_path.relative_to(self.base_directory)
        except ValueError:
            abort(403, "Access denied: Path outside allowed directory")
        
        if not full_path.exists():
            abort(404, "Directory not found")
        
        if not full_path.is_dir():
            abort(400, "Path is not a directory")
        
        file_list = []
        
        try:
            for item in sorted(full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                
                item_info = {
                    'name': item.name,
                    'path': str(item.relative_to(self.base_directory)),
                    'is_directory': item.is_dir(),
                    'size': 0,
                    'size_formatted': '',
                    'icon': 'folder-fill',
                    'type': 'directory'
                }
                
                if not item.is_dir():
                    try:
                        stat_info = item.stat()
                        item_info.update({
                            'size': stat_info.st_size,
                            'size_formatted': self._format_file_size(stat_info.st_size),
                            'icon': self._get_file_icon(item.suffix.lower().lstrip('.')),
                            'type': item.suffix.lower().lstrip('.') or 'file'
                        })
                                                    
                    except (OSError, IOError):
                        continue  # Skip unreadable
                
                file_list.append(item_info)
        
        except PermissionError:
            abort(403, "Permission denied")
        
        # Calculate parent path for navigation
        parent_path = None
        if current_path:
            parent_parts = current_path.rstrip('/').split('/')
            if len(parent_parts) > 1:
                parent_path = '/'.join(parent_parts[:-1])
            else:
                parent_path = ''
        
        return render_template(
            'file_browser.html',
            file_list=file_list,
            current_path=current_path,
            parent_path=parent_path,
            base_directory=str(self.base_directory)
        )
    
    def _serve_file_content(self, file_path) -> Response:
        """Serve file contents"""
        if not file_path:
            abort(400, "No file path specified")
        
        # Construct full path and security check
        full_path = (self.base_directory / file_path).resolve()
        
        try:
            full_path.relative_to(self.base_directory)
        except ValueError:
            abort(403, "Access denied: Path outside allowed directory")
        
        if not full_path.exists() or not full_path.is_file():
            abort(404, "File not found")

        is_image = self._is_image_file(full_path)
        if not is_image and self._is_binary_file(full_path):
            abort(403, "Access denied: Reading binary files not allowed")

        file_ext = full_path.suffix.lower().lstrip('.')

        try:
            if self._is_text_file(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
            elif is_image:
                with open(full_path, 'rb') as f:
                    return f.read(), 200
        except Exception as e:
            abort(500, f"Error reading file: {str(e)}")

    def _save_file(self) -> Response:
        """Save file content from form data"""
        filepath = request.form.get('filepath', '').strip()
        filename = request.form.get('filename', '').strip()
        filecontent = request.form.get('filecontent', '')
        
        if not filepath or not filename:
            return jsonify({'success': False, 'message': 'Missing file path or name'}), 400
        
        # Construct full path and security check
        full_path = (self.base_directory / filepath).resolve()
        
        try:
            full_path.relative_to(self.base_directory)
        except ValueError:
            return jsonify({'success': False, 'message': 'Access denied: Path outside allowed directory'}), 403
        
        if not full_path.exists():
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        
        if not self._is_editable_file(full_path):
            return jsonify({'success': False, 'message': 'File type not editable'}), 400
        
        # Validators
        file_ext = full_path.suffix.lower().lstrip('.')
        if file_ext in ['yaml', 'yml']:
            return self.file_handler.handle_yaml_save(full_path, filecontent)
        elif file_ext == 'json':
            return self.file_handler.handle_json_save(full_path, filecontent)
        else:
            return self.file_handler.handle_generic_save(full_path, filecontent)
    
    def _get_file_info(self, file_path:os.PathLike) -> dict:
        """Get detailed information about a file"""
        if not file_path:
            return jsonify({'error': 'No file path specified'}), 400
        
        full_path = (self.base_directory / file_path).resolve()
        
        try:
            full_path.relative_to(self.base_directory)
        except ValueError:
            return jsonify({'error': 'Access denied: Path outside allowed directory'}), 403
        
        if not full_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        try:
            stat_info = full_path.stat()
            ext = full_path.suffix.lower().lstrip('.')
            file_info = {
                'name': full_path.name,
                'path': str(full_path.relative_to(self.base_directory)),
                'size': stat_info.st_size,
                'size_formatted': self._format_file_size(stat_info.st_size),
                'is_directory': full_path.is_dir(),
                'mime_type': mimetypes.guess_type(str(full_path))[0],
                'extension': ext,
                'modified': stat_info.st_mtime,
                'icon': self._get_file_icon(ext) if not full_path.is_dir() else 'folder-fill',
                'is_editable': self._is_editable_file(full_path)
            }
            return jsonify(file_info)
        
        except (OSError, IOError) as e:
            return jsonify({'error': f'Error retrieving file info: {str(e)}'}), 500

    
    @staticmethod
    def _is_binary_file(path:os.PathLike, blocksize:int=1024) -> bool:
        """Check if a file is binary by sampling its content."""
        try:
            with open(path, 'rb') as f:
                chunk = f.read(blocksize)
                if not chunk:
                    return False  # empty = text
                # Heuristic: contains null byte → binary
                if b'\0' in chunk:
                    return True
                # Fallback: too many non-printable bytes
                text_chars = bytearray(range(32, 127)) + b"\n\r\t\b"
                nontext = chunk.translate(None, text_chars)
                return float(len(nontext)) / len(chunk) > 0.30
        except Exception as e:
            print(e)
            return True  # if unsure, treat as binary for safety

    @staticmethod
    def _format_file_size(size_bytes:int|float) -> str:
        """Pretty-print file size"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    @staticmethod
    def _get_file_icon(extension) -> str:
        """Get Bootstrap icon class for file extension"""
        icon_map = { # TODO: Find a better way
            'txt': 'file-earmark-text',
            'md': 'file-earmark-text',
            'yaml': 'file-earmark-code',
            'yml': 'file-earmark-code',
            'json': 'file-earmark-code',
            'py': 'file-earmark-code',
            'js': 'file-earmark-code',
            'html': 'file-earmark-code',
            'css': 'file-earmark-code',
            'xml': 'file-earmark-code',
            'png': 'file-earmark-image',
            'jpg': 'file-earmark-image',
            'jpeg': 'file-earmark-image',
            'gif': 'file-earmark-image',
            'svg': 'file-earmark-image',
            'webp': 'file-earmark-image',
            'bmp': 'file-earmark-image',
            'log': 'file-earmark-text',
            'conf': 'gear',
            'config': 'gear',
            'ini': 'gear',
            'env': 'gear',
            'sh': 'terminal',
            'dockerfile': 'file-earmark-code'
        }
        return icon_map.get(extension, 'file-earmark')
    
    @staticmethod
    def _is_text_file(path) -> bool:
        """Wrapper for readability"""
        return not FileBrowser._is_binary_file(path)

    @staticmethod
    def _is_editable_file(path) -> bool:
        """Images maybe someday?"""
        return FileBrowser._is_text_file(path)

    @staticmethod
    def _is_image_file(path) -> bool:
        """Check if file extension represents an image file"""
        ext = path.suffix.lower().lstrip('.')
        image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp'}
        return ext in image_extensions

def init_filebrowser(app, base_directory:str="/docker", url_prefix:str="/files") -> FileBrowser:
    return FileBrowser(app, base_directory, url_prefix)


def register_blueprint(app) -> Blueprint:
    return init_filebrowser(app).blueprint