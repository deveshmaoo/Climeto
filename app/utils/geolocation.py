import requests
from flask import current_app

def get_location_from_ip(ip_address):
    """Get location information from IP address using a geolocation service"""
    try:
        # Skip for localhost/private IPs
        if ip_address in ('127.0.0.1', 'localhost') or ip_address.startswith('192.168.'):
            return 'Office Network'
            
        # Use a geolocation service (example using ipapi.co)
        api_key = current_app.config.get('IPAPI_KEY')
        if api_key:
            response = requests.get(
                f'https://ipapi.co/{ip_address}/json/',
                params={'key': api_key}
            )
            if response.status_code == 200:
                data = response.json()
                return f"{data.get('city', '')}, {data.get('country_name', '')}"
        
        return 'Unknown Location'
    except Exception as e:
        current_app.logger.error(f"Error getting location for IP {ip_address}: {str(e)}")
        return 'Unknown Location' 