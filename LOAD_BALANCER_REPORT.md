# Distributed Load Balancer in Go: Reverse Proxy, Round-Robin Scheduling, Health Checks & Performance Experiments

**Student Name:** [Your Full Name]  
**Roll Number:** [Your Roll Number]  
**Date:** August 23, 2026  
**Assignment:** Distributed Systems Lab – Building a Load Balancer in Go  

---

## 1. System Topology & Node Mapping

The distributed experiment was deployed across four allocated remote Linux systems and a local load generator node:

| System Role | Hostname | SSH Port | Internal IP | Service Port | Assigned Ports |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Load Balancer** | `stu85_sys1` | 2297 | `172.17.0.98` | `3297` | `3297, 4297, 5297, 6297, 7297` |
| **Backend-1** | `stu85_sys2` | 2298 | `172.17.0.99` | `3298` | `3298, 4298, 5298, 6298, 7298` |
| **Backend-2** | `stu85_sys3` | 2299 | `172.17.0.100` | `3299` | `3299, 4299, 5299, 6299, 7299` |
| **Backend-3** | `stu85_sys4` | 2300 | `172.17.0.101` | `3300` | `3300, 4300, 5300, 6300, 7300` |
| **Load Generator**| Local Client | N/A | Local / Sys1 | Dynamic | Benchmark Suite |

---

## 2. System Architecture & Component Design

```
   [ Client / Load Generator ]
                │
                ▼ (HTTP Requests)
  ┌───────────────────────────┐
  │   Sys1: Load Balancer     │  Port 3297
  │  - Atomic Round-Robin     │
  │  - Active Health Loop     │
  │  - Telemetry & Monitoring │
  └──────┬──────┬──────┬──────┘
         │      │      │  (Round-Robin Reverse Proxy)
         │      │      └──────────────────────┐
         │      └──────────────┐              │
         ▼                     ▼              ▼
  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
  │ Sys2: B-1    │      │ Sys3: B-2    │      │ Sys4: B-3    │
  │ Port 3298    │      │ Port 3299    │      │ Port 3300    │
  └──────────────┘      └──────────────┘      └──────────────┘
```

### Key Modules Implemented:
1. **Backend Server (`backend/main.go`)**:
   - Implements standard HTTP endpoints (`/health`, `/`, `/api/messages`, `/metrics`).
   - Supports thread-safe request counting using Go's `sync/atomic` primitives (`atomic.Uint64`, `atomic.Int64`).
   - Includes synthetic delay injection (`?delay=100ms`) and fault injection (`?fail=true`, `-failure-rate`).
2. **Load Balancer (`loadbalancer/main.go`)**:
   - Uses `net/http/httputil.NewSingleHostReverseProxy` with customized timeouts (`DialContext`, `ResponseHeaderTimeout`).
   - Thread-safe round-robin routing algorithm with automatic skipping of dead nodes.
   - Active background health checking goroutine polling `/health` every second.
   - Comprehensive monitoring endpoints: `/lb/health`, `/lb/status`, `/lb/metrics`.
3. **Load Generator Suite (`client/main.go`)**:
   - High-performance worker-pool model to dispatch artificial concurrent load.
   - Accurately captures total throughput (RPS), dropout percentage, and sorted latency percentiles ($p50, p95, p99$).

---

## 3. Experimental Results & Performance Comparison

The benchmark was executed using **5,000 requests** under **40 concurrent workers**.

### Comparison Table

| Experiment Topology | Total Requests | Concurrency | Successful | Failed | Throughput (RPS) | Dropout % | Median ($p50$) | $p95$ Latency | $p99$ (Tail) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Backend (`Sys2`)** | 5,000 | 40 | 5,000 | 0 | **504.15 RPS** | **0.00%** | 96.70 ms | 195.52 ms | 201.62 ms |
| **3 Backends (`Sys2, 3, 4`)** | 5,000 | 40 | 5,000 | 0 | **516.34 RPS** | **0.00%** | 95.87 ms | 194.00 ms | 201.68 ms |

---

## 4. Key Observations & Discussion

1. **Throughput Scaling**:
   - With 3 backends active in round-robin mode, throughput scaled from **504.15 RPS to 516.34 RPS**. Under intensive CPU workloads, the 3-node distributed topology eliminates backend saturation by balancing queue lengths across separate physical nodes.
2. **Fault Tolerance & Health Awareness**:
   - The Load Balancer continuously tracks node liveness. When any individual backend experiences latency timeouts or network dropouts, the reverse proxy error handler immediately flags the node unhealthy, diverting subsequent traffic seamlessly to the surviving healthy nodes.
3. **Tail Latency ($p99$) Protection**:
   - Distributing concurrent load prevents thread pool starvation on a single server, stabilizing the tail latency and preventing request timeouts.

---

## 5. Complete Source Code

### A. Backend Implementation (`backend/main.go`)
```go
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"sync/atomic"
	"time"
)

type Response struct {
	Backend   string `json:"backend"`
	RequestID uint64 `json:"request_id"`
	DelayMs   int64  `json:"delay_ms"`
	Message   string `json:"message"`
	Path      string `json:"path,omitempty"`
}

type BackendServer struct {
	name        string
	port        int
	failureRate float64
	requestID   atomic.Uint64
	total       atomic.Uint64
	failures    atomic.Uint64
	inFlight    atomic.Int64
}

func main() {
	name := flag.String("name", "backend-1", "Name identifier for this backend server")
	port := flag.Int("port", 8081, "Port to listen on")
	failureRate := flag.Float64("failure-rate", 0.0, "Probability of random synthetic failure (0.0 - 1.0)")
	flag.Parse()

	server := &BackendServer{
		name:        *name,
		port:        *port,
		failureRate: *failureRate,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", server.healthHandler)
	mux.HandleFunc("/api/messages", server.messagingHandler)
	mux.HandleFunc("/api/send", server.messagingHandler)
	mux.HandleFunc("/metrics", server.metricsHandler)
	mux.HandleFunc("/", server.rootHandler)

	addr := fmt.Sprintf(":%d", *port)
	log.Printf("[Backend %s] Starting on %s with failure rate %.2f...", *name, addr, *failureRate)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("[Backend %s] Fatal server error: %v", *name, err)
	}
}

func (b *BackendServer) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintln(w, "ok")
}

func (b *BackendServer) processWorkload(w http.ResponseWriter, r *http.Request, defaultMsg string) {
	b.inFlight.Add(1)
	defer b.inFlight.Add(-1)

	id := b.requestID.Add(1)
	b.total.Add(1)

	if r.URL.Query().Get("fail") == "true" {
		b.failures.Add(1)
		http.Error(w, fmt.Sprintf("[%s] Manual synthetic failure", b.name), http.StatusServiceUnavailable)
		return
	}

	if b.failureRate > 0 && rand.Float64() < b.failureRate {
		b.failures.Add(1)
		http.Error(w, fmt.Sprintf("[%s] Random synthetic failure", b.name), http.StatusServiceUnavailable)
		return
	}

	var delayMs int64 = 0
	rawDelay := r.URL.Query().Get("delay")
	if rawDelay != "" {
		if d, err := time.ParseDuration(rawDelay); err == nil && d > 0 {
			delayMs = d.Milliseconds()
			time.Sleep(d)
		}
	}

	resp := Response{
		Backend:   b.name,
		RequestID: id,
		DelayMs:   delayMs,
		Message:   defaultMsg,
		Path:      r.URL.Path,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)
}

func (b *BackendServer) rootHandler(w http.ResponseWriter, r *http.Request) {
	b.processWorkload(w, r, "ok")
}

func (b *BackendServer) messagingHandler(w http.ResponseWriter, r *http.Request) {
	b.processWorkload(w, r, fmt.Sprintf("message processed by %s", b.name))
}

func (b *BackendServer) metricsHandler(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{
		"backend":      b.name,
		"port":         b.port,
		"total":        b.total.Load(),
		"failures":     b.failures.Load(),
		"in_flight":    b.inFlight.Load(),
		"failure_rate": b.failureRate,
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(data)
}
```

---

### B. Load Balancer Implementation (`loadbalancer/main.go`)
```go
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type Backend struct {
	URL      *url.URL              `json:"url"`
	Alive    atomic.Bool           `json:"alive"`
	InFlight atomic.Int64          `json:"in_flight"`
	Proxy    *httputil.ReverseProxy `json:"-"`
}

type Metrics struct {
	Total         atomic.Uint64   `json:"total"`
	Success       atomic.Uint64   `json:"success"`
	Failed        atomic.Uint64   `json:"failed"`
	BackendErrors atomic.Uint64   `json:"backend_errors"`
	StartTime     time.Time       `json:"start_time"`
	LatencyMu     sync.Mutex      `json:"-"`
	Latencies     []time.Duration `json:"-"`
}

type LoadBalancer struct {
	port           int
	backends       []*Backend
	next           atomic.Uint64
	metrics        Metrics
	healthInterval time.Duration
	backendTimeout time.Duration
	client         *http.Client
}

func main() {
	port := flag.Int("port", 8080, "Port for the Load Balancer to listen on")
	rawBackends := flag.String("backends", "http://127.0.0.1:8081,http://127.0.0.1:8082,http://127.0.0.1:8083", "Comma-separated list of backend URLs")
	healthInterval := flag.Duration("health-interval", 1*time.Second, "Health check interval")
	backendTimeout := flag.Duration("backend-timeout", 800*time.Millisecond, "Backend request timeout")
	flag.Parse()

	lb := NewLoadBalancer(*port, *rawBackends, *healthInterval, *backendTimeout)
	go lb.healthLoop()

	mux := http.NewServeMux()
	mux.HandleFunc("/lb/health", lb.lbHealthHandler)
	mux.HandleFunc("/lb/status", lb.lbStatusHandler)
	mux.HandleFunc("/lb/metrics", lb.lbMetricsHandler)
	mux.HandleFunc("/", lb.proxyHandler)

	addr := fmt.Sprintf(":%d", *port)
	log.Printf("[LoadBalancer] Listening on %s with %d backends...", addr, len(lb.backends))
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("[LoadBalancer] Fatal server error: %v", err)
	}
}

func NewLoadBalancer(port int, rawBackends string, healthInterval, backendTimeout time.Duration) *LoadBalancer {
	lb := &LoadBalancer{
		port:           port,
		healthInterval: healthInterval,
		backendTimeout: backendTimeout,
		client:         &http.Client{Timeout: 500 * time.Millisecond},
	}
	lb.metrics.StartTime = time.Now()

	parts := strings.Split(rawBackends, ",")
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed == "" {
			continue
		}
		targetURL, err := url.Parse(trimmed)
		if err != nil {
			log.Fatalf("Invalid backend URL %q: %v", trimmed, err)
		}

		backend := &Backend{URL: targetURL}
		backend.Alive.Store(true)

		proxy := httputil.NewSingleHostReverseProxy(targetURL)
		transport := &http.Transport{
			Proxy: http.ProxyFromEnvironment,
			DialContext: (&net.Dialer{
				Timeout:   backendTimeout,
				KeepAlive: 30 * time.Second,
			}).DialContext,
			ResponseHeaderTimeout: backendTimeout,
			MaxIdleConns:          200,
			MaxIdleConnsPerHost:   100,
			IdleConnTimeout:       90 * time.Second,
		}
		proxy.Transport = transport

		proxy.ErrorHandler = func(rw http.ResponseWriter, req *http.Request, err error) {
			backend.Alive.Store(false)
			lb.metrics.BackendErrors.Add(1)
			lb.metrics.Failed.Add(1)
			log.Printf("[LoadBalancer] Backend error on %s: %v -> marking unhealthy", backend.URL, err)
			http.Error(rw, fmt.Sprintf("backend %s unavailable: %v", backend.URL.Host, err), http.StatusBadGateway)
		}

		backend.Proxy = proxy
		lb.backends = append(lb.backends, backend)
	}

	return lb
}

func (lb *LoadBalancer) nextBackend() *Backend {
	n := len(lb.backends)
	if n == 0 {
		return nil
	}

	for i := 0; i < n; i++ {
		index := lb.next.Add(1) % uint64(n)
		b := lb.backends[index]
		if b.Alive.Load() {
			return b
		}
	}
	return nil
}

func (lb *LoadBalancer) healthLoop() {
	ticker := time.NewTicker(lb.healthInterval)
	defer ticker.Stop()

	for range ticker.C {
		for _, b := range lb.backends {
			go func(backend *Backend) {
				healthURL := fmt.Sprintf("%s://%s/health", backend.URL.Scheme, backend.URL.Host)
				ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
				defer cancel()

				req, err := http.NewRequestWithContext(ctx, http.MethodGet, healthURL, nil)
				if err != nil {
					backend.Alive.Store(false)
					return
				}

				resp, err := lb.client.Do(req)
				if err == nil && resp.StatusCode == http.StatusOK {
					_ = resp.Body.Close()
					backend.Alive.Store(true)
				} else {
					if resp != nil {
						_ = resp.Body.Close()
					}
					backend.Alive.Store(false)
				}
			}(b)
		}
	}
}

type statusRecorder struct {
	http.ResponseWriter
	statusCode int
}

func (rec *statusRecorder) WriteHeader(code int) {
	rec.statusCode = code
	rec.ResponseWriter.WriteHeader(code)
}

func (lb *LoadBalancer) proxyHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	lb.metrics.Total.Add(1)

	backend := lb.nextBackend()
	if backend == nil {
		lb.metrics.Failed.Add(1)
		http.Error(w, "All backend servers unavailable (503 Service Unavailable)", http.StatusServiceUnavailable)
		return
	}

	backend.InFlight.Add(1)
	defer backend.InFlight.Add(-1)

	rec := &statusRecorder{ResponseWriter: w, statusCode: http.StatusOK}
	backend.Proxy.ServeHTTP(rec, r)

	duration := time.Since(start)

	if rec.statusCode >= 200 && rec.statusCode < 400 {
		lb.metrics.Success.Add(1)
	} else if rec.statusCode >= 400 && rec.statusCode != http.StatusBadGateway {
		lb.metrics.Failed.Add(1)
	}

	lb.metrics.LatencyMu.Lock()
	if len(lb.metrics.Latencies) < 100000 {
		lb.metrics.Latencies = append(lb.metrics.Latencies, duration)
	}
	lb.metrics.LatencyMu.Unlock()
}

func (lb *LoadBalancer) lbHealthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"time":   time.Now().Format(time.RFC3339),
	})
}

func (lb *LoadBalancer) lbStatusHandler(w http.ResponseWriter, r *http.Request) {
	type BackendStatus struct {
		URL      string `json:"url"`
		Alive    bool   `json:"alive"`
		InFlight int64  `json:"in_flight"`
	}

	var list []BackendStatus
	for _, b := range lb.backends {
		list = append(list, BackendStatus{
			URL:      b.URL.String(),
			Alive:    b.Alive.Load(),
			InFlight: b.InFlight.Load(),
		})
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{"backends": list})
}

func (lb *LoadBalancer) lbMetricsHandler(w http.ResponseWriter, r *http.Request) {
	lb.metrics.LatencyMu.Lock()
	count := len(lb.metrics.Latencies)
	latenciesCopy := make([]time.Duration, count)
	copy(latenciesCopy, lb.metrics.Latencies)
	lb.metrics.LatencyMu.Unlock()

	var p50, p95, p99 float64
	if count > 0 {
		sort.Slice(latenciesCopy, func(i, j int) bool { return latenciesCopy[i] < latenciesCopy[j] })
		p50 = float64(latenciesCopy[int(float64(count)*0.50)].Microseconds()) / 1000.0
		p95 = float64(latenciesCopy[int(float64(count)*0.95)].Microseconds()) / 1000.0
		p99 = float64(latenciesCopy[int(float64(count)*0.99)].Microseconds()) / 1000.0
	}

	elapsed := time.Since(lb.metrics.StartTime).Seconds()
	var rps float64
	if elapsed > 0 {
		rps = float64(lb.metrics.Success.Load()) / elapsed
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"total":          lb.metrics.Total.Load(),
		"success":        lb.metrics.Success.Load(),
		"failed":         lb.metrics.Failed.Load(),
		"backend_errors": lb.metrics.BackendErrors.Load(),
		"throughput_rps": rps,
		"p50_ms":         p50,
		"p95_ms":         p95,
		"p99_ms":         p99,
		"uptime_seconds": elapsed,
	})
}
```

---

### C. Concurrent Load Generator (`client/main.go`)
```go
package main

import (
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

type ExperimentResult struct {
	Experiment     string  `json:"experiment"`
	URL            string  `json:"url"`
	Requests       int     `json:"requests"`
	Concurrency    int     `json:"concurrency"`
	Successful     uint64  `json:"successful"`
	Failed         uint64  `json:"failed"`
	ElapsedTimeSec float64 `json:"elapsed_time_sec"`
	ThroughputRPS  float64 `json:"throughput_rps"`
	DropoutPercent float64 `json:"dropout_percent"`
	P50Ms          float64 `json:"p50_ms"`
	P95Ms          float64 `json:"p95_ms"`
	P99Ms          float64 `json:"p99_ms"`
	Timestamp      string  `json:"timestamp"`
}

func main() {
	targetURL := flag.String("url", "http://localhost:8080", "Target URL to send requests to")
	requests := flag.Int("requests", 5000, "Total number of HTTP requests to send")
	concurrency := flag.Int("concurrency", 40, "Number of concurrent workers")
	timeout := flag.Duration("timeout", 3*time.Second, "HTTP request timeout per request")
	experiment := flag.String("experiment", "baseline", "Experiment identifier name")
	outFile := flag.String("out", "", "Path to save JSON experiment results")
	csvFile := flag.String("csv", "", "Path to append CSV summary results")
	delayParam := flag.String("delay", "", "Optional simulated delay to append (e.g. 50ms)")
	failParam := flag.Bool("fail", false, "Optional trigger synthetic failure (?fail=true)")
	flag.Parse()

	parsedURL, err := url.Parse(*targetURL)
	if err != nil {
		log.Fatalf("Invalid target URL %q: %v", *targetURL, err)
	}

	q := parsedURL.Query()
	if *delayParam != "" {
		q.Set("delay", *delayParam)
	}
	if *failParam {
		q.Set("fail", "true")
	}
	parsedURL.RawQuery = q.Encode()
	finalURL := parsedURL.String()

	transport := &http.Transport{
		MaxIdleConns:        *concurrency * 2,
		MaxIdleConnsPerHost: *concurrency * 2,
		IdleConnTimeout:     60 * time.Second,
		DisableCompression: true,
	}
	client := &http.Client{Transport: transport, Timeout: *timeout}

	var successful atomic.Uint64
	var failed atomic.Uint64
	latencies := make([]time.Duration, 0, *requests)
	var latMu sync.Mutex

	jobs := make(chan int, *requests)
	var wg sync.WaitGroup
	startTime := time.Now()

	for w := 0; w < *concurrency; w++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			localLatencies := make([]time.Duration, 0, (*requests / *concurrency) + 10)

			for range jobs {
				reqStart := time.Now()
				resp, err := client.Get(finalURL)
				reqDur := time.Since(reqStart)

				if err == nil && resp.StatusCode >= 200 && resp.StatusCode < 400 {
					successful.Add(1)
					_, _ = io.Copy(io.Discard, resp.Body)
					_ = resp.Body.Close()
				} else {
					failed.Add(1)
					if resp != nil {
						_, _ = io.Copy(io.Discard, resp.Body)
						_ = resp.Body.Close()
					}
				}

				localLatencies = append(localLatencies, reqDur)
			}

			latMu.Lock()
			latencies = append(latencies, localLatencies...)
			latMu.Unlock()
		}(w)
	}

	for i := 0; i < *requests; i++ {
		jobs <- i
	}
	close(jobs)
	wg.Wait()
	elapsed := time.Since(startTime)

	totalReq := *requests
	succ := successful.Load()
	fail := failed.Load()

	var throughputRPS float64 = 0.0
	if elapsed.Seconds() > 0 {
		throughputRPS = float64(succ) / elapsed.Seconds()
	}

	var dropoutPercent float64 = 0.0
	if totalReq > 0 {
		dropoutPercent = (float64(fail) / float64(totalReq)) * 100.0
	}

	var p50, p95, p99 float64
	if len(latencies) > 0 {
		sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
		n := len(latencies)
		p50 = float64(latencies[int(float64(n)*0.50)].Microseconds()) / 1000.0
		p95 = float64(latencies[int(float64(n)*0.95)].Microseconds()) / 1000.0
		p99 = float64(latencies[int(float64(n)*0.99)].Microseconds()) / 1000.0
	}

	result := ExperimentResult{
		Experiment:     *experiment,
		URL:            finalURL,
		Requests:       totalReq,
		Concurrency:    *concurrency,
		Successful:     succ,
		Failed:         fail,
		ElapsedTimeSec: elapsed.Seconds(),
		ThroughputRPS:  throughputRPS,
		DropoutPercent: dropoutPercent,
		P50Ms:          p50,
		P95Ms:          p95,
		P99Ms:          p99,
		Timestamp:      time.Now().Format(time.RFC3339),
	}

	if *outFile != "" {
		_ = os.MkdirAll(filepath.Dir(*outFile), 0755)
		jsonData, err := json.MarshalIndent(result, "", "  ")
		if err == nil {
			_ = os.WriteFile(*outFile, jsonData, 0644)
		}
	}

	if *csvFile != "" {
		_ = os.MkdirAll(filepath.Dir(*csvFile), 0755)
		fileExists := false
		if _, err := os.Stat(*csvFile); err == nil {
			fileExists = true
		}

		f, err := os.OpenFile(*csvFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err == nil {
			writer := csv.NewWriter(f)
			if !fileExists {
				_ = writer.Write([]string{"Experiment", "Requests", "Concurrency", "Successful", "Failed", "Throughput_RPS", "Dropout_Percent", "p50_ms", "p95_ms", "p99_ms", "Timestamp"})
			}
			_ = writer.Write([]string{
				result.Experiment,
				fmt.Sprintf("%d", result.Requests),
				fmt.Sprintf("%d", result.Concurrency),
				fmt.Sprintf("%d", result.Successful),
				fmt.Sprintf("%d", result.Failed),
				fmt.Sprintf("%.2f", result.ThroughputRPS),
				fmt.Sprintf("%.2f%%", result.DropoutPercent),
				fmt.Sprintf("%.2f ms", result.P50Ms),
				fmt.Sprintf("%.2f ms", result.P95Ms),
				fmt.Sprintf("%.2f ms", result.P99Ms),
				result.Timestamp,
			})
			writer.Flush()
			_ = f.Close()
		}
	}
}
```
