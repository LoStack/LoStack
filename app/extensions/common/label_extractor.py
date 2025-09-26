"""Handler to normalize and extract values from labels"""

class LabelExtractor:
    """Centralized label extraction to reduce redundancy"""
    
    @staticmethod
    def normalize_labels(labels):
        """Normalize labels to dict format"""
        if isinstance(labels, list):
            normalized = {}
            for label in labels:
                if isinstance(label, str) and '=' in label:
                    key, value = label.split('=', 1)
                    normalized[key.strip()] = value.strip()
            return normalized
        elif isinstance(labels, dict):
            return {k: str(v) for k, v in labels.items()}
        return {}
    
    @staticmethod
    def get_by_prefix(labels, prefix):
        """Get first label value matching prefix"""
        normalized = LabelExtractor.normalize_labels(labels)
        for key, value in normalized.items():
            if key.startswith(prefix):
                return value
        return None
    
    @staticmethod
    def get_by_suffix(labels, suffix):
        """Get first label value with matching suffix"""
        normalized = LabelExtractor.normalize_labels(labels)
        for key, value in normalized.items():
            if key.endswith(suffix):
                return value
        return None
    
    @staticmethod
    def get_lostack_port(labels, default=None):
        """Extract Traefik port from labels"""
        port = LabelExtractor.get_label(labels, "lostack.port").strip('"')
        return port or str(default) if default else port
    
    @staticmethod
    def get_traefik_router(labels):
        """Extract Traefik router rule from labels"""
        normalized = LabelExtractor.normalize_labels(labels)
        for key, value in normalized.items():
            if key.startswith('traefik.http.routers.') and key.endswith('.rule'):
                return value
        return None
    
    @staticmethod
    def get_friendly_name(labels, fallback=None):
        """Extract friendly name with fallback"""
        normalized = LabelExtractor.normalize_labels(labels)
        return (
            normalized.get('homepage.name') or
            normalized.get('lostack.name') or
            (fallback.title() if fallback else None)
        )
    
    @staticmethod
    def get_tags(labels):
        """Extract and clean tags from labels"""
        normalized = LabelExtractor.normalize_labels(labels)
        tags_str = normalized.get('lostack.tags', '')
        if not tags_str:
            return []
        return [tag.strip().title() for tag in tags_str.split(',')]
    
    @staticmethod
    def parse_boolean(value) -> bool:
        """Parse Docker label value to Python bool"""
        if isinstance(value, int):
            return value == 1
        if isinstance(value, bool):
            return value
        if not isinstance(value, str) or not value:
            try:
                value = str(value)
            except:
                raise ValueError("Invalid value for boolean parsing")
        
        if value.lower() in ('true', '1', 'yes', 'on', 'enable', 'enabled'):
            return True
        elif value.lower() in ('false', '0', 'no', 'off', 'disable', 'disabled'):
            return False
        else:
            raise ValueError(f"Could not parse boolean value")

    @staticmethod
    def get_label(labels, key):
        """Extract value from labels with given key"""
        normalized = LabelExtractor.normalize_labels(labels)
        return normalized.get(key)