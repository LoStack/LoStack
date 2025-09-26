import functools
import logging
import os
import re
from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)
from flask_login import current_user
from typing import List, Dict
from .forms import MultiCheckboxField, UserForm, GroupForm, SearchForm


logger = logging.getLogger(__name__)

def get_all_groups():
    """Get all LDAP groups"""    
    try:
        groups = current_app.ldap_manager.get_all_groups()
        return [group['name'] for group in groups]
    except Exception as e:
        logger.error(f"Failed to get groups: {e}")
        return []

def get_all_users():
    """Get all LDAP users"""
    try:
        users = current_app.ldap_manager.get_all_users()
        return [user['username'] for user in users]
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        return []


def json_error_handler(func):
    """Decorator to catch exceptions and return JSON error response."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            return jsonify({'error': str(e)}), 500
    return wrapper

def register_blueprint(app):
    blueprint = Blueprint(
        'ldap', __name__, 
        url_prefix='/ldap',
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static")
    )

    @blueprint.route('/')
    @blueprint.route('/users')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def users():
        """List all users"""
        search = request.args.get('search', '', type=str)
        users_data = []
        
        try:
            if search:
                users_data = current_app.ldap_manager.search_users(search)
            else:
                users_data = current_app.ldap_manager.get_all_users()
        except Exception as e:
            flash(f'Failed to retrieve users: {str(e)}', 'error')
            logger.error(f"Error retrieving users: {e}")

        return render_template(
            'ldap_users.html', 
            users=users_data, 
            search=search
        )

    @blueprint.route('/users/create', methods=['GET', 'POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def create_user():
        """Create new user"""
        form = UserForm()
        form.groups.choices = [(g, g) for g in get_all_groups()]
        
        try:
            if form.validate_on_submit():
                if not form.password:
                    flash("You must create a password for a new user") 
                try:
                    form.validate_password(form.password)
                except Exception:
                    flash(f'Passwords do not match', 'error')
                    return render_template('ldap_user_form.html', form=form, action='Create')

                
                fields = (
                    form.username.data,
                    form.password.data,
                    form.email.data,
                    form.first_name.data,
                    form.last_name.data,
                    form.phone.data,
                    form.department.data,
                    form.title.data
                )

                try:
                    # Create user
                    success = current_app.ldap_manager.create_user(
                        username=form.username.data,
                        password=form.password.data,
                        email=form.email.data,
                        first_name=form.first_name.data,
                        last_name=form.last_name.data,
                        telephoneNumber=form.phone.data or None,
                        departmentNumber=form.department.data or None,
                        title=form.title.data or None
                    )

                    if success:
                        for group_name in form.groups.data:
                            current_app.ldap_manager.add_user_to_group(form.username.data, group_name)
                        
                        flash(f'User {form.username.data} created successfully', 'success')
                        return redirect(url_for('ldap.users'))
                    else:
                        flash('Failed to create user', 'error')
                        
                except Exception as e:
                    flash(f'Error creating user: {str(e)}', 'error')
                    logger.error(f"Error creating user {form.username.data}: {e}")
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')

        return render_template('ldap_user_form.html', form=form, action='Create')

    @blueprint.route('/users/<username>/edit', methods=['GET', 'POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def edit_user(username):
        """Edit existing user"""
        form = UserForm()
        form.groups.choices = [(g, g) for g in get_all_groups()]
        
        try:
            if request.method == 'GET':
                user_data = current_app.ldap_manager.get_user(username)
                if user_data:
                    form.username.data = user_data.get('username', '')
                    form.email.data = user_data.get('email', '')
                    form.first_name.data = user_data.get('first_name', '')
                    form.last_name.data = user_data.get('last_name', '')
                    form.phone.data = user_data.get('phone', '')
                    form.department.data = user_data.get('department', '')
                    form.title.data = user_data.get('title', '')
                    form.groups.data = user_data.get('groups', [])
                else:
                    flash(f'User {username} not found', 'error')
                    return redirect(url_for('ldap.users'))
            
            elif form.validate_on_submit():
                update_data = {
                    'mail': form.email.data,
                    'givenName': form.first_name.data,
                    'sn': form.last_name.data,
                }
                
                if form.phone.data:
                    update_data['telephoneNumber'] = form.phone.data
                if form.department.data:
                    update_data['departmentNumber'] = form.department.data
                if form.title.data:
                    update_data['title'] = form.title.data
                if form.password.data:
                    update_data['userPassword'] = form.password.data
                
                success = current_app.ldap_manager.update_user(username, **update_data)
                
                if success:
                    success, msg = current_app.ldap_manager.update_user_groups(username, form.groups.data)
                    if success:
                        flash(f'User {username} updated successfully', 'success')
                        return redirect(url_for('ldap.users'))
                    flash(f'Failed to update user groups - {msg}', 'error')
                else:
                    flash('Failed to update user', 'error')
                    
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')
            logger.error(f"Error updating user {username}: {e}")
        
        return render_template('ldap_user_form.html', 
                            form=form, action='Edit', username=username)

    @blueprint.route('/users/<username>/delete', methods=['POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    @json_error_handler
    def delete_user(username):
        """Delete user"""
        if current_user.name == username:
            return jsonify({'success': False, 'message': 'You cannot delete your own account'})

        if current_app.ldap_manager.remove_user(username):
            return jsonify({'success': True, 'message': f'User {username} deleted successfully'})

        return jsonify({'success': False, 'message': 'Failed to delete user'})


    @blueprint.route('/groups')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def groups():
        """List all groups"""
        search = request.args.get('search', '', type=str)
        groups_data = []
    
        try:
            if search:
                groups_data = current_app.ldap_manager.search_groups(search)
            else:
                groups_data = current_app.ldap_manager.get_all_groups()
        except Exception as e:
            flash(f'Failed to retrieve groups: {str(e)}', 'error')
            logger.error(f"Error retrieving groups: {e}")
        
        return render_template(
            'ldap_groups.html', 
            groups=groups_data, 
            search=search
        )

    @blueprint.route('/groups/create', methods=['GET', 'POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def create_group():
        """Create new group"""
        form = GroupForm()
        form.members.choices = [(u, u) for u in get_all_users()]
        
        if form.validate_on_submit():
            if not form.members.data:
                flash("You must select at least one member for a group.", "error")
                return render_template("ldap_group_form.html", form=form, action="Create")


            try:
                success = current_app.ldap_manager.create_group(
                    group_name=form.name.data,
                    description=form.description.data or "",
                    initial_members=form.members.data
                )
                
                if success:
                    flash(f'Group {form.name.data} created successfully', 'success')
                    return redirect(url_for('ldap.groups'))
                else:
                    flash('Failed to create group', 'error')
                    
            except Exception as e:
                flash(f'Error creating group: {str(e)}', 'error')
                logger.error(f"Error creating group {form.name.data}: {e}")
        
        return render_template('ldap_group_form.html', form=form, action='Create')

    @blueprint.route('/groups/<group_name>/edit', methods=['GET', 'POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    def edit_group(group_name):
        """Edit existing group"""
        form = GroupForm()
        form.members.choices = [(u, u) for u in get_all_users()]
                
        try:
            if request.method == 'GET':
                # Populate form with existing group data
                group_data = current_app.ldap_manager.get_group(group_name)
                if group_data:
                    form.name.data = group_data.get('name', '')
                    form.description.data = group_data.get('description', '')
                    form.members.data = group_data.get('members', [])
                else:
                    flash(f'Group {group_name} not found', 'error')
                    return redirect(url_for('ldap.groups'))
            
            elif form.validate_on_submit():
                # Update group
                success = current_app.ldap_manager.update_group(
                    group_name=group_name,
                    description=form.description.data or "",
                )
                
                if success:
                    # Update group membership
                    current_members = set(current_app.ldap_manager.get_group_members(group_name))
                    new_members = set(form.members.data)

                    status = True

                    # Add new members
                    for username in new_members - current_members:
                        status = current_app.ldap_manager.add_user_to_group(username, group_name)
                        if not status:
                            flash(f'Failed to update group membership status of {username} for {group_name}', 'error')
                    
                    # Remove old members
                    for username in current_members - new_members:
                        status = current_app.ldap_manager.remove_user_from_group(username, group_name)
                        if not status:
                            flash(f'Failed to update group membership status of {username} for {group_name}', 'error')
                    
                    if not status:
                        flash(f'Errors encountered updating membership for {group_name}', 'error')
                    else:
                        flash(f'Group {group_name} updated successfully', 'success')

                    return redirect(url_for('ldap.groups'))
                else:
                    flash('Failed to update group', 'error')
                    
        except Exception as e:
            flash(f'Error updating group: {str(e)}', 'error')
            logger.error(f"Error updating group {group_name}: {e}")
        
        return render_template(
            'ldap_group_form.html', 
            form=form,
            action='Edit', 
            group_name=group_name
        )

    @blueprint.route('/groups/<group_name>/delete', methods=['POST'])
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    @json_error_handler
    def delete_group(group_name):
        """Delete group"""
        if (success := current_app.ldap_manager.remove_group(group_name)):
            return jsonify({'success': True, 'message': f'Group {group_name} deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete group'})
            
    @blueprint.route('/api/user/<username>')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    @json_error_handler
    def get_user_api(username):        
        if (user := current_app.ldap_manager.get_user(username)):
            return jsonify(user)
        else:
            return jsonify({'error': 'User not found'}), 404

    @blueprint.route('/api/group/<group_name>')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    @json_error_handler
    def get_group_api(group_name):
        """API endpoint to get group details"""
        if (group_data := current_app.ldap_manager.get_group(group_name)):
            return jsonify(group_data)
        else:
            return jsonify({'error': 'Group not found'}), 404

    @blueprint.route('/api/connection/status')
    @app.permission_required(app.models.PERMISSION_ENUM.ADMIN)
    @json_error_handler
    def connection_status():
        """API endpoint to check LDAP connection status"""        
        return current_app.ldap_manager.get_connection_status()


    app.register_blueprint(blueprint)

    app.get_all_ldap_groups = get_all_groups
    app.get_all_ldap_users = get_all_users