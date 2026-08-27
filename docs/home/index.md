# OpenShift Proof of Concept Guide

Welcome to the OpenShift Proof of Concept documentation. This site provides step-by-step instructions for installing, configuring, and validating Red Hat [OpenShift Container Platform](https://docs.redhat.com/en/documentation/openshift_container_platform) in on-premise environments. This documentation is a focused, tactical set of instructions and details needed for potential OpenShift customers to evaluate the platform in their environment. 

## How to Use This Guide

At the top of the page, follow the tabs left to right — each represents a phase of the POC:

| Phase                                                      | What You Do                                                                 |
| ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| **[Prerequisites](../prerequisites/index.md)**             | Gather requirements, provision infrastructure, configure DNS and networking |
| **[Install the Cluster](../installation/index.md)**        | Deploy OpenShift using the Assisted or Agent-Based installer                |
| **[Configure the Cluster](../post-installation/index.md)** | Install storage, operators, and platform capabilities                       |
| **[Validate the POC](../workloads/index.md)**              | Run workloads and operational tests to demonstrate value                    |

## Important First Steps

1. Read and understand the [prerequisites](../prerequisites/index.md) associated with installing a POC environment for OpenShift.
2. Communicate your intent to all the major stakeholders in your organization. The infrastructure, networking, security, and application development teams will all be interested in learning and understanding the impacts of OpenShift on the organization's processes. **Invite them to join the conversation early.**
3. Follow the recommendations in this guide. The documentation here highlights common time-wasting mistakes that happen during the install or initial configuration.