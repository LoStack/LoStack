import os
import time
import ldap
import ldap.modlist as modlist
from ldap import LDAPError
import logging
from typing import List, Dict, Optional, Any
from functools import wraps


def ldap_error_handler():
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            def try_(retries = 3):
                for attempt in range(retries):
                    try:
                        with self: # handle reconnect
                            return func(self, *args, **kwargs)
                    except (ldap.SERVER_DOWN, ldap.CONNECT_ERROR, ldap.TIMEOUT) as e:
                        self._log("warning", f"Connection lost in {func.__name__}")
                    except Exception as e:
                        raise e # Pass up
                    raise ldap.SERVER_DOWN("Could not reconnect connect to ldap server")
            try:         
                with self:                         
                    return try_()
            except ldap.ALREADY_EXISTS as e:
                raise self._log_exc(e, f"Entry already exists in {func.__name__}")
            except ldap.NO_SUCH_OBJECT as e:
                raise self._log_exc(e, f"Object not found in {func.__name__}")
            except ldap.TYPE_OR_VALUE_EXISTS as e:
                raise self._log_exc(e, f"Value already exists in {func.__name__}")
            except ldap.NO_SUCH_ATTRIBUTE as e:
                raise self._log_exc(e, f"Attribute not found in {func.__name__}")
            except LDAPError as e:
                raise self._log_exc(e, f"LDAP error in {func.__name__}")
            except Exception as e:
                raise self._log_exc(e, f"Unexpected error in {func.__name__}")
        return wrapper
    return decorator


class LDAPManager:    
    def __init__(self, app):
        conf = app.config.get

        # LDAP connection settings
        self.ldap_host          = conf("LDAP_HOST", "openldap")
        self.ldap_port          = int(conf("LDAP_PORT_NUMBER", "389"))
        self.ldap_ldaps_port    = int(conf("LDAP_LDAPS_PORT_NUMBER", "636"))
        self.use_ldaps          = conf("LDAP_USE_LDAPS", "false").lower() == "true"
        if self.use_ldaps:
            self.ldap_uri       = f"ldaps://{self.ldap_host}:{self.ldap_ldaps_port}"
        else:
            self.ldap_uri       = f"ldap://{self.ldap_host}:{self.ldap_port}"       
        
        # LDAP structure
        self.ldap_domain        = conf("DOMAIN_NAME", "lostack.internal")
        self.base_dn            = conf("LDAP_BASE_DN", f"dc={self.ldap_domain.replace('.', ',dc=')}")
        self.people_dn          = f"ou=people,{self.base_dn}"
        self.groups_dn          = f"ou=groups,{self.base_dn}"
        
        self.organisation       = conf("LDAP_ORGANISATION", self.ldap_domain)
        self.admin_username     = conf("LDAP_ADMIN_USERNAME", "admin")
        self.admin_bind_dn      = conf("LDAP_ADMIN_BIND_DN", f"cn={self.admin_username},{self.base_dn}")
        self.admin_bind_pwd     = conf("LDAP_ADMIN_PASSWORD", "one_time_login_password")
        self._additional_groups = conf("FIRST_RUN_ADDITIONAL_LDAP_GROUPS", "")
        
        # TLS/Security settings
        self.tls_verify_client  = conf("LDAP_TLS_VERIFY_CLIENT", "never")
        self.ignore_cert_errors = conf("LDAP_IGNORE_CERT_ERRORS", "true").lower() == "true"
        self.require_starttls   = conf("LDAP_REQUIRE_STARTTLS", "false").lower() == "true"
            
        # Application-specific settings
        self.admins_group       = conf("ADMIN_GROUP", "admins")
        self.email_domain       = conf("EMAIL_DOMAIN", f"mail.{self.ldap_domain}")

        self.connection = None
        self.logger = app.logger
        
        # Set up LDAP options based on TLS settings
        if self.ignore_cert_errors or self.tls_verify_client == "never":
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        elif self.tls_verify_client == "allow":
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)
        elif self.tls_verify_client == "demand":
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)

    def await_connection(self):
        self.logger.info("Connecting to LDAP server...")
        attempt = 0
        while attempt < 10:
            try:
                self._connect()
                if self.connection:
                    self.logger.info(f"LDAP connection successful on attempt {attempt+1}")
                    return True
            except ldap.SERVER_DOWN as e:
                self.logger.info(f"LDAP connection failed, attempt {attempt+1}")
                attempt += 1
            time.sleep(3)
        self.logger("Failed to connect to LDAP server!")
        raise ldap.SERVER_DOWN("Failed to connect to LDAP server!")

    def __enter__(self):
        if not self.connection:
            self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _dn_user(self, username):
        return f"uid={username},{self.people_dn}"

    def _dn_group(self, group):  
        return f"cn={group},{self.groups_dn}"

    def _search(self, base, scope, filterstr, attrs):
        return self.connection.search_s(base, scope, filterstr, attrs)

    def _search_entities(self, entity_type: str, query: str, attributes: List[str] = None) -> List[Dict]:
        """Generic search method for users or groups"""
        if entity_type == "user":
            base_dn = self.people_dn
            object_class = "posixAccount"
            default_attrs = ['uid', 'cn', 'givenName', 'sn', 'mail']
            search_fields = ["uid", "cn", "givenName", "sn", "mail"]
        else:  # group
            base_dn = self.groups_dn
            object_class = "posixGroup"
            default_attrs = ['cn', 'description']
            search_fields = ["cn", "description"]
        
        attributes = attributes or default_attrs
        search_filters = [f"({field}=*{query}*)" for field in search_fields]
        search_filter = f"(&(objectClass={object_class})(|{''.join(search_filters)}))"
        
        result = self._search(base_dn, ldap.SCOPE_SUBTREE, search_filter, attributes)
        
        entities = []
        for dn, attrs in result:
            if not dn:  # Skip referrals
                continue
                
            if entity_type == "user":
                entity = {
                    'username': self._get_attr_value(attrs, 'uid'),
                    'email': self._get_attr_value(attrs, 'mail'),
                    'name': self._get_attr_value(attrs, 'cn'),
                    'first_name': self._get_attr_value(attrs, 'givenName'),
                    'last_name': self._get_attr_value(attrs, 'sn')
                }
            else:  # group
                entity = {
                    'name': self._get_attr_value(attrs, 'cn'),
                    'description': self._get_attr_value(attrs, 'description')
                }
            entities.append(entity)
        
        return entities

    def _log(self, level:str, msg:str) -> None:
        log_func = getattr(self.logger, level)
        log_func(msg)

    def _log_exc(self, e:Exception, msg:str) -> Exception:
        self.logger.error(msg + f" - {e}")
        return e

    def _get_next_id_number(self, object_type: str, object_class: str) -> int:
        """Generic method to get next UID or GID number"""
        base_dn = self.people_dn if object_type == "uid" else self.groups_dn
        id_attr = f"{object_type}Number"
        
        result = self._search(
            base_dn,
            ldap.SCOPE_SUBTREE,
            f"(objectClass={object_class})",
            [id_attr]
        )
        
        id_numbers = []
        for dn, attrs in result:
            if id_attr in attrs:
                id_numbers.append(int(attrs[id_attr][0].decode("utf-8")))
        
        return max(id_numbers, default=999) + 1

    def _get_next_uid_number(self) -> int:
        return self._get_next_id_number("uid", "posixAccount")
    
    def _get_next_gid_number(self) -> int:
        return self._get_next_id_number("gid", "posixGroup")
        
    def _safe_add(self, dn, attrs, label="entry"):
        try:
            self.connection.add_s(dn, modlist.addModlist(attrs))
            self.logger.info(f"Created {label}: {dn}")
        except ldap.ALREADY_EXISTS:
            self.logger.info(f"{label.capitalize()} already exists: {dn}")

    def _prepare_attributes(self, attrs_dict: Dict[str, Any]) -> Dict[str, List[bytes]]:
        """Convert attribute dictionary to LDAP format with proper encoding"""
        prepared_attrs = {}
        for key, value in attrs_dict.items():
            if value is None:
                continue
            elif isinstance(value, str):
                prepared_attrs[key] = [value.encode("utf-8")]
            elif isinstance(value, list):
                prepared_attrs[key] = [
                    v.encode("utf-8") if isinstance(v, str) else v 
                    for v in value if v is not None
                ]
            elif isinstance(value, bytes):
                prepared_attrs[key] = [value]
            else:
                prepared_attrs[key] = [str(value).encode("utf-8")]
        return prepared_attrs
    
    def _prepare_modifications(self, **kwargs) -> List[tuple]:
        """Prepare modification list for LDAP modify operations"""
        mod_attrs = []
        for key, value in kwargs.items():
            if value is None:
                mod_attrs.append((ldap.MOD_DELETE, key, None))
            elif isinstance(value, str):
                if value.strip():
                    mod_attrs.append((ldap.MOD_REPLACE, key, [value.encode("utf-8")]))
                else:
                    mod_attrs.append((ldap.MOD_DELETE, key, None))
            elif isinstance(value, list):
                clean_values = [
                    v.encode("utf-8") if isinstance(v, str) else v
                    for v in value if v not in (None, "")
                ]
                if clean_values:
                    mod_attrs.append((ldap.MOD_REPLACE, key, clean_values))
                else:
                    mod_attrs.append((ldap.MOD_DELETE, key, None))
        return mod_attrs

    def _check_entity_exists(self, dn: str, entity_type: str) -> bool:
        """Check if an LDAP entity exists"""
        try:
            result = self._search(dn, ldap.SCOPE_BASE, "(objectClass=*)", ["cn"])
            if not result:
                self.logger.warning(f"{entity_type.capitalize()} not found")
                return False
            return True
        except ldap.NO_SUCH_OBJECT:
            self.logger.warning(f"{entity_type.capitalize()} not found")
            return False

    def _modify_group_membership(self, username: str, group_name: str, operation: int, action: str) -> bool:
        """Generic method for adding/removing users from groups"""
        group_dn = self._dn_group(group_name)
        user_dn = self._dn_user(username)
        
        if operation == ldap.MOD_DELETE:
            if not self._can_remove_from_group(username, group_name):
                return False
        
        mod_attrs = [(operation, "uniqueMember", [user_dn.encode("utf-8")])]
        self.connection.modify_s(group_dn, mod_attrs)
        self.logger.info(f"Successfully {action} user {username} {action.replace('ed', '')} group {group_name}")
        return True

    def _can_remove_from_group(self, username: str, group_name: str) -> bool:
        """Check if user can be removed from group (not the last member)"""
        group_dn = self._dn_group(group_name)
        user_dn = self._dn_user(username)

        try:
            result = self._search(
                group_dn, ldap.SCOPE_BASE,
                '(objectClass=groupOfUniqueNames)',
                ['uniqueMember']
            )
            
            if result:
                _, attrs = result[0]
                if 'uniqueMember' in attrs and len(attrs['uniqueMember']) == 1:
                    last_member_dn = attrs['uniqueMember'][0].decode('utf-8')
                    if last_member_dn == user_dn:
                        self.logger.error(
                            f"Cannot remove last member '{username}' from group '{group_name}'. "
                            "This would violate the 'groupOfUniqueNames' schema."
                        )
                        return False
        except ldap.NO_SUCH_OBJECT:
            self.logger.error(f"Group {group_name} not found when trying to remove user.")
            return False
        
        return True

    def _build_entity_dict(self, dn: str, attrs: Dict, entity_type: str) -> Dict:
        """Build standardized entity dictionary from LDAP attributes"""
        if entity_type == "user":
            entity = {
                'username': self._get_attr_value(attrs, 'uid'),
                'email': self._get_attr_value(attrs, 'mail'),
                'first_name': self._get_attr_value(attrs, 'givenName'),
                'last_name': self._get_attr_value(attrs, 'sn'),
                'full_name': self._get_attr_value(attrs, 'cn'),
                'phone': self._get_attr_value(attrs, 'telephoneNumber'),
                'title': self._get_attr_value(attrs, 'title'),
                'uid_number': self._get_attr_value(attrs, 'uidNumber'),
                'gid_number': self._get_attr_value(attrs, 'gidNumber'),
                'groups': self.get_user_groups(self._get_attr_value(attrs, 'uid')),
                'is_active': True,
                'dn': dn
            }
            # Add department for get_user method
            if 'departmentNumber' in attrs:
                entity['department'] = self._get_attr_value(attrs, 'departmentNumber')
        else:  # group
            group_name = self._get_attr_value(attrs, 'cn')
            members = self.get_group_members(group_name)
            entity = {
                'name': group_name,
                'description': self._get_attr_value(attrs, 'description'),
                'gid_number': self._get_attr_value(attrs, 'gidNumber'),
                'members': members,
                'member_count': len(members),
                'dn': dn
            }
        
        return entity

    def _connect(self) -> bool:
        try:
            self.logger.info("Connecting with " + self.ldap_uri)
            self.connection = ldap.initialize(self.ldap_uri)
            self.connection.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
            
            # Handle TLS/StartTLS
            if self.use_ldaps:
                pass # TLS is already established
            elif self.require_starttls:
                # Use StartTLS for LDAP connections
                self.connection.start_tls_s()
            
            self.connection.simple_bind_s(self.admin_bind_dn, self.admin_bind_pwd)
            self.logger.info(f"Successfully connected to LDAP server at {self.ldap_uri}")            
        except LDAPError as e:
            self.logger.error(f"Failed to connect to LDAP server: {e}")
            raise e
    
    def _disconnect(self):
        """Disconnect from LDAP server."""
        if self.connection:
            self.connection.unbind_s()
            self.connection = None
            self.logger.info("Disconnected from LDAP server")
    
    def disconnect(self):
        self._disconnect()

    def setup_ldap_structure(
        self,
        additional_groups:list[str]|None=None
    ) -> bool:
        organizational_units = [
            (self.people_dn, {"objectClass": [b"organizationalUnit"], "ou": [b"users"]}, "users OU"),
            (self.groups_dn, {"objectClass": [b"organizationalUnit"], "ou": [b"groups"]}, "groups OU")
        ]
        
        for dn, attrs, label in organizational_units:
            self._safe_add(dn, attrs, label)

        self.create_admin_user_and_group(additional_groups=additional_groups)

        return True

    def create_admin_user_and_group(
        self,
        username: str = None,
        password: str = None,
        email: str = None,
        additional_groups: list[str] | None = None
    ) -> bool:
        if username is None:
            username = self.admin_username
        if password is None:
            password = self.admin_bind_pwd
        if email is None:
            email = f"{username}@{self.email_domain}"
        if additional_groups is None:
            additional_groups = self._additional_groups.split(",")
        
        user_dn = self._dn_user(username)
        admins_group_dn = self._dn_group(self.admins_group)
        
        # Check if admin user already exists
        try:
            self._search(user_dn, ldap.SCOPE_BASE, "(objectClass=*)", ["uid"])
            self.logger.info(f"Admin user {username} already exists")
            admin_exists = True
        except ldap.NO_SUCH_OBJECT:
            admin_exists = False
        
        def _check_group(grp):
            try:
                self._search(grp, ldap.SCOPE_BASE, "(objectClass=*)", ["cn"])
                self.logger.info(f"Group {grp} already exists")
                return True
            except ldap.NO_SUCH_OBJECT:
                return False

        # Create admin user if it doesn't exist
        if not admin_exists:
            uid_number = self._get_next_uid_number()
            user_attrs = {
                "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"],
                "uid": username,
                "cn": "Administrator User",
                "sn": "User",
                "givenName": "Administrator", 
                "mail": email,
                "userPassword": password,
                "uidNumber": str(uid_number),
                "gidNumber": str(uid_number),
                "homeDirectory": f"/home/{username}",
                "loginShell": "/bin/bash"
            }
            
            prepared_user_attrs = self._prepare_attributes(user_attrs)
            self.connection.add_s(user_dn, modlist.addModlist(prepared_user_attrs))
            self.logger.info(f"Successfully created admin user: {username}")
                
        for group in [self.admins_group, *additional_groups]:
            dn_group = self._dn_group(group)
            if _check_group(dn_group):
                continue # Exists
                
            gid_number = self._get_next_gid_number()
            group_attrs = {
                "objectClass": ["posixGroup", "groupOfUniqueNames"],
                "cn": group,
                "description": f"{group.title()} Group generated by LoStack",
                "gidNumber": str(gid_number),
                "uniqueMember": [user_dn]  # Add admin user as member
            }
            prepared_group_attrs = self._prepare_attributes(group_attrs)
            self.connection.add_s(dn_group, modlist.addModlist(prepared_group_attrs))
            self.logger.info(f"Successfully created group: {group}")

        return True

    
    @ldap_error_handler()
    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        first_name: str,
        last_name: str,
        **kwargs
    ) -> bool:
        user_dn = self._dn_user(username)
        uid_number = self._get_next_uid_number()
        
        user_attrs = {
            "objectClass": ["inetOrgPerson", "posixAccount", "shadowAccount"],
            "uid": username,
            "cn": f"{first_name} {last_name}",
            "sn": last_name,
            "givenName": first_name,
            "mail": email,
            "userPassword": password,
            "uidNumber": str(uid_number),
            "gidNumber": str(uid_number),
            "homeDirectory": f"/home/{username}",
            "loginShell": "/bin/bash",
            **kwargs
        }

        prepared_attrs = self._prepare_attributes(user_attrs)
        self.connection.add_s(user_dn, modlist.addModlist(prepared_attrs))
        self.logger.info(f"Successfully created user: {username}")
        return True
    
    @ldap_error_handler()
    def update_user(self, username: str, **kwargs) -> bool:
        user_dn = self._dn_user(username)
        mod_attrs = self._prepare_modifications(**kwargs)
        
        self.connection.modify_s(user_dn, mod_attrs)
        self.logger.info(f"Successfully updated user: {username}")
        return True

    @ldap_error_handler()
    def update_user_groups(self, username: str, new_groups: list[str]) -> tuple[bool, str]:
        current_groups = set(self.get_user_groups(username))
        target_groups = set(new_groups or [])

        groups_to_add = target_groups - current_groups
        groups_to_remove = current_groups - target_groups
        
        operations = [
            (self.add_user_to_group, groups_to_add, "add"),
            (self.remove_user_from_group, groups_to_remove, "remove")
        ]
        
        all_successful = True
        for operation, groups, action in operations:
            for group in groups:
                if not operation(username, group):
                    all_successful = False

        status = "Successfully" if all_successful else "Could not fully"
        level = "info" if all_successful else "warning"
        msg = f"{status} updated groups for user: {username}"
        
        self._log(level, msg)
        return all_successful, msg
    
    @ldap_error_handler()
    def remove_user(self, username: str) -> bool:
        self.connection.delete_s(self._dn_user(username))
        self.logger.info(f"Successfully removed user: {username}")
        return True
        
    @ldap_error_handler()
    def create_group(
        self,
        group_name: str,
        description: str = None,
        initial_members: list = None
    ) -> bool:
        group_dn = self._dn_group(group_name)
        gid_number = self._get_next_gid_number()
        
        group_attrs = {
            "objectClass": ["posixGroup", "groupOfUniqueNames"],
            "cn": group_name,
            "gidNumber": str(gid_number)
        }
        
        if description is not None:
            group_attrs["description"] = description
        
        if not (initial_members and len(initial_members) > 0):
            self.logger.info(f"Failed to create group, no members specified - {group_name}")
            return False
        
        group_attrs["uniqueMember"] = [self._dn_user(username) for username in initial_members]
        
        prepared_attrs = self._prepare_attributes(group_attrs)
        self.connection.add_s(group_dn, modlist.addModlist(prepared_attrs))
        self.logger.info(f"Successfully created group: {group_name}")
        return True

    @ldap_error_handler()
    def remove_group(self, group_name: str) -> bool:
        group_dn = self._dn_group(group_name)
        
        if not self._check_entity_exists(group_dn, f"Group {group_name}"):
            return False
        
        self.connection.delete_s(group_dn)
        self.logger.info(f"Successfully removed group: {group_name}")
        return True

    @ldap_error_handler()
    def add_user_to_group(self, username: str, group_name: str) -> bool:
        return self._modify_group_membership(username, group_name, ldap.MOD_ADD, "added to")

    @ldap_error_handler()
    def remove_user_from_group(self, username: str, group_name: str) -> bool:
        return self._modify_group_membership(username, group_name, ldap.MOD_DELETE, "removed from")

    @ldap_error_handler()
    def get_user_groups(self, username: str) -> List[str]:
        user_dn = self._dn_user(username)
        search_filter = f"(&(objectClass=groupOfUniqueNames)(uniqueMember={user_dn}))"
        result = self._search(self.groups_dn, ldap.SCOPE_SUBTREE, search_filter, ["cn"])
        
        return [
            attrs["cn"][0].decode("utf-8") 
            for dn, attrs in result 
            if "cn" in attrs
        ]

    @ldap_error_handler()
    def get_group_members(self, group_name: str) -> List[str]:
        group_dn = self._dn_group(group_name)
        result = self._search(group_dn, ldap.SCOPE_BASE, "(objectClass=*)", ["uniqueMember"])
        
        if not result:
            return []
        
        members = []
        attrs = result[0][1]
        
        if "uniqueMember" in attrs:
            for member_dn in attrs["uniqueMember"]:
                member_dn_str = member_dn.decode("utf-8")
                if member_dn_str and "uid=" in member_dn_str:
                    try:
                        uid = member_dn_str.split(",")[0].split("uid=")[1]
                        members.append(uid)
                    except (IndexError, ValueError):
                        self.logger.warning(f"Could not parse member DN: {member_dn_str}")
                        continue
        
        return members
        
    @ldap_error_handler()
    def update_group(self, group_name: str, **kwargs) -> bool:
        group_dn = self._dn_group(group_name)
        mod_attrs = self._prepare_modifications(**kwargs)
        
        if mod_attrs:
            self.connection.modify_s(group_dn, mod_attrs)
            self.logger.info(f"Successfully updated group: {group_name}")
        else:
            self.logger.info(f"No changes requested for group: {group_name}")
        return True

    @ldap_error_handler()
    def get_all_users(self, search_filter="(objectClass=posixAccount)"):
        result = self._search(
            self.people_dn, ldap.SCOPE_SUBTREE, search_filter,
            ['uid', 'cn', 'givenName', 'sn', 'mail', 'telephoneNumber', 
            'departmentNumber', 'title', 'uidNumber', 'gidNumber']
        )
        
        return [
            self._build_entity_dict(dn, attrs, "user")
            for dn, attrs in result if dn  # Skip referrals
        ]
        
    @ldap_error_handler()
    def get_all_groups(self, search_filter="(objectClass=posixGroup)"):
        result = self._search(
            self.groups_dn, ldap.SCOPE_SUBTREE, search_filter,
            ['cn', 'description', 'gidNumber', 'member']
        )
        
        return [
            self._build_entity_dict(dn, attrs, "group")
            for dn, attrs in result if dn  # Skip referrals
        ]
        
    @ldap_error_handler()
    def get_user(self, username):
        user_dn = self._dn_user(username)
        result = self._search(
            user_dn, ldap.SCOPE_BASE, '(objectClass=*)',
            ['uid', 'cn', 'givenName', 'sn', 'mail', 'telephoneNumber', 
            'departmentNumber', 'title', 'uidNumber', 'gidNumber']
        )
        
        if not result:
            return None
        
        dn, attrs = result[0]
        return self._build_entity_dict(dn, attrs, "user")
        
    @ldap_error_handler()
    def get_group(self, group_name):
        group_dn = self._dn_group(group_name)
        result = self._search(
            group_dn, ldap.SCOPE_BASE, '(objectClass=*)',
            ['cn', 'description', 'gidNumber', 'member']
        )
        
        if not result:
            return None
        
        dn, attrs = result[0]
        return self._build_entity_dict(dn, attrs, "group")

    @ldap_error_handler()
    def search_users(self, query, attributes=None):
        return self._search_entities("user", query, attributes)
    
    @ldap_error_handler()
    def search_groups(self, query, attributes=None):
        return self._search_entities("group", query, attributes)

    @ldap_error_handler()
    def get_connection_status(self):
        self._search(self.base_dn, ldap.SCOPE_BASE, '(objectClass=*)', ['dc'])
        
        return {
            'status': 'Connected',
            'server': self.ldap_uri,
            'base_dn': self.base_dn,
            'bind_dn': self.admin_bind_dn
        }
    
    @ldap_error_handler()
    def get_directory_stats(self):
        stats = {
            'total_users': 0,
            'total_groups': 0,
            'active_users': 0,
            'connection_status': 'Connected'
        }
        
        # Count entities using a generic helper
        entity_counts = [
            (self.people_dn, '(objectClass=posixAccount)', 'total_users'),
            (self.groups_dn, '(objectClass=posixGroup)', 'total_groups')
        ]
        
        for base_dn, filter_str, stat_key in entity_counts:
            result = self._search(base_dn, ldap.SCOPE_SUBTREE, filter_str, ['cn'])
            stats[stat_key] = len([r for r in result if r[0]])
        
        stats['active_users'] = stats['total_users']  # handle better dashboard stats later
        return stats
    
    def _get_attr_value(self, attrs, attr_name, default=''):
        if attr_name in attrs and attrs[attr_name]:
            value = attrs[attr_name][0]
            return value.decode('utf-8') if isinstance(value, bytes) else value
        return default

def setup_ldap_manager(app) -> LDAPManager:
    return LDAPManager(app)