# Prerequisites Overview

Before beginning an OpenShift installation, ensure all infrastructure, networking, DNS, and storage requirements are met. These prerequisites apply to both the [Standalone Cluster](../standalone/index.md) and [Fleet Management](../fleet-management/index.md) approaches.

For the installation, the documentation assumes a bare metal environment in an on-premise data center. Your network, security, and storage teams will need to be involved. If you have ticketing processes for making changes to networks, DNS, and other services, it will be imperative to get everything planned, submitted, and validated prior to the installation.

## Checklist

- [ ] [Infrastructure](infrastructure.md) - Compute resources provisioned
- [ ] [Networking](networking.md) - Network topology and firewall rules configured
- [ ] [DNS](dns.md) - Required DNS records created
- [ ] [Load Balancer](load-balancer.md) - API and Ingress load balancers configured (multi-node only)
- [ ] [Storage](storage.md) - Persistent storage backend available
- [ ] [Installation Host](installation-host.md) - Tools downloaded and environment validated

## Red Hat Account

- Evaluation subscriptions are required for any proof of concept using Red Hat products
- You need a [Red Hat account](https://www.redhat.com/wapps/ugc/register.html) associated with your organization. Do not use personal Red Hat accounts for business purposes
- The pull secret is available at [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
