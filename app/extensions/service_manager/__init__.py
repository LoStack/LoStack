from flask import Flask
from .service_manager import ServiceManager

def init_service_manager(app:Flask) -> ServiceManager:
    return ServiceManager(app)