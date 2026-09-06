import subprocess
import time
import json
import os

nodes = [
    {"name": "Sys1 (Load Balancer)", "port": 2297},
    {"name": "Sys2 (Backend 1 + DB)", "port": 2298},
    {"name": "Sys3 (Backend 2)", "port": 2299},
    {"name": "Sys4 (Backend 3)", "port": 2300}
]

ssh_key = r"C:\Users\hp\.ssh\id_ed25519"

def sample_node(port):
    cmd = [
        "ssh", "-i", ssh_key, "-p", str(port),
        "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=3",
        "student@10.1.75.53",
        "awk '/^cpu / {print $2+$4, $2+$4+$5}' /proc/stat; free -m | awk '/^Mem:/ {print $2, $3}'"
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        lines = p.stdout.strip().split("\n")
        cpu_busy, cpu_total = map(int, lines[0].split())
        mem_total, mem_used = map(int, lines[1].split())
        mem_pct = round((mem_used / mem_total) * 100, 2)
        return {"busy": cpu_busy, "total": cpu_total, "mem_pct": mem_pct, "mem_used_mb": mem_used}
    except Exception as e:
        return None

prev_samples = {n["port"]: sample_node(n["port"]) for n in nodes}
time.sleep(1)

results = []
for step in range(15):
    step_data = {"timestamp": step * 2, "nodes": {}}
    for n in nodes:
        curr = sample_node(n["port"])
        prev = prev_samples.get(n["port"])
        if curr and prev:
            d_busy = curr["busy"] - prev["busy"]
            d_total = curr["total"] - prev["total"]
            cpu_pct = round((d_busy / max(1, d_total)) * 100, 2)
            step_data["nodes"][n["name"]] = {
                "cpu_pct": cpu_pct,
                "mem_pct": curr["mem_pct"],
                "mem_used_mb": curr["mem_used_mb"]
            }
        prev_samples[n["port"]] = curr
    results.append(step_data)
    time.sleep(1)

with open("D:/go-load-balancer/results/system_utilization.json", "w") as f:
    json.dump(results, f, indent=2)

print("SUCCESS_LOCAL_UTILIZATION")
