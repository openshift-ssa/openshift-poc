# DNS

OpenShift requires specific DNS records for the API and ingress services. All records must be resolvable before installation begins.

## Required DNS Records

| A Record                                     | Value                        |
| -------------------------------------------- | ---------------------------- | 
| api.{{ cluster_name }}.{{ base_domain }}     | API VIP or node IP (SNO)     | 
| api-int.{{ cluster_name }}.{{ base_domain }} | API VIP or node IP (SNO)     | 
| *.apps.{{ cluster_name }}.{{ base_domain }}  | Ingress VIP or node IP (SNO) | 

Validate the DNS using dig:

```bash
dig +noall +answer @{{ nameserver_ip }} api.{{ cluster_name }}.{{ base_domain }}
dig +noall +answer @{{ nameserver_ip }} test.apps.{{ cluster_name }}.{{ base_domain }}
```

---

## Details

### API Records

The `api` record is used by external clients (developers, CI/CD) to reach the Kubernetes API. The `api-int` record is used by cluster nodes internally. Both should resolve to the same API VIP.

### Wildcard Ingress

The `*.apps` wildcard record routes all application traffic through the OpenShift router. This must resolve to the ingress VIP.

### Single Node OpenShift (SNO)

For SNO, all three DNS records point to the single node's IP address. No VIPs are needed.

### Reverse DNS (PTR Records)

Node A records (for example `cp01.{{ cluster_name }}.{{ base_domain }}`) and reverse DNS (PTR) are **recommended**, not required for installation. Without PTR records, nodes may register with incorrect hostnames during provisioning.

```bash
dig +noall +answer -x {{ node_ip }}
```

Each node IP should resolve back to its FQDN (e.g., `cp01.{{ cluster_name }}.{{ base_domain }}`).

!!! note
    Wildcard DNS records may require special handling in Active Directory DNS. Consult your DNS administrator if using AD-integrated DNS.

### Documentation

- [DNS Requirements](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_on_bare_metal/index#installation-dns-user-infra_installing-bare-metal-network-customizations)
- [Validating DNS resolution](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_on_bare_metal/index#installation-user-provisioned-validating-dns_installing-bare-metal-network-customizations)
