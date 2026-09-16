"""Actual gateway multipart rejection before any upload/parser/scan state."""
import http.client
import json
import urllib.request


def health():
    with urllib.request.urlopen("http://127.0.0.1:8098/health", timeout=10) as response:
        return json.load(response)


def rejected(headers, expected):
    connection = http.client.HTTPConnection("127.0.0.1", 8098, timeout=10)
    try:
        connection.putrequest("POST", "/v1/scan")
        connection.putheader("Content-Type", "multipart/form-data; boundary=capacity-fixture")
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == expected, response.read().decode()
        response.read()
    finally:
        connection.close()


def main():
    before = health()
    print("running test case 1/3 live gateway exposes bounded capacity and scanner readiness", flush=True)
    assert before["clamd"] is True
    assert 0 < before["max_file_bytes"] <= before["max_pending_bytes"]
    assert before["max_queue"] > 0 and before["max_sessions"] > 0
    print("running test case 2/3 missing/chunked upload lengths reject before multipart parsing", flush=True)
    rejected({}, 411)
    rejected({"Transfer-Encoding": "chunked"}, 411)
    print("running test case 3/3 oversize envelope rejects without retained scan state", flush=True)
    rejected({"Content-Length": str(before["max_file_bytes"] + 1024 * 1024 + 1)}, 413)
    after = health()
    assert all(after[key] == before[key] for key in ("queue", "pending_bytes", "sessions"))
    print("PASS live antivirus request capacity")


if __name__ == "__main__":
    main()
