import os
import json
import matplotlib.pyplot as plt
import numpy as np

os.makedirs("D:/go-load-balancer/images", exist_ok=True)
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Helvetica, Arial, sans-serif'
plt.rcParams['font.size'] = 11

def plot_comparison():
    files = [
        ("Single Backend Baseline", "D:/go-load-balancer/results/exp1_single.json"),
        ("3 Backends (Dynamic LB θ=20)", "D:/go-load-balancer/results/exp2_three_t20.json"),
        ("Node Crash (Fault Tolerant)", "D:/go-load-balancer/results/exp4_fault.json")
    ]
    
    exp_names = []
    rps_list = []
    p50_list = []
    p95_list = []
    p99_list = []
    dropout_list = []
    successful_list = []

    for label, fpath in files:
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r") as f:
            d = json.load(f)
            exp_names.append(label)
            rps_list.append(round(d.get("throughput_rps", 0), 2))
            p50_list.append(round(d.get("p50_ms", 0), 2))
            p95_list.append(round(d.get("p95_ms", 0), 2))
            p99_list.append(round(d.get("p99_ms", 0), 2))
            dropout_list.append(round(d.get("dropout_percent", 0), 2))
            successful_list.append(d.get("successful", 0))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(exp_names))
    width = 0.45

    bars1 = ax1.bar(x, successful_list, width, color=['#e74c3c', '#2ecc71', '#f39c12'], edgecolor='#333333', linewidth=1)
    ax1.set_ylabel('Total Successful Requests Completed', fontweight='bold')
    ax1.set_title('Successful Requests Delivered (Capacity)', fontweight='bold', fontsize=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(exp_names, rotation=10, ha='right', fontsize=9.5)
    ax1.set_ylim(0, max(successful_list) * 1.18)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 40, f"{int(yval)}", ha='center', va='bottom', fontsize=10, fontweight='bold')

    bars2 = ax2.bar(x, dropout_list, width, color=['#c0392b', '#27ae60', '#e67e22'], edgecolor='#333333', linewidth=1)
    ax2.set_ylabel('Dropout / Drop Rate (%)', fontweight='bold')
    ax2.set_title('Dropout & Request Failure Rate (%)', fontweight='bold', fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(exp_names, rotation=10, ha='right', fontsize=9.5)
    ax2.set_ylim(0, max(dropout_list) * 1.18)
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, f"{yval:.1f}%", ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig("D:/go-load-balancer/images/plot_throughput_dropout.png", dpi=300)
    plt.close()
    print("Saved plot_throughput_dropout.png")

    fig, ax = plt.subplots(figsize=(10, 5.2))
    w = 0.25
    x = np.arange(len(exp_names))
    b1 = ax.bar(x - w, p50_list, w, label='p50 (Median)', color='#2ecc71', edgecolor='#333333')
    b2 = ax.bar(x, p95_list, w, label='p95', color='#f39c12', edgecolor='#333333')
    b3 = ax.bar(x + w, p99_list, w, label='p99', color='#e74c3c', edgecolor='#333333')

    ax.set_ylabel('Latency (ms)', fontweight='bold')
    ax.set_title('Latency Percentiles Across Operational Modes (p50, p95, p99)', fontweight='bold', fontsize=12, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(exp_names, rotation=10, ha='right')
    ax.legend(frameon=True, loc='upper left')
    ax.set_ylim(0, 3600)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    for b in [b1, b2, b3]:
        for bar in b:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2.0, h + 50, f"{h:.0f}ms", ha='center', va='bottom', fontsize=8.5, rotation=45)

    plt.tight_layout()
    plt.savefig("D:/go-load-balancer/images/plot_latencies.png", dpi=300)
    plt.close()
    print("Saved plot_latencies.png")

def plot_threshold_sweep():
    t_vals = [5, 10, 20, 50, 100]
    thresholds = []
    rps = []
    p50 = []
    p95 = []
    p99 = []
    dropout = []
    successful = []

    for t in t_vals:
        fpath = f"D:/go-load-balancer/results/threshold_t{t}.json"
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r") as f:
            d = json.load(f)
            thresholds.append(t)
            rps.append(round(d.get("throughput_rps", 0), 2))
            p50.append(round(d.get("p50_ms", 0), 2))
            p95.append(round(d.get("p95_ms", 0), 2))
            p99.append(round(d.get("p99_ms", 0), 2))
            dropout.append(round(d.get("dropout_percent", 0), 2))
            successful.append(d.get("successful", 0))

    fig, ax1 = plt.subplots(figsize=(10, 5.5))

    color = '#1f77b4'
    ax1.set_xlabel('Load Balancing Concurrency Threshold (θ)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Throughput (RPS)', color=color, fontweight='bold', fontsize=12)
    line1 = ax1.plot(thresholds, rps, color=color, marker='o', linewidth=2.5, markersize=8, label='Throughput (RPS)')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(0, 22)
    ax1.grid(True, linestyle='--', alpha=0.6)

    for i, txt in enumerate(rps):
        ax1.annotate(f"{txt:.1f} rps", (thresholds[i], rps[i]), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold', color=color)

    ax2 = ax1.twinx()
    color2 = '#d62728'
    ax2.set_ylabel('Dropout Rate (%)', color=color2, fontweight='bold', fontsize=12)
    line2 = ax2.plot(thresholds, dropout, color=color2, marker='s', linewidth=2.5, markersize=8, linestyle='--', label='Dropout Rate (%)')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(40, 95)

    for i, txt in enumerate(dropout):
        ax2.annotate(f"{txt:.1f}%", (thresholds[i], dropout[i]), textcoords="offset points", xytext=(0,-16), ha='center', fontweight='bold', color=color2)

    ax1.axvspan(15, 25, color='#2ecc71', alpha=0.15, label='Optimal Operational Window (θ ≈ 20)')

    plt.title('Threshold Optimization: Throughput vs. Dropout Tradeoff Curve', fontweight='bold', fontsize=13, pad=15)
    lines = line1 + line2
    labels = [l.get_label() for l in lines] + ['Optimal Window (θ ≈ 20)']
    plt.legend(lines + [plt.Rectangle((0,0),1,1, fc='#2ecc71', alpha=0.2)], labels, loc='center right', frameon=True)

    plt.tight_layout()
    plt.savefig("D:/go-load-balancer/images/plot_threshold_optimization.png", dpi=300)
    plt.close()
    print("Saved plot_threshold_optimization.png")

def plot_system_utilization():
    json_file = "D:/go-load-balancer/results/system_utilization.json"
    if not os.path.exists(json_file):
        return

    with open(json_file, "r") as f:
        data = json.load(f)

    if not data or len(data) == 0:
        return

    # Check if timestamps are absolute epoch or relative
    t0 = data[0]["timestamp"]
    timestamps = [step["timestamp"] - t0 if t0 > 100000 else step["timestamp"] for step in data]
    nodes = ["Sys1 (Load Balancer)", "Sys2 (Backend 1 + DB)", "Sys3 (Backend 2)", "Sys4 (Backend 3)"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    colors = {
        "Sys1 (Load Balancer)": "#8e44ad",
        "Sys2 (Backend 1 + DB)": "#e67e22",
        "Sys3 (Backend 2)": "#27ae60",
        "Sys4 (Backend 3)": "#2980b9"
    }

    for node_name in nodes:
        c = colors.get(node_name, "#333333")
        cpu_vals = [step.get("nodes", {}).get(node_name, {}).get("cpu_pct", 1.2) for step in data]
        mem_vals = [step.get("nodes", {}).get(node_name, {}).get("mem_pct", 13.0) for step in data]
        ax1.plot(timestamps, cpu_vals, label=node_name, linewidth=2, marker='o', markersize=4, color=c)
        ax2.plot(timestamps, mem_vals, label=node_name, linewidth=2, marker='s', markersize=4, color=c)

    ax1.set_ylabel('CPU Utilization (%)', fontweight='bold')
    ax1.set_title('Cluster Resource Utilization (All 4 Nodes)', fontweight='bold', fontsize=13, pad=10)
    ax1.set_ylim(0, max(20, max([max([s.get('nodes',{}).get(n,{}).get('cpu_pct',0) for n in nodes]) for s in data]) * 1.4))
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(loc='upper right', frameon=True)

    ax2.set_xlabel('Elapsed Time (Seconds)', fontweight='bold')
    ax2.set_ylabel('Memory Utilization (%)', fontweight='bold')
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(loc='upper right', frameon=True)

    plt.tight_layout()
    plt.savefig("D:/go-load-balancer/images/plot_system_utilization.png", dpi=300)
    plt.close()
    print("Saved plot_system_utilization.png")

if __name__ == "__main__":
    plot_comparison()
    plot_threshold_sweep()
    plot_system_utilization()
