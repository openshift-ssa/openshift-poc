# Prerequisites

Before beginning an OpenShift installation, ensure all infrastructure, networking, DNS, and storage requirements are met.

For the installation, the documentation assumes a bare metal environment in an on-premise data center. Your network, security, and storage teams will need to be involved. If you have ticketing processes for making changes to networks, DNS, and other services, get everything planned, submitted, and validated prior to the installation.

## Red Hat Account

- You need a [Red Hat account](https://access.redhat.com/registration) associated with your organization. Do not use personal Red Hat accounts for business purposes.
- Evaluation subscriptions are required for any proof of concept using Red Hat products. DO NOT START installation until the trial subscriptions have been created and allocated to the Red Hat user account of the person associated with doing the install.

## VM Migration from VMware

If the POC includes migrating virtual machines from VMware vSphere to OpenShift Virtualization, you must obtain the VMware Virtual Disk Development Kit (VDDK) from Broadcom **before** beginning migrations. Public VDDK downloads were withdrawn by Broadcom in August 2026. Access is now available through select TAP (Technology Alliance Program) partners only — customer support tickets are no longer a reliable path. Customers should confirm they already have a VDDK archive (or a TAP partner path) before scoping warm or vSAN migrations. Cold migrations of non-vSAN VMs can proceed without VDDK (at slower transfer speeds). See [Migration Toolkit for Virtualization — Obtaining the VDDK](../configure-the-cluster/mtv.md#obtaining-the-vddk) for full instructions.

## POC Checklist

Use the [POC Checklist](poc-checklist.md) as a starting place for your master tracking document throughout the engagement. It covers every phase from discovery through closeout. Please download and make the appropriate changes for your scope. 

## Requirements

Complete each of the following before starting the install:

- [Infrastructure](infrastructure.md) — Compute resources provisioned (bare metal or virtual)
- [Networking](networking.md) — Network topology, VLANs, firewall rules, and outbound access
- [DNS](dns.md) — API, Ingress wildcard are required, node A/PTR records are recommended
- [Storage](storage.md) — Persistent storage backend available and validated
- [Installation Host](installation-host.md) — CLI tools downloaded and environment validated
