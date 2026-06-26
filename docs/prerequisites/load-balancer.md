# Load Balancer

OpenShift requires load balancers for the Kubernetes API and application ingress traffic.

## Load Balancer Configuration

| Service     | Frontend Port | Backend Port | Backend Targets          | Health Check          |
| ----------- | ------------- | ------------ | ------------------------ | --------------------- |
| API         | 6443          | 6443         | Control plane nodes      | HTTPS /readyz         |
| API (int)   | 22623         | 22623        | Control plane nodes      | HTTPS /healthz        |
| Ingress HTTP  | 80          | 80           | Worker/Infra nodes       | TCP                   |
| Ingress HTTPS | 443         | 443          | Worker/Infra nodes       | TCP                   |

```bash
# Test API load balancer
curl -k https://api.<cluster_name>.<base_domain>:6443/readyz

# Test Ingress load balancer
curl -I http://test.apps.<cluster_name>.<base_domain>
```

---

## Details

### API Load Balancer

The API load balancer distributes traffic to all control plane nodes on ports 6443 (Kubernetes API) and 22623 (Machine Config Server). During bootstrap, the bootstrap node must also be included as a backend target and removed after bootstrap completes.

### Ingress Load Balancer

The ingress load balancer distributes HTTP (80) and HTTPS (443) traffic to nodes running the OpenShift router pods. By default these run on worker nodes, but in production they should be moved to dedicated infrastructure nodes.

### HAProxy Example

```bash
sudo dnf install -y haproxy
```

Example `/etc/haproxy/haproxy.cfg`:

```
frontend api
    bind *:6443
    default_backend api_backend

backend api_backend
    balance roundrobin
    option httpchk GET /readyz HTTP/1.0
    option log-health-checks
    server control-plane-0 10.0.0.10:6443 check check-ssl verify none
    server control-plane-1 10.0.0.11:6443 check check-ssl verify none
    server control-plane-2 10.0.0.12:6443 check check-ssl verify none

frontend ingress_https
    bind *:443
    default_backend ingress_https_backend

backend ingress_https_backend
    balance roundrobin
    server worker-0 10.0.0.20:443 check
    server worker-1 10.0.0.21:443 check
    server worker-2 10.0.0.22:443 check

frontend ingress_http
    bind *:80
    default_backend ingress_http_backend

backend ingress_http_backend
    balance roundrobin
    server worker-0 10.0.0.20:80 check
    server worker-1 10.0.0.21:80 check
    server worker-2 10.0.0.22:80 check

frontend machine_config
    bind *:22623
    default_backend machine_config_backend

backend machine_config_backend
    balance roundrobin
    option httpchk GET /healthz HTTP/1.0
    server control-plane-0 10.0.0.10:22623 check check-ssl verify none
    server control-plane-1 10.0.0.11:22623 check check-ssl verify none
    server control-plane-2 10.0.0.12:22623 check check-ssl verify none
```

```bash
sudo systemctl enable --now haproxy
sudo firewall-cmd --permanent --add-port={6443,22623,80,443}/tcp
sudo firewall-cmd --reload
```
