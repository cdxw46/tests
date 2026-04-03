import http.server
import socketserver
import os

os.chdir("/workspace/web")
handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("0.0.0.0", 80), handler) as httpd:
    print("Servidor web en puerto 80")
    httpd.serve_forever()
