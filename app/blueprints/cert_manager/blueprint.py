import os
from pathlib import Path
from flask import (
    Blueprint,
    Response,
    render_template,
    request,
    redirect,
    flash,
    current_app,
    url_for
)

DEFAULT_CERTS = {
    "root": {
        "key": "/certs/DOMAIN.internal-key.pem",
        "cert": "/certs/DOMAIN.internal.pem",
    },
    "wildcard": {
        "key": "/certs/_wildcard.DOMAIN.internal-key.pem",
        "cert": "/certs/_wildcard.DOMAIN.internal.pem",
    }
}

def read(file: str) -> str:
    try:
        with open(file) as f:
            return f.read()
    except FileNotFoundError:
        return ""

def write(file: str, content: str) -> None:
    with open(file, 'w') as f:
        f.write(content)

def discover_certs(certs_dir="/certs") -> dict:
    """Dynamically discover certificate files in /certs directory"""
    if not os.path.exists(certs_dir):
        return {}
    
    certs = {}
    files = list(Path(certs_dir).glob("*.pem"))
    
    # Group files by base name (key and cert pairs)
    cert_groups = {}
    for file in files:
        name = file.stem
        if name.endswith("-key"):
            base_name = name[:-4]  # Remove "-key"
            if base_name not in cert_groups:
                cert_groups[base_name] = {}
            cert_groups[base_name]["key"] = str(file)
        else:
            base_name = name
            if base_name not in cert_groups:
                cert_groups[base_name] = {}
            cert_groups[base_name]["cert"] = str(file)
    
    return cert_groups

def validate_cert_path(path: str) -> bool:
    """Ensure certificate path is within /certs directory"""
    abs_path = os.path.abspath(path)
    return abs_path.startswith("/certs/")

class CertHandler:
    def __init__(self, app, certs: dict = None):
        self.domain = app.config.get("DOMAIN_NAME", "example")
        self.certs_dir = "/certs"
        self.default_certs = certs or DEFAULT_CERTS

    def discover_certs(self) -> dict:
        """Get all certificate pairs from /certs directory"""
        return discover_certs(self.certs_dir)

    def read_cert_content(self, cert_path: str) -> str:
        """Read content of a certificate file"""
        if not validate_cert_path(cert_path):
            raise ValueError(f"Certificate path must be within /certs directory: {cert_path}")
        return read(cert_path)

    def write_cert_content(self, cert_path: str, content: str) -> None:
        """Write content to a certificate file"""
        if not validate_cert_path(cert_path):
            raise ValueError(f"Certificate path must be within /certs directory: {cert_path}")
        write(cert_path, content)

    def get_all_certs_with_content(self) -> dict:
        """Get all certificates with their content"""
        certs = self.discover_certs()
        result = {}
        
        for name, paths in certs.items():
            result[name] = {
                "key": {
                    "path": paths.get("key", ""),
                    "content": read(paths["key"]) if paths.get("key") else ""
                },
                "cert": {
                    "path": paths.get("cert", ""),
                    "content": read(paths["cert"]) if paths.get("cert") else ""
                }
            }
        
        return result


def register_blueprint(app):
    blueprint = bp = Blueprint(
        'certs', __name__, 
        url_prefix='/certs',
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    @bp.route('/', methods=["GET", "POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def index() -> Response:
        cert_handler = current_app.cert_handler
        
        if request.method == "POST":
            try:
                # Handle existing certificates
                certs = cert_handler.discover_certs()
                for cert_name in certs.keys():
                    key_content = request.form.get(f"{cert_name}_key_content")
                    cert_content = request.form.get(f"{cert_name}_cert_content")
                    
                    if key_content is not None and certs[cert_name].get("key"):
                        cert_handler.write_cert_content(certs[cert_name]["key"], key_content)
                    
                    if cert_content is not None and certs[cert_name].get("cert"):
                        cert_handler.write_cert_content(certs[cert_name]["cert"], cert_content)
                
                # Handle new certificate creation
                new_cert_name = request.form.get("new_cert_name")
                new_key_path = request.form.get("new_key_path")
                new_cert_path = request.form.get("new_cert_path")
                new_key_content = request.form.get("new_key_content")
                new_cert_content = request.form.get("new_cert_content")
                
                if new_cert_name and (new_key_path or new_cert_path):
                    # Validate paths
                    if new_key_path and not validate_cert_path(new_key_path):
                        flash("Key path must be within /certs directory", "danger")
                        return redirect(url_for('certs.index'))
                    
                    if new_cert_path and not validate_cert_path(new_cert_path):
                        flash("Certificate path must be within /certs directory", "danger")
                        return redirect(url_for('certs.index'))
                    
                    # Write new certificates
                    if new_key_path and new_key_content:
                        cert_handler.write_cert_content(new_key_path, new_key_content)
                    
                    if new_cert_path and new_cert_content:
                        cert_handler.write_cert_content(new_cert_path, new_cert_content)
                    
                    flash(f"Certificate '{new_cert_name}' created successfully", "success")
                else:
                    flash("Certificates updated successfully", "success")
                
                return redirect(url_for('certs.index'))
                
            except ValueError as e:
                flash(str(e), "danger")
                return redirect(url_for('certs.index'))
            except Exception as e:
                flash(f"Error saving certificates: {str(e)}", "danger")
                return redirect(url_for('certs.index'))
        
        # GET request - display form
        current_certs = cert_handler.get_all_certs_with_content()
        
        return render_template(
            'certs.html',
            certs=current_certs,
            domain=cert_handler.domain
        )

    @bp.route('/delete/<cert_name>', methods=["POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def delete(cert_name: str) -> Response:
        """Delete a certificate pair"""
        try:
            cert_handler = current_app.cert_handler
            certs = cert_handler.discover_certs()
            
            if cert_name in certs:
                cert_info = certs[cert_name]
                
                # Delete key file
                if cert_info.get("key") and os.path.exists(cert_info["key"]):
                    os.remove(cert_info["key"])
                
                # Delete cert file
                if cert_info.get("cert") and os.path.exists(cert_info["cert"]):
                    os.remove(cert_info["cert"])
                
                flash(f"Certificate '{cert_name}' deleted successfully", "success")
            else:
                flash(f"Certificate '{cert_name}' not found", "warning")
                
        except Exception as e:
            flash(f"Error deleting certificate: {str(e)}", "danger")
        
        return redirect(url_for('certs.index'))

    app.cert_handler = CertHandler(app)
    app.register_blueprint(blueprint)
    return blueprint