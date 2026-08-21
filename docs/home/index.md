# OpenShift POC

Welcome to the OpenShift Proof of Concept documentation.

This site provides step-by-step instructions for installing, configuring, and validating Red Hat [OpenShift Container Platform](https://docs.redhat.com/en/documentation/openshift_container_platform) in on-premise environments.

### USE THE SEARCH IN THE TOP RIGHT CORNER OF THE PAGE. It's very good!

## How to Use This Guide

Follow the tabs left to right — each represents a phase of the POC:

| Phase | What You Do |
| ----- | ----------- |
| **[Prerequisites](../prerequisites/index.md)** | Gather requirements, provision infrastructure, configure DNS and networking |
| **[Install the Cluster](../installation/index.md)** | Deploy OpenShift using the Assisted or Agent-Based installer |
| **[Configure the Cluster](../post-installation/index.md)** | Install storage, operators, and platform capabilities |
| **[Validate the POC](../workloads/index.md)** | Run workloads and operational tests to demonstrate value |

## Important First Steps

1. Read and understand the [prerequisites](../prerequisites/index.md) associated with installing a POC environment for OpenShift.
2. Communicate your intent to all the major stakeholders in your organization. The infrastructure, networking, security, and application development teams will all be interested in learning and understanding the impacts of OpenShift on the organization's processes. Invite them to join the conversation early.
3. Follow the recommendations in this guide. The documentation here highlights common time-wasting mistakes that happen during the install or initial configuration.

!!! info
    You must have an active Red Hat account for your organization.

## Installation Approaches

- **[Standard Installation](../installation/index.md)** — Single cluster for application workloads and/or virtual machines using [OpenShift Virtualization](https://docs.redhat.com/en/documentation/red_hat_openshift_virtualization)
- **[Fleet Management](../installation/other/fleet-management/index.md)** — Multi-cluster management with [Red Hat Advanced Cluster Management](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest), starting with a SNO hub

[Get Started →](../prerequisites/index.md){ .md-button .md-button--primary }
