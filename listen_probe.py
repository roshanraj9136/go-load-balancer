import socket
import threading
import time

ports = [3000, 3297, 4297, 5297, 6297, 7297, 8000, 8001, 8080, 80]

def listen_port(p):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', p))
        s.listen(5)
        print(f"LISTENING ON {p}", flush=True)
        while True:
            conn, addr = s.accept()
            print(f"*** HIT RECEIVED ON PORT {p} from {addr} ***", flush=True)
            data = conn.recv(1024)
            resp = f"HTTP/1.1 200 OK\r\nContent-Length: 16\r\n\r\nMATCHED PORT {p}\n"
            conn.sendall(resp.encode())
            conn.close()
    except Exception as e:
        print(f"Port {p} error: {e}", flush=True)

threads = []
for p in ports:
    t = threading.Thread(target=listen_port, args=(p,), daemon=True)
    t.start()
    threads.append(t)

time.sleep(30)
