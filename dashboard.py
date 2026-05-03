#!/usr/bin/env python3
from flask import Flask, render_template_string, jsonify
import psutil
import subprocess
import datetime
import os
import time
import re

app = Flask(__name__)

# Cache for Minecraft status (updates every 30 seconds)
mc_cache = {
    'online': False,
    'players': [],
    'last_update': 0,
    'cache_ttl': 30 # seconds between updates
}

def get_minecraft_status_cached():
    """
    Get Minecraft status with caching to save CPU
    """
    now = time.time()
    
    # Return cached data if still fresh
    if now - mc_cache['last_update'] < mc_cache['cache_ttl']:
        return mc_cache['online'], mc_cache['players']
    
    # Update cache
    mc_cache['online'], mc_cache['players'] = get_minecraft_status_real()
    mc_cache['last_update'] = now
    return mc_cache['online'], mc_cache['players']

def get_minecraft_status_real():
    """
    Get REAL Minecraft status using RCON
    """
    try:
        # Check if server process is running
        result = subprocess.run(['pgrep', '-f', 'server.jar'], capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, []
        
        # Use mcrcon to get player list
        cmd = ['mcrcon', '-H', '127.0.0.1', '-P', '25575', '-p', 'YOUR_RCON_PASSWORD', 'list']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        output = result.stdout.strip()
        
        # Remove ANSI color codes (like \033[0m, \x1b[0m, etc.)
        import re
        output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        
        print(f"DEBUG: Cleaned RCON output = '{output}'")
        
        # Parse output - example: "There are 1 of a max of 20 players online: jello_eaterr"
        players = []
        if "players online:" in output.lower():
            # Extract everything after the colon
            if ":" in output:
                players_part = output.split(":", 1)[1].strip()
                # Split by commas and clean up
                players = [p.strip() for p in players_part.split(",") if p.strip()]
        
        return True, players
        
    except subprocess.TimeoutExpired:
        print("RCON timeout - server not responding")
        return True, []
    
    except subprocess.CalledProcessError as e:
        print(f"RCON command failed: {e}")
        return True, []
    
    except Exception as e:
        print(f"Unexpected error in RCON: {e}")
        return True, []
    
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Home Server Dashboard</title>
    <meta http-equiv="refresh" content="10">
    
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #1e1e1e; color: #eee; }
        .container { max-width: 800px; margin: auto; background: #2d2d2d; padding: 20px; border-radius: 10px; }
        h1 { color: #4caf50; }
        .status-online { color: #4caf50; font-weight: bold; }
        .status-offline { color: #f44336; font-weight: bold; }
        .metric { margin: 15px 0; padding: 10px; background: #3d3d3d; border-radius: 5px; }
        .bar { background: #4caf50; height: 20px; border-radius: 10px; margin-top: 5px; }
        .bar-container { background: #555; border-radius: 10px; overflow: hidden; }
        .last-update { font-size: 12px; color: #888; text-align: right; margin-top: 20px; }
    </style>
    
</head>
<body>
    <div class="container">
        <h1>🖥️ Home Server Dashboard</h1>
        
        <div class="metric">
            <strong>System Uptime:</strong><br>
            {{ uptime }}
        </div>
        
        <div class="metric">
            <strong>Memory Usage:</strong><br>
            {{ memory_used }} GB / {{ memory_total }} GB ({{ memory_percent }}%)
            <div class="bar-container">
                <div class="bar" style="width: {{ memory_percent }}%;"></div>
            </div>
        </div>
        
        <div class="metric">
            <strong>⚙️ CPU Usage:</strong><br>
            {{ cpu_percent }}%
            <div class="bar-container">
                <div class="bar" style="width: {{ cpu_percent }}%;"></div>
            </div>
        </div>
        
        <div class="metric">
            <strong>Minecraft Server:</strong><br>
            {% if mc_online %}
                <span class="status-online">ONLINE</span>
                {% if mc_players %}
                    <br>Players online ({{ mc_player_count }}): {{ mc_players|join(', ') }}
                {% else %}
                    <br>No players online
                {% endif %}
            {% else %}
                <span class="status-offline">OFFLINE</span>
            {% endif %}
        </div>
        
        <div class="metric">
            <strong>System Info:</strong><br>
            CPU Cores: {{ cpu_count }}<br>
            Server Time: {{ current_time }}
        </div>
        
        <div class="last-update">
            Page auto-refreshes every {{cache_ttl}} seconds
        </div>
    </div>
</body>
</html>
"""

def get_uptime():
    """
    Reads from /proc/uptime and uses psutil library to get memory and CPU stats
    """
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return str(datetime.timedelta(seconds=int(uptime_seconds)))

@app.route('/')
def dashboard():
    
    # Memory stats
    memory = psutil.virtual_memory()
    memory_used = round(memory.used / (1024**3), 1)
    memory_total = round(memory.total / (1024**3), 1)
    memory_percent = memory.percent
    
    # CPU stats
    cpu_percent = psutil.cpu_percent(interval = 0.5)
    cpu_count = psutil.cpu_count()
    
    # Time server has been up
    uptime = get_uptime()
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Checks if server is online and how many players are in server
    mc_online, mc_players = get_minecraft_status_cached()
    mc_player_count = len(mc_players)
    
    # Whats rendered
    return render_template_string(HTML_TEMPLATE, 
                                   uptime = uptime,
                                   memory_used = memory_used,
                                   memory_total = memory_total,
                                   memory_percent = memory_percent,
                                   cpu_percent = cpu_percent,
                                   cpu_count = cpu_count,
                                   current_time = current_time,
                                   mc_online = mc_online,
                                   mc_players = mc_players,
                                   mc_player_count = mc_player_count, 
                                   cache_ttl = mc_cache['cache_ttl'])

# Run
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000, debug = False, threaded=True)