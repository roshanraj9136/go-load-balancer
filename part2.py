sections_1_to_6 = """
    <h2>1. Important Submission Links & Verification Directory</h2>
    <p>
        The table below provides direct, clickable hyperlinks for all active endpoints, API routes, status interfaces, and code repositories required for grading and evaluation. Every link is live and fully verified.
    </p>

    <table class="lab-table link-table">
        <thead>
            <tr>
                <th style="width: 25%;">Service / Resource</th>
                <th style="width: 13%;">Type / Method</th>
                <th style="width: 38%;">Direct Clickable URL</th>
                <th style="width: 24%;">Evaluation Purpose</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Load Balancer Base Endpoint</strong></td>
                <td><span class="method-tag tag-get">ENTRY</span></td>
                <td class="url-cell"><a href="http://10.1.75.53:3297" target="_blank">http://10.1.75.53:3297</a></td>
                <td>Primary submission URL for official evaluator load generator</td>
            </tr>
            <tr>
                <td><strong>Dynamic LB Health & Status</strong></td>
                <td><span class="method-tag tag-get">GET</span></td>
                <td class="url-cell"><a href="http://10.1.75.53:3297/lb/status" target="_blank">http://10.1.75.53:3297/lb/status</a></td>
                <td>Returns live backend health, active in-flight counts, & &theta;=20</td>
            </tr>
            <tr>
                <td><strong>Message Submission API</strong></td>
                <td><span class="method-tag tag-post">POST</span></td>
                <td class="url-cell"><a href="http://10.1.75.53:3297/message" target="_blank">http://10.1.75.53:3297/message</a></td>
                <td>Submits message (AES-GCM encryption + Ed25519 signature + DB dedup)</td>
            </tr>
            <tr>
                <td><strong>Feed Retrieval API</strong></td>
                <td><span class="method-tag tag-get">GET</span></td>
                <td class="url-cell"><a href="http://10.1.75.53:3297/feed" target="_blank">http://10.1.75.53:3297/feed</a></td>
                <td>Retrieves all messages in order, decrypted from PostgreSQL</td>
            </tr>
            <tr>
                <td><strong>Fallback Swagger UI (Pond Planner)</strong></td>
                <td><span class="method-tag tag-get">GET</span></td>
                <td class="url-cell"><a href="http://10.1.75.53:3297/docs" target="_blank">http://10.1.75.53:3297/docs</a></td>
                <td>Reverse-proxy fallback proving existing port 8001 services run intact</td>
            </tr>
            <tr>
                <td><strong>Fallback OpenAPI JSON Schema</strong></td>
                <td><span class="method-tag tag-get">GET</span></td>
                <td class="url-cell"><a href="http://10.1.75.53:3297/openapi.json" target="_blank">http://10.1.75.53:3297/openapi.json</a></td>
                <td>OpenAPI 3.1 specification for proxied fallback services</td>
            </tr>
            <tr>
                <td><strong>GitHub: Go Load Balancer & Cluster</strong></td>
                <td><span class="method-tag tag-get">GIT REPO</span></td>
                <td class="url-cell"><a href="https://github.com/roshanraj9136/go-load-balancer" target="_blank">https://github.com/roshanraj9136/go-load-balancer</a></td>
                <td>Source code for Load Balancer, Backend, and Custom Client</td>
            </tr>
            <tr>
                <td><strong>GitHub: Base Secure Chat Backend</strong></td>
                <td><span class="method-tag tag-get">GIT REPO</span></td>
                <td class="url-cell"><a href="https://github.com/roshanraj9136/chitchat" target="_blank">https://github.com/roshanraj9136/chitchat</a></td>
                <td>Base persistent secure group-chat backend (Spring Boot / Java)</td>
            </tr>
            <tr>
                <td><strong>GitHub: Base Chat Frontend</strong></td>
                <td><span class="method-tag tag-get">GIT REPO</span></td>
                <td class="url-cell"><a href="https://github.com/roshanraj9136/chitchat-frontend" target="_blank">https://github.com/roshanraj9136/chitchat-frontend</a></td>
                <td>Base secure chat React user interface repository</td>
            </tr>
            <tr>
                <td><strong>Live Messaging App Web URL</strong></td>
                <td><span class="method-tag tag-get">WEB APP</span></td>
                <td class="url-cell"><a href="http://10.1.75.51:3286/" target="_blank">http://10.1.75.51:3286/</a></td>
                <td>Live deployed web application interface for group messaging</td>
            </tr>
        </tbody>
    </table>

    <h2>2. Executive Summary & Assignment Objectives</h2>
    <p>
        In this assignment, I extended my previous secure group-chat application by deploying its backend across three assigned server systems (<code>Sys2</code>, <code>Sys3</code>, and <code>Sys4</code>) and fronting them with a custom high-performance dynamic Load Balancer hosted on <code>Sys1</code>. Clients only interact with the central Load Balancer URL: <a href="http://10.1.75.53:3297" target="_blank">http://10.1.75.53:3297</a>.
    </p>
    <p>
        The core requirements satisfied in this implementation include:
    </p>
    <ul>
        <li><strong>Deployment & Hosting:</strong> The backend is deployed on all 3 allotted systems. External clients access only the Load Balancer URL/port (<a href="http://10.1.75.53:3297" target="_blank">http://10.1.75.53:3297</a>). A persistent port forwarder bridges container port 3000 to 3297 on <code>Sys1</code>.</li>
        <li><strong>Performance-Based Dynamic Routing:</strong> The load balancer tracks active in-flight request concurrency on every backend. Rather than blind Round-Robin, traffic switches to another healthy backend whenever the active backend exceeds the concurrency threshold (&theta;).</li>
        <li><strong>Fault Tolerance & Health Checks:</strong> The load balancer runs periodic background health checks (<code>/health</code> every 3s) and passive network dial monitoring. When a backend crashes or becomes unresponsive, traffic is immediately rerouted to remaining healthy nodes.</li>
        <li><strong>Threshold Optimization:</strong> An empirical sweep across &theta; &isin; {5, 10, 20, 50, 100} was conducted to identify the optimal threshold (&theta; &approx; 20) that minimizes dropout while maximizing throughput.</li>
        <li><strong>Database Persistence & Strict Idempotent Deduplication:</strong> All backend servers share a centralized PostgreSQL 16 database on <code>Sys2</code>. A strict primary key constraint and <code>ON CONFLICT (id) DO NOTHING</code> ensure that duplicate message IDs from retries or reconnections are safely ignored and never stored twice.</li>
        <li><strong>Required API Routes:</strong> The load balancer exposes the required exact routes: <code>POST /message</code> (accepting <code>client-name</code> and <code>msg</code>) and <code>GET /feed</code> (retrieving all chronological messages).</li>
        <li><strong>Custom Benchmark Load Generator:</strong> I developed an authentic Go benchmark tool supporting a variable number of concurrent users, random/variable message lengths, and variable sleep intervals between messages to evaluate response times, dropout rates, and system utilization across all 4 systems.</li>
        <li><strong>Authentic Security Preservation:</strong> All cryptographic guarantees (AES-256-GCM encryption + Ed25519 digital signatures) from the previous secure chat project were fully maintained and NOT stripped or simplified for artificial leaderboard speed.</li>
    </ul>

    <div class="page-break"></div>

    <h2>3. Assigned Cluster Topology & Network Architecture</h2>
    <p>
        The system is deployed across four dedicated Linux containers hosted at <code>10.1.75.53</code>, interconnected over the internal Docker network <code>172.17.0.0/16</code>:
    </p>

    <table class="lab-table">
        <thead>
            <tr>
                <th>Node</th>
                <th>Hostname</th>
                <th>SSH Port</th>
                <th>Internal IP</th>
                <th>Service Port</th>
                <th>Role & Running Processes</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Sys1</strong></td>
                <td>stu85_sys1</td>
                <td>2297</td>
                <td>172.17.0.98</td>
                <td>3297</td>
                <td>Dynamic Go Load Balancer, Port Forwarder (3000&rarr;3297), Fallback Proxy to Port 8001</td>
            </tr>
            <tr>
                <td><strong>Sys2</strong></td>
                <td>stu85_sys2</td>
                <td>2298</td>
                <td>172.17.0.99</td>
                <td>3298</td>
                <td>Backend 1 (Go) + Centralized PostgreSQL 16 Database Server (Port 5432)</td>
            </tr>
            <tr>
                <td><strong>Sys3</strong></td>
                <td>stu85_sys3</td>
                <td>2299</td>
                <td>172.17.0.100</td>
                <td>3299</td>
                <td>Backend 2 (Go) connected over internal Docker network to PostgreSQL on Sys2</td>
            </tr>
            <tr>
                <td><strong>Sys4</strong></td>
                <td>stu85_sys4</td>
                <td>2300</td>
                <td>172.17.0.101</td>
                <td>3300</td>
                <td>Backend 3 (Go) connected over internal Docker network to PostgreSQL on Sys2</td>
            </tr>
        </tbody>
    </table>

    <div class="callout">
        <strong>Docker Port Mapping & Tmux Process Architecture:</strong><br>
        On <code>Sys1</code>, the host's external port 3297 is mapped by Docker to container port 3000. To ensure external access without port conflict, <code>forwarder.py</code> runs in a persistent <code>tmux</code> session listening on <code>0.0.0.0:3000</code> and forwarding TCP streams to the Go Load Balancer on <code>127.0.0.1:3297</code>. Because container environments terminate background jobs upon SSH exit, all processes run inside persistent <code>tmux</code> sessions:
        <code>lb</code> and <code>forwarder</code> on Sys1, and <code>backend</code> on Sys2, Sys3, and Sys4.
    </div>

    <h2>4. Performance-Based Dynamic Load Balancing Implementation</h2>
    <p>
        Fixed Round-Robin algorithms distribute requests uniformly without regard to server load. In a secure chat application, requests require cryptographic decryption, digital signature validation, and database queries. Under bursty traffic, static round-robin quickly causes queuing delays and packet drops on busy nodes while idle nodes sit underutilized.
    </p>
    <p>
        To solve this, I implemented dynamic performance-based routing:
    </p>
    <ul>
        <li><strong>Atomic Concurrency Tracking:</strong> Each backend struct holds an <code>inFlight</code> atomic counter. When a request is forwarded, the counter is atomically incremented; upon response completion, it is atomically decremented.</li>
        <li><strong>Threshold-Based Spillover (&theta;):</strong> The load balancer routes requests to the currently active backend as long as its in-flight concurrency is below &theta;. When the in-flight requests reach &theta;, the load balancer switches to the healthy backend currently carrying the minimum in-flight load.</li>
        <li><strong>Health Probing & Instant Failover:</strong> A background goroutine polls <code>http://&lt;backend&gt;/health</code> every 3 seconds. If a backend fails or if a network error occurs during request forwarding, the backend is marked down immediately and traffic shifts to surviving backends.</li>
        <li><strong>Non-Disruption Fallback Reverse Proxy:</strong> Any request not targeting chat endpoints (such as <code>/docs</code>, <code>/openapi.json</code>, or existing <code>village_pond_planner</code> API routes) is transparently forwarded to <code>http://127.0.0.1:8001</code>, ensuring zero downtime for previously deployed services.</li>
    </ul>

    <div class="callout">
        <strong>Dynamic Switching Logic (loadbalancer/main.go):</strong>
        <div class="code-box">func (lb *LoadBalancer) getNextBackend() *Backend {
    lb.mu.Lock()
    defer lb.mu.Unlock()
    curr := lb.backends[lb.currIdx]
    if curr.IsAlive() && atomic.LoadInt64(&curr.InFlight) < int64(lb.threshold) {
        return curr
    }
    var best *Backend
    var minLoad int64 = 1<<62 - 1
    bestIdx := -1
    for i := 0; i < len(lb.backends); i++ {
        idx := (lb.currIdx + i + 1) % len(lb.backends)
        b := lb.backends[idx]
        if !b.IsAlive() { continue }
        load := atomic.LoadInt64(&b.InFlight)
        if load < minLoad {
            minLoad = load
            best = b
            bestIdx = idx
        }
    }
    if best != nil && bestIdx != lb.currIdx {
        lb.currIdx = bestIdx
        atomic.AddInt64(&lb.switchCount, 1)
    }
    return best
}</div>
    </div>

    <div class="page-break"></div>

    <h2>5. Cryptographic Security Guarantees (Preserving Previous Application Architecture)</h2>
    <p>
        The lab instructions explicitly forbid removing or simplifying security functionality to gain higher leaderboard rankings. All cryptographic protections from the previous secure group chat project were fully preserved:
    </p>
    <ul>
        <li><strong>AES-256-GCM Authenticated Encryption:</strong> Every message is encrypted using 256-bit AES in Galois/Counter Mode. A fresh, cryptographically random 12-byte nonce is generated via <code>crypto/rand</code> for every submission. GCM authentication tags guarantee that message ciphertext cannot be tampered with in transit.</li>
        <li><strong>Ed25519 Asymmetric Digital Signatures:</strong> Every client identity has a corresponding Ed25519 public/private keypair. The sender signs the plaintext before transmission, and backend servers verify the digital signature using <code>ed25519.Verify()</code> before accepting the message into the database.</li>
    </ul>

    <h2>6. Shared Database Persistence & Strict Idempotent Deduplication</h2>
    <p>
        All three backend nodes connect to a single shared PostgreSQL 16 database running on <code>Sys2</code> (<code>172.17.0.99:5432</code>). This ensures all backends view the exact same unified chat history:
    </p>
    <div class="code-box">postgres://chatuser:chatpass@172.17.0.99:5432/chatdb?sslmode=disable</div>

    <p>
        <strong>Strict Idempotency & Deduplication:</strong> In distributed systems, client retries and transient network blips can cause the same message to be delivered multiple times. To guarantee zero duplicate records without table locking, the schema uses:
    </p>
    <div class="code-box">CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(64) PRIMARY KEY,
    client_name VARCHAR(255) NOT NULL,
    ciphertext TEXT NOT NULL,
    nonce TEXT NOT NULL,
    signature TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);</div>

    <p>
        During insertion, backends execute:
    </p>
    <div class="code-box">INSERT INTO messages (id, client_name, ciphertext, nonce, signature)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (id) DO NOTHING;</div>

    <p>
        If the message ID already exists, the database ignores the insert and returns 0 affected rows. The backend detects this and returns <code>{"status": "duplicate_ignored", "message_id": msgID}</code>, ensuring that no message is ever duplicated in storage.
    </p>
"""
