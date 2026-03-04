#!/usr/bin/env python3
"""
Mock FledgePOWER Gateway Server
デモ用の簡易版FledgePOWERゲートウェイ
実際のFledgePOWERは利用できないため、最小限のHTTPエンドポイントを提供
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime
import uvicorn
import os
import redis
import time

app = FastAPI(title="Mock FledgePOWER Gateway")

# Redis接続設定
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis.data-zone.svc.cluster.local')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))

# 起動時刻
START_TIME = time.time()

@app.get("/fledge/ping")
async def ping():
    """Health check endpoint for liveness/readiness probes"""
    return {
        "uptime": 0,
        "dataRead": 0,
        "dataSent": 0,
        "dataPurged": 0,
        "authenticationOptional": True,
        "serviceName": "FledgePOWER-Gateway",
        "hostName": os.environ.get('HOSTNAME', 'fledgepower'),
        "ipAddresses": ["0.0.0.0"],
        "health": "green",
        "safeMode": False
    }

@app.get("/fledge/service")
async def service():
    """Service information endpoint"""
    return {
        "services": [
            {
                "name": "FledgePOWER-Gateway",
                "type": "Southbound",
                "protocol": "http",
                "address": "0.0.0.0",
                "management_port": 1995,
                "service_port": 8081,
                "status": "running"
            }
        ]
    }

@app.get("/fledge/asset")
async def assets():
    """Mock assets endpoint"""
    return []

@app.get("/api/info")
async def api_info():
    """API Information endpoint"""
    return {
        "service": "Mock FledgePOWER Gateway",
        "version": "1.0.0",
        "status": "running",
        "note": "This is a mock implementation for demo purposes"
    }

@app.get("/api/stats")
async def get_stats():
    """Get gateway statistics"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        fledge_stream_len = r.xlen('fledge-telemetry') if r.exists('fledge-telemetry') else 0
        r.close()

        uptime = int(time.time() - START_TIME)

        return {
            "uptime_seconds": uptime,
            "redis_stream": "fledge-telemetry",
            "messages_sent": fledge_stream_len,
            "status": "running",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "uptime_seconds": int(time.time() - START_TIME),
            "redis_stream": "fledge-telemetry",
            "messages_sent": 0,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

@app.get("/", response_class=HTMLResponse)
async def gui_root():
    """FledgePOWER Gateway Web UI"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FledgePOWER Gateway - Management UI</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .header h1 {
            color: #667eea;
            font-size: 2em;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h2 {
            color: #667eea;
            font-size: 1.5em;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .stat-item:last-child {
            border-bottom: none;
        }
        .stat-label {
            color: #666;
            font-weight: 500;
        }
        .stat-value {
            color: #333;
            font-weight: bold;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-running {
            background: #10b981;
            color: white;
        }
        .status-error {
            background: #ef4444;
            color: white;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            margin-top: 15px;
            transition: background 0.3s ease;
        }
        .refresh-btn:hover {
            background: #5568d3;
        }
        .footer {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            color: #666;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .endpoint-list {
            list-style: none;
            padding: 0;
        }
        .endpoint-list li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .endpoint-list li:last-child {
            border-bottom: none;
        }
        .endpoint-list code {
            background: #f3f4f6;
            padding: 2px 8px;
            border-radius: 3px;
            font-family: monospace;
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔌 FledgePOWER Gateway</h1>
            <p>Digital Twin Substation Edge Data Gateway</p>
        </div>

        <div class="grid">
            <div class="card">
                <h2>📊 System Status</h2>
                <div class="stat-item">
                    <span class="stat-label">Service Status:</span>
                    <span class="stat-value"><span id="status" class="status-badge status-running">Running</span></span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Uptime:</span>
                    <span class="stat-value" id="uptime">Loading...</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Version:</span>
                    <span class="stat-value">1.0.0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Last Update:</span>
                    <span class="stat-value" id="timestamp">Loading...</span>
                </div>
                <button class="refresh-btn" onclick="refreshStats()">🔄 Refresh</button>
            </div>

            <div class="card">
                <h2>📤 Data Pipeline</h2>
                <div class="stat-item">
                    <span class="stat-label">Redis Stream:</span>
                    <span class="stat-value">fledge-telemetry</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Messages Sent:</span>
                    <span class="stat-value" id="messages">Loading...</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Source IEDs:</span>
                    <span class="stat-value">OT Zone</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Target:</span>
                    <span class="stat-value">Data Zone</span>
                </div>
            </div>

            <div class="card">
                <h2>🔗 API Endpoints</h2>
                <ul class="endpoint-list">
                    <li><code>GET /</code> - This GUI</li>
                    <li><code>GET /fledge/ping</code> - Health check</li>
                    <li><code>GET /fledge/service</code> - Service info</li>
                    <li><code>GET /fledge/asset</code> - Assets list</li>
                    <li><code>GET /api/stats</code> - Statistics</li>
                    <li><code>GET /api/info</code> - API info</li>
                </ul>
            </div>
        </div>

        <div class="footer">
            <p>FledgePOWER Gateway Mock Implementation for Digital Twin Substations Demo</p>
            <p style="margin-top: 10px; font-size: 0.9em;">Edge Zone • OpenShift Local</p>
        </div>
    </div>

    <script>
        async function refreshStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();

                document.getElementById('uptime').textContent = formatUptime(data.uptime_seconds);
                document.getElementById('messages').textContent = data.messages_sent.toLocaleString();
                document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleTimeString();

                const statusEl = document.getElementById('status');
                if (data.status === 'running') {
                    statusEl.className = 'status-badge status-running';
                    statusEl.textContent = 'Running';
                } else {
                    statusEl.className = 'status-badge status-error';
                    statusEl.textContent = 'Error';
                }
            } catch (error) {
                console.error('Failed to fetch stats:', error);
            }
        }

        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);

            if (days > 0) {
                return `${days}d ${hours}h ${minutes}m`;
            } else if (hours > 0) {
                return `${hours}h ${minutes}m ${secs}s`;
            } else if (minutes > 0) {
                return `${minutes}m ${secs}s`;
            } else {
                return `${secs}s`;
            }
        }

        // Refresh stats on page load
        refreshStats();

        // Auto-refresh every 5 seconds
        setInterval(refreshStats, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    # Start server on port 8081 (Fledge GUI port)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081,
        log_level="info"
    )
