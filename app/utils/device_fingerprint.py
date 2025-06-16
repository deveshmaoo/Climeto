import hashlib
from flask import request

def get_device_fingerprint(request):
    """Generate a unique device fingerprint based on various request attributes"""
    # Collect device-specific information
    user_agent = request.headers.get('User-Agent', '')
    accept_language = request.headers.get('Accept-Language', '')
    accept_encoding = request.headers.get('Accept-Encoding', '')
    screen_resolution = request.cookies.get('screen_resolution', '')
    timezone = request.cookies.get('timezone', '')
    
    # Combine all attributes
    device_string = f"{user_agent}|{accept_language}|{accept_encoding}|{screen_resolution}|{timezone}"
    
    # Generate hash
    return hashlib.sha256(device_string.encode()).hexdigest() 