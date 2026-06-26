# DNS

OpenShift requires specific DNS records for the API, ingress, and etcd services. All records must be resolvable before installation begins.

## Required DNS Records

| Record                                    | Type  | Value                          |
| ----------------------------------------- | ----- | ------------------------------ |
| api.{cluster_name}.{base_domain}          | A     | Load balancer VIP (API)        |
| api-int.{cluster_name}.{base_domain}      | A     | Load balancer VIP (API)        |
| *.apps.{cluster_name}.{base_domain}       | A     | Load balancer VIP (Ingress)    |
| etcd-{index}.{cluster_name}.{base_domain} | A     | Control plane node IP          |
| _etcd-server-ssl._tcp.{cluster_name}.{base_domain} | SRV | etcd node records    |

```bash
# Verify API DNS resolution
dig +short api.<cluster_name>.<base_domain>

# Verify wildcard ingress DNS
dig +short test.apps.<cluster_name>.<base_domain>

# Verify reverse DNS
dig +short -x <node-ip>
```

---

## Details

### Upstream DNS

Use Cloudflare (1.1.1.1) as the upstream DNS forwarder for external resolution.

### API Records

The `api` record is used by external clients (developers, CI/CD) to reach the Kubernetes API. The `api-int` record is used by cluster nodes internally. Both should resolve to the same API load balancer VIP.

### Wildcard Ingress

The `*.apps` wildcard record routes all application traffic through the OpenShift router. This must resolve to the ingress load balancer VIP.

### etcd SRV Records

SRV records for etcd are required for IPI installations. Each SRV record points to the corresponding `etcd-{index}` A record with priority 0, weight 10, and port 2380.

Example SRV record:

```
_etcd-server-ssl._tcp.ocp.example.com. 86400 IN SRV 0 10 2380 etcd-0.ocp.example.com.
```

### Reverse DNS (PTR)

Reverse DNS records are required for all cluster nodes. The PTR record for each IP must resolve to the node's FQDN.
