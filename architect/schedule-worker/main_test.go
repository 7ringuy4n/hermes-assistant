package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestExplicitHermesScheduleDoesNotUseZalo(t *testing.T) {
	calls := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		var body map[string]any
		if json.NewDecoder(r.Body).Decode(&body) != nil || body["input"] != "Sample task" {
			t.Error("missing native asynchronous run input")
		}
		w.WriteHeader(http.StatusAccepted)
		_, _ = w.Write([]byte(`{"run_id":"sample-run"}`))
	}))
	defer server.Close()
	oldHermes, oldZalo := hermesURL, zaloInject
	hermesURL, zaloInject = server.URL, "http://127.0.0.1:1/unavailable-zalo"
	defer func() { hermesURL, zaloInject = oldHermes, oldZalo }()
	if err := sendBack(scheduleRow{FireText: "Sample task", Origin: map[string]any{"platform": "hermes", "thread_id": "Sample local session"}}); err != nil {
		t.Fatal(err)
	}
	if calls != 1 {
		t.Fatalf("Hermes handoffs = %d; want one", calls)
	}
	if err := sendBack(scheduleRow{FireText: "Sample task", Origin: map[string]any{"platform": "unknown"}}); err == nil {
		t.Fatal("unsupported platform accepted")
	}
}

func TestHermesAdmissionRequiresDurableRunID(t *testing.T) {
	for _, body := range []string{`{}`, `invalid`} {
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.Header.Get("Idempotency-Key") != "schedule-sample-execution" {
				t.Error("missing execution idempotency key")
			}
			w.WriteHeader(http.StatusAccepted)
			_, _ = w.Write([]byte(body))
		}))
		previous := hermesURL
		hermesURL = server.URL
		err := sendBack(scheduleRow{FireText: "Sample task", Origin: map[string]any{"platform":"hermes", "execution_id":"sample-execution"}})
		hermesURL = previous
		server.Close()
		if err == nil { t.Fatal("unconfirmed admission accepted") }
	}
}
