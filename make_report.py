import os
import html

def build():
    with open("loadbalancer/main.go", "r", encoding="utf-8") as f:
        lb_code = f.read().strip()
    with open("backend/main.go", "r", encoding="utf-8") as f:
        backend_code = f.read().strip()
    with open("client/main.go", "r", encoding="utf-8") as f:
        client_code = f.read().strip()
    
    return lb_code, backend_code, client_code

print("Ready")
