#!/bin/bash
set -e
mkdir -p /home/student/go-load-balancer/results
cd /home/student/go-load-balancer

echo "=== 1. Baseline Benchmark: Single Backend (Sys2 only) ==="
pkill -9 -f "go-load-balancer/bin/loadbalancer" 2>/dev/null || true
sleep 1
tmux kill-session -t lb 2>/dev/null || true
sleep 1
tmux new-session -d -s lb "/home/student/go-load-balancer/bin/loadbalancer -port 3297 -backends http://172.17.0.99:3298 -threshold 20 -fallback http://127.0.0.1:8001"
sleep 2

./bin/client -url "http://127.0.0.1:3297" -requests 3000 -concurrency 25 -experiment "Single_Backend_Baseline" -out results/exp1_single.json -csv results/comparison.csv

echo "=== 2. Distributed Benchmark: 3 Backends (Dynamic LB, Threshold=20) ==="
pkill -9 -f "go-load-balancer/bin/loadbalancer" 2>/dev/null || true
sleep 1
tmux kill-session -t lb 2>/dev/null || true
sleep 1
tmux new-session -d -s lb "/home/student/go-load-balancer/bin/loadbalancer -port 3297 -backends http://172.17.0.99:3298,http://172.17.0.100:3299,http://172.17.0.101:3300 -threshold 20 -fallback http://127.0.0.1:8001"
sleep 2

./bin/client -url "http://127.0.0.1:3297" -requests 3000 -concurrency 25 -experiment "Three_Backends_T20" -out results/exp2_three_t20.json -csv results/comparison.csv

echo "=== 3. Threshold Optimization Sweep: T=5, T=10, T=20, T=50, T=100 ==="
for T in 5 10 20 50 100; do
    pkill -9 -f "go-load-balancer/bin/loadbalancer" 2>/dev/null || true
    sleep 1
    tmux kill-session -t lb 2>/dev/null || true
    sleep 1
    tmux new-session -d -s lb "/home/student/go-load-balancer/bin/loadbalancer -port 3297 -backends http://172.17.0.99:3298,http://172.17.0.100:3299,http://172.17.0.101:3300 -threshold $T -fallback http://127.0.0.1:8001"
    sleep 2

    ./bin/client -url "http://127.0.0.1:3297" -requests 2500 -concurrency 30 -experiment "Threshold_Opt_T${T}" -out "results/threshold_t${T}.json" -csv results/threshold_sweep.csv
done

echo "=== 4. Fault Tolerance Test: Backend 2 Crash & Recovery ==="
pkill -9 -f "go-load-balancer/bin/loadbalancer" 2>/dev/null || true
sleep 1
tmux kill-session -t lb 2>/dev/null || true
sleep 1
tmux new-session -d -s lb "/home/student/go-load-balancer/bin/loadbalancer -port 3297 -backends http://172.17.0.99:3298,http://172.17.0.100:3299,http://172.17.0.101:3300 -threshold 20 -fallback http://127.0.0.1:8001"
sleep 2

ssh -i /home/student/.ssh/id_ed25519 -p 2299 -o StrictHostKeyChecking=no student@10.1.75.53 "pkill -9 -f backend || true; tmux kill-session -t backend || true" || true

./bin/client -url "http://127.0.0.1:3297" -requests 2000 -concurrency 20 -experiment "Fault_Tolerance_Node_Down" -out results/exp4_fault.json -csv results/comparison.csv

ssh -i /home/student/.ssh/id_ed25519 -p 2299 -o StrictHostKeyChecking=no student@10.1.75.53 "bash /home/student/start_backend.sh backend-2 3299 postgres://chatuser:chatpass@172.17.0.99:5432/chatdb?sslmode=disable" || true
sleep 3

echo "=== Experiments Completed Successfully ==="
