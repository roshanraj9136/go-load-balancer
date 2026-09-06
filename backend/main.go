package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	_ "github.com/lib/pq"
)

var (
	aesKey = []byte("chitchat-secure-aes-256-key12345")
)

type BackendApp struct {
	name      string
	port      int
	db        *sql.DB
	inFlight  atomic.Int64
	totalReqs atomic.Uint64
	keyLock   sync.RWMutex
	pubKeys   map[string]ed25519.PublicKey
	privKeys  map[string]ed25519.PrivateKey
}

type MessageRequest struct {
	ClientName    string `json:"client-name"`
	ClientNameAlt string `json:"client_name"`
	Msg           string `json:"msg"`
	MessageAlt    string `json:"message"`
	ID            string `json:"id"`
	MessageID     string `json:"message-id"`
}

type MessageItem struct {
	ID         string `json:"id"`
	ClientName string `json:"client-name"`
	Msg        string `json:"msg"`
	Timestamp  string `json:"timestamp"`
	Backend    string `json:"backend,omitempty"`
}

func main() {
	name := flag.String("name", "backend-1", "")
	port := flag.Int("port", 3298, "")
	dbURL := flag.String("db", "postgres://chatuser:chatpass@127.0.0.1:5432/chatdb?sslmode=disable", "")
	flag.Parse()

	db, err := sql.Open("postgres", *dbURL)
	if err != nil {
		log.Fatalf("db open: %v", err)
	}
	defer db.Close()

	db.SetMaxOpenConns(100)
	db.SetMaxIdleConns(50)
	db.SetConnMaxLifetime(10 * time.Minute)

	if err := db.Ping(); err != nil {
		log.Fatalf("db ping: %v", err)
	}

	app := &BackendApp{
		name:     *name,
		port:     *port,
		db:       db,
		pubKeys:  make(map[string]ed25519.PublicKey),
		privKeys: make(map[string]ed25519.PrivateKey),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", app.handleHealth)
	mux.HandleFunc("/message", app.handleMessage)
	mux.HandleFunc("/feed", app.handleFeed)
	mux.HandleFunc("/metrics", app.handleMetrics)

	addr := fmt.Sprintf(":%d", *port)
	log.Printf("[%s] Listening on %s", *name, addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("listen: %v", err)
	}
}

func (a *BackendApp) getOrCreateKey(clientName string) (ed25519.PublicKey, ed25519.PrivateKey) {
	a.keyLock.RLock()
	pub, pubOk := a.pubKeys[clientName]
	priv, privOk := a.privKeys[clientName]
	a.keyLock.RUnlock()

	if pubOk && privOk {
		return pub, priv
	}

	a.keyLock.Lock()
	defer a.keyLock.Unlock()

	if pub, pubOk = a.pubKeys[clientName]; pubOk {
		return pub, a.privKeys[clientName]
	}

	seed := sha256.Sum256([]byte("salt:" + clientName))
	reader := strings.NewReader(string(seed[:]))
	pub, priv, err := ed25519.GenerateKey(reader)
	if err != nil {
		pub, priv, _ = ed25519.GenerateKey(rand.Reader)
	}

	a.pubKeys[clientName] = pub
	a.privKeys[clientName] = priv
	return pub, priv
}

func (a *BackendApp) encrypt(plaintext string) (string, string, error) {
	block, err := aes.NewCipher(aesKey)
	if err != nil {
		return "", "", err
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", "", err
	}

	nonce := make([]byte, aesGCM.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", "", err
	}

	ciphertext := aesGCM.Seal(nil, nonce, []byte(plaintext), nil)
	return base64.StdEncoding.EncodeToString(ciphertext), base64.StdEncoding.EncodeToString(nonce), nil
}

func (a *BackendApp) decrypt(ciphertextB64, nonceB64 string) (string, error) {
	ciphertext, err := base64.StdEncoding.DecodeString(ciphertextB64)
	if err != nil {
		return "", err
	}

	nonce, err := base64.StdEncoding.DecodeString(nonceB64)
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(aesKey)
	if err != nil {
		return "", err
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	plaintext, err := aesGCM.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", err
	}

	return string(plaintext), nil
}

func (a *BackendApp) sign(priv ed25519.PrivateKey, clientName, cipherB64, nonceB64 string) string {
	payload := []byte(clientName + "|" + cipherB64 + "|" + nonceB64)
	sig := ed25519.Sign(priv, payload)
	return base64.StdEncoding.EncodeToString(sig)
}

func (a *BackendApp) verify(pub ed25519.PublicKey, clientName, cipherB64, nonceB64, sigB64 string) bool {
	sig, err := base64.StdEncoding.DecodeString(sigB64)
	if err != nil {
		return false
	}
	payload := []byte(clientName + "|" + cipherB64 + "|" + nonceB64)
	return ed25519.Verify(pub, payload, sig)
}

func (a *BackendApp) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "healthy",
		"backend":   a.name,
		"in_flight": a.inFlight.Load(),
		"total":     a.totalReqs.Load(),
	})
}

func (a *BackendApp) handleMessage(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	a.inFlight.Add(1)
	defer a.inFlight.Add(-1)
	a.totalReqs.Add(1)

	var req MessageRequest
	bodyBytes, _ := io.ReadAll(r.Body)
	_ = json.Unmarshal(bodyBytes, &req)

	formVals, _ := url.ParseQuery(string(bodyBytes))
	queryVals := r.URL.Query()

	getVal := func(keys ...string) string {
		for _, k := range keys {
			if k == "client-name" && req.ClientName != "" {
				return req.ClientName
			}
			if k == "client_name" && req.ClientNameAlt != "" {
				return req.ClientNameAlt
			}
			if k == "msg" && req.Msg != "" {
				return req.Msg
			}
			if k == "message" && req.MessageAlt != "" {
				return req.MessageAlt
			}
			if k == "id" && req.ID != "" {
				return req.ID
			}
			if k == "message-id" && req.MessageID != "" {
				return req.MessageID
			}
			if v := formVals.Get(k); v != "" {
				return v
			}
			if v := queryVals.Get(k); v != "" {
				return v
			}
		}
		return ""
	}

	clientName := getVal("client-name", "client_name")
	msg := getVal("msg", "message")
	msgID := getVal("message-id", "id")

	if clientName == "" || msg == "" {
		http.Error(w, "client-name and msg are required", http.StatusBadRequest)
		return
	}

	if msgID == "" {
		raw := fmt.Sprintf("%s:%s:%d:%d", clientName, msg, time.Now().UnixNano(), randInt())
		sum := sha256.Sum256([]byte(raw))
		msgID = hex.EncodeToString(sum[:16])
	}

	cipherB64, nonceB64, err := a.encrypt(msg)
	if err != nil {
		http.Error(w, "encryption error", http.StatusInternalServerError)
		return
	}

	_, priv := a.getOrCreateKey(clientName)
	sigB64 := a.sign(priv, clientName, cipherB64, nonceB64)

	res, err := a.db.Exec(
		"INSERT INTO messages (id, client_name, ciphertext, nonce, signature, created_at) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (id) DO NOTHING",
		msgID, clientName, cipherB64, nonceB64, sigB64, time.Now(),
	)
	if err != nil {
		http.Error(w, "database error: "+err.Error(), http.StatusInternalServerError)
		return
	}

	rows, _ := res.RowsAffected()
	status := "success"
	if rows == 0 {
		status = "duplicate_ignored"
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"status":      status,
		"message_id":  msgID,
		"client-name": clientName,
		"backend":     a.name,
	})
}

func (a *BackendApp) handleFeed(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	a.inFlight.Add(1)
	defer a.inFlight.Add(-1)
	a.totalReqs.Add(1)

	rows, err := a.db.Query("SELECT id, client_name, ciphertext, nonce, signature, created_at FROM messages ORDER BY created_at ASC")
	if err != nil {
		http.Error(w, "database error: "+err.Error(), http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var feed []MessageItem
	for rows.Next() {
		var id, clientName, cipherB64, nonceB64, sigB64 string
		var createdAt time.Time
		if err := rows.Scan(&id, &clientName, &cipherB64, &nonceB64, &sigB64, &createdAt); err != nil {
			continue
		}

		pub, _ := a.getOrCreateKey(clientName)
		if !a.verify(pub, clientName, cipherB64, nonceB64, sigB64) {
			continue
		}

		plaintext, err := a.decrypt(cipherB64, nonceB64)
		if err != nil {
			continue
		}

		feed = append(feed, MessageItem{
			ID:         id,
			ClientName: clientName,
			Msg:        plaintext,
			Timestamp:  createdAt.Format(time.RFC3339),
			Backend:    a.name,
		})
	}

	if feed == nil {
		feed = []MessageItem{}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(feed)
}

func (a *BackendApp) handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"backend":   a.name,
		"port":      a.port,
		"in_flight": a.inFlight.Load(),
		"total":     a.totalReqs.Load(),
	})
}

func randInt() int64 {
	var b [8]byte
	_, _ = rand.Read(b[:])
	var val int64
	for i := 0; i < 8; i++ {
		val = (val << 8) | int64(b[i])
	}
	if val < 0 {
		return -val
	}
	return val
}
