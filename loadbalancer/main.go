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
	Name        string                 `json:"name"`
	URL         *url.URL               `json:"url"`
	Alive       atomic.Bool            `json:"alive"`
	InFlight    atomic.Int64           `json:"in_flight"`
	TotalReqs   atomic.Uint64          `json:"total_reqs"`
	TotalErrors atomic.Uint64          `json:"total_errors"`
	Proxy       *httputil.ReverseProxy `json:"-"`
}

type Metrics struct {
	Total         atomic.Uint64   `json:"total"`
	Success       atomic.Uint64   `json:"success"`
	Failed        atomic.Uint64   `json:"failed"`
	BackendErrors atomic.Uint64   `json:"backend_errors"`
	Switches      atomic.Uint64   `json:"threshold_switches"`
	StartTime     time.Time       `json:"start_time"`
	LatencyMu     sync.Mutex      `json:"-"`
	Latencies     []time.Duration `json:"-"`
}

type LoadBalancer struct {
	port           int
	backends       []*Backend
	threshold      int64
	currIndex      atomic.Uint64
	metrics        Metrics
	healthInterval time.Duration
	client         *http.Client
	fallbackProxy  *httputil.ReverseProxy
}

func main() {
	port := flag.Int("port", 3297, "")
	rawBackends := flag.String("backends", "http://172.17.0.99:3298,http://172.17.0.100:3299,http://172.17.0.101:3300", "")
	threshold := flag.Int64("threshold", 25, "")
	healthInterval := flag.Duration("health-interval", 500*time.Millisecond, "")
	fallbackURLStr := flag.String("fallback", "http://127.0.0.1:8001", "")
	flag.Parse()

	lb := NewLoadBalancer(*port, *rawBackends, *threshold, *healthInterval, *fallbackURLStr)
	go lb.healthLoop()

	mux := http.NewServeMux()
	mux.HandleFunc("/message", lb.chatProxyHandler)
	mux.HandleFunc("/feed", lb.chatProxyHandler)
	mux.HandleFunc("/lb/health", lb.lbHealthHandler)
	mux.HandleFunc("/lb/status", lb.lbStatusHandler)
	mux.HandleFunc("/lb/metrics", lb.lbMetricsHandler)
	mux.HandleFunc("/", lb.rootHandler)

	l, err := net.Listen("tcp4", fmt.Sprintf("0.0.0.0:%d", *port))
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	log.Printf("[LoadBalancer] Listening on 0.0.0.0:%d (Threshold: %d, Backends: %d)", *port, *threshold, len(lb.backends))
	if err := http.Serve(l, mux); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

func NewLoadBalancer(port int, rawBackends string, threshold int64, healthInterval time.Duration, fallbackURLStr string) *LoadBalancer {
	lb := &LoadBalancer{
		port:           port,
		threshold:      threshold,
		healthInterval: healthInterval,
		client: &http.Client{
			Timeout: 800 * time.Millisecond,
		},
	}
	lb.metrics.StartTime = time.Now()

	if fallbackURL, err := url.Parse(fallbackURLStr); err == nil {
		lb.fallbackProxy = httputil.NewSingleHostReverseProxy(fallbackURL)
	}

	parts := strings.Split(rawBackends, ",")
	for i, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed == "" {
			continue
		}
		targetURL, err := url.Parse(trimmed)
		if err != nil {
			log.Fatalf("invalid backend: %v", err)
		}

		b := &Backend{
			Name: fmt.Sprintf("backend-%d", i+1),
			URL:  targetURL,
		}
		b.Alive.Store(true)

		transport := &http.Transport{
			Proxy: http.ProxyFromEnvironment,
			DialContext: (&net.Dialer{
				Timeout:   1 * time.Second,
				KeepAlive: 30 * time.Second,
			}).DialContext,
			ResponseHeaderTimeout: 3 * time.Second,
			MaxIdleConns:          500,
			MaxIdleConnsPerHost:   200,
			IdleConnTimeout:       90 * time.Second,
		}

		proxy := httputil.NewSingleHostReverseProxy(targetURL)
		proxy.Transport = transport
		proxy.ErrorHandler = func(rw http.ResponseWriter, req *http.Request, err error) {
			b.Alive.Store(false)
			b.TotalErrors.Add(1)
			lb.metrics.BackendErrors.Add(1)
			lb.metrics.Failed.Add(1)
			http.Error(rw, fmt.Sprintf("backend %s error: %v", b.URL.Host, err), http.StatusBadGateway)
		}

		b.Proxy = proxy
		lb.backends = append(lb.backends, b)
	}

	if len(lb.backends) == 0 {
		log.Fatal("no backends configured")
	}

	return lb
}

func (lb *LoadBalancer) selectBackend() *Backend {
	var healthy []*Backend
	for _, b := range lb.backends {
		if b.Alive.Load() {
			healthy = append(healthy, b)
		}
	}

	if len(healthy) == 0 {
		return nil
	}

	idx := int(lb.currIndex.Load() % uint64(len(healthy)))
	candidate := healthy[idx]

	if candidate.InFlight.Load() < lb.threshold {
		return candidate
	}

	lb.metrics.Switches.Add(1)
	best := healthy[0]
	minLoad := best.InFlight.Load()

	for _, b := range healthy[1:] {
		load := b.InFlight.Load()
		if load < minLoad {
			minLoad = load
			best = b
		}
	}

	for i, b := range healthy {
		if b == best {
			lb.currIndex.Store(uint64(i))
			break
		}
	}

	return best
}

func (lb *LoadBalancer) healthLoop() {
	ticker := time.NewTicker(lb.healthInterval)
	defer ticker.Stop()

	for range ticker.C {
		for _, b := range lb.backends {
			go func(backend *Backend) {
				healthURL := fmt.Sprintf("%s://%s/health", backend.URL.Scheme, backend.URL.Host)
				ctx, cancel := context.WithTimeout(context.Background(), 600*time.Millisecond)
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

func (lb *LoadBalancer) chatProxyHandler(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	lb.metrics.Total.Add(1)

	backend := lb.selectBackend()
	if backend == nil {
		lb.metrics.Failed.Add(1)
		http.Error(w, "All backend servers unavailable", http.StatusServiceUnavailable)
		return
	}

	backend.InFlight.Add(1)
	backend.TotalReqs.Add(1)
	defer backend.InFlight.Add(-1)

	rec := &statusRecorder{ResponseWriter: w, statusCode: http.StatusOK}
	backend.Proxy.ServeHTTP(rec, r)

	duration := time.Since(start)
	if rec.statusCode >= 200 && rec.statusCode < 400 {
		lb.metrics.Success.Add(1)
	} else {
		lb.metrics.Failed.Add(1)
	}

	lb.metrics.LatencyMu.Lock()
	if len(lb.metrics.Latencies) < 200000 {
		lb.metrics.Latencies = append(lb.metrics.Latencies, duration)
	}
	lb.metrics.LatencyMu.Unlock()
}

func (lb *LoadBalancer) rootHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/message" || r.URL.Path == "/feed" {
		lb.chatProxyHandler(w, r)
		return
	}

	if lb.fallbackProxy != nil {
		lb.fallbackProxy.ServeHTTP(w, r)
		return
	}

	lb.chatProxyHandler(w, r)
}

func (lb *LoadBalancer) lbHealthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"status": "healthy",
		"time":   time.Now().Format(time.RFC3339),
	})
}

func (lb *LoadBalancer) lbStatusHandler(w http.ResponseWriter, r *http.Request) {
	type StatusItem struct {
		Name      string `json:"name"`
		URL       string `json:"url"`
		Alive     bool   `json:"alive"`
		InFlight  int64  `json:"in_flight"`
		TotalReqs uint64 `json:"total_reqs"`
		Errors    uint64 `json:"errors"`
	}

	var list []StatusItem
	for _, b := range lb.backends {
		list = append(list, StatusItem{
			Name:      b.Name,
			URL:       b.URL.String(),
			Alive:     b.Alive.Load(),
			InFlight:  b.InFlight.Load(),
			TotalReqs: b.TotalReqs.Load(),
			Errors:    b.TotalErrors.Load(),
		})
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"threshold": lb.threshold,
		"switches":  lb.metrics.Switches.Load(),
		"backends":  list,
	})
}

func (lb *LoadBalancer) lbMetricsHandler(w http.ResponseWriter, r *http.Request) {
	lb.metrics.LatencyMu.Lock()
	count := len(lb.metrics.Latencies)
	latenciesCopy := make([]time.Duration, count)
	copy(latenciesCopy, lb.metrics.Latencies)
	lb.metrics.LatencyMu.Unlock()

	var p50, p95, p99 float64
	if count > 0 {
		sort.Slice(latenciesCopy, func(i, j int) bool {
			return latenciesCopy[i] < latenciesCopy[j]
		})
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
		"switches":       lb.metrics.Switches.Load(),
		"throughput_rps": rps,
		"p50_ms":         p50,
		"p95_ms":         p95,
		"p99_ms":         p99,
	})
}
