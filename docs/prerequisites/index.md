# Prerequisites Overview

Before beginning an OpenShift installation, ensure all infrastructure, networking, DNS, and storage requirements are met. These prerequisites apply to both the [Installation](../installation/index.md) and [Fleet Management](../fleet-management/index.md) approaches.

For the installation, the documentation assumes a bare metal environment in an on-premise data center. Your network, security, and storage teams will need to be involved. If you have ticketing processes for making changes to networks, DNS, and other services, it will be imperative to get everything planned, submitted, and validated prior to the installation.

## Red Hat Account

- You need a [Red Hat account](https://www.redhat.com/wapps/ugc/register.html) associated with your organization. Do not use personal Red Hat accounts for business purposes.
- Evaluation subscriptions are required for any proof of concept using Red Hat products. DO NOT START installation until the trial subscriptions have been created and allocated to the Red Hat user account of the person associated with doing the install.

## Checklist

- [Infrastructure](infrastructure.md) - Compute resources provisioned
- [Networking](networking.md) - Network topology and firewall rules configured
- [DNS](dns.md) - Required DNS records created
- [Storage](storage.md) - Persistent storage backend available
- [Installation Host](installation-host.md) - Tools downloaded and environment validated

## VM Migration from VMware

If the POC includes migrating virtual machines from VMware vSphere to OpenShift Virtualization, you must obtain the VMware Virtual Disk Development Kit (VDDK) from Broadcom **before** beginning migrations. Broadcom has restricted access to the VDDK — a support ticket is required to get the download. This process can take several business days, so initiate it early.

See [Migration Toolkit for Virtualization — Obtaining the VDDK](../post-installation/mtv.md#obtaining-the-vddk) for full instructions.
