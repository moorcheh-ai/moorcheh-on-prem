from prometheus_client import Counter, Gauge

# Request counters
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Gauge("http_request_latency_seconds", "Request latency in seconds")

def record_request(method: str, endpoint: str):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
