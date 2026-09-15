from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['endpoint'])
JOBS_IN_QUEUE = Histogram('jobs_in_queue', 'Celery Jobs Depth')
ACTIVE_JOBS = Counter('active_jobs', 'Currently running optimization jobs')
