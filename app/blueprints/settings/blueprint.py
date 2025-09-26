import os
from flask import (
    Blueprint,
    Flask,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    abort
)
from .forms import LoStackDefaultsForm


def populate_defaults_form(form, defaults=None):
    """Populate the defaults form with current values"""
    if defaults is None:
        with current_app.app_context():
            defaults = current_app.models.LoStackDefaults.get_defaults()
    
    form.domain.data = defaults.domain
    form.session_duration.data = defaults.session_duration
    form.refresh_frequency.data = defaults.refresh_frequency
    form.show_details.data = defaults.show_details
    return form


def register_blueprint(app:Flask):
    bp = blueprint = Blueprint(
        'settings',
        __name__,
        url_prefix="/settings",
        template_folder=os.path.join(os.path.dirname(__file__), "templates")
    )

    @bp.route("/", methods=["GET", "POST"])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def settings():
        """Edit LoStack package default configuration"""
        form = LoStackDefaultsForm()
        defaults = current_app.models.LoStackDefaults.get_defaults()

        if request.method == "GET":
            populate_defaults_form(form, defaults)

        if form.validate_on_submit():
            defaults.domain = form.domain.data
            defaults.session_duration = form.session_duration.data
            defaults.refresh_frequency = form.refresh_frequency.data
            defaults.show_details = form.show_details.data

            try:
                app.db.session.commit()
                flash("Default configuration updated successfully!", "success")

                if app.models.save_traefik_config():
                    flash("Configuration file regenerated successfully!", "info")
                else:
                    flash("Warning: Configuration file could not be regenerated!", "warning")

                return redirect(url_for("settings.settings"))
            except Exception as e:
                app.db.session.rollback()
                flash(f"Error updating LoStack defaults: {str(e)}", "error")

        if not form.is_submitted():
            populate_defaults_form(form, defaults)

        return render_template("settings.html", form=form)

    app.register_blueprint(bp)
    return bp