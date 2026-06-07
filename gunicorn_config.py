"""
Gunicorn configuration for production
"""
import os
import multiprocessing

# ==================== SERVER SOCKET ====================
bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"
backlog = 2048
timeout = 300
keepalive = 5

# ==================== WORKER PROCESSES ====================
workers = int(os.environ.get("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# ==================== LOGGING ====================
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ==================== PROCESS NAMING ====================
proc_name = "experto-agi"

# ==================== SERVER HOOKS ====================
def post_fork(server, worker):
    """Called after a worker has been forked"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called before re-executing the master"""
    server.log.info("Forking new master")

def when_ready(server):
    """Called when the server is ready to accept requests"""
    server.log.info("Server is ready")

def pre_request(worker, req):
    """Called just before a worker processes a request"""
    worker.log.info(f"Request: {req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes a request"""
    pass
