# OpenShift PoC

Welcome to the OpenShift Proof of Concept (POC) documentation.  

This site provides the prerequisites and step-by-step instructions for installing Red Hat [OpenShift Container Platform](https://docs.redhat.com/en/documentation/openshift_container_platform) in on-premise environments.

## Architecture and Process

There is a wide variety of choices on how to install OpenShift. We recommed these two approaches for a POC: 

1. **Standalone Cluster** - if your are only interested in OpenShift as a application platform and/or to run your virtual machines using [OpenShift Virtualization](https://docs.redhat.com/en/documentation/red_hat_openshift_virtualization)
2. **Fleet Management** - if you are interested in OpenShift but also how [Red Hat Advanced Cluster Management for Kubernetes](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes) could be utilized to manage your cluster fleet at scale

For either method, it is important for you to fully complete and verify the prerequisites for installation. This includes gathering machine information, network information, creating DNS entries (including wildcard entries), as well as possibly opening your firewall to connect to Red Hat image repositories and other Red Hat resources.  

!!! info
    You must have an active Red Hat account for your organization. 

### Standalone Cluster

For a standalone cluster installation, we recommend using the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters) available to you in the [Red Hat Hybrid Cloud Console](https://console.redhat.com). 

### Fleet Management 

For fleet management, we recommend starting with a single node OpenShift installation using the using the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters) available to you in the [Red Hat Hybrid Cloud Console](https://console.redhat.com). Once completed, you can then install and configure [Red Hat Advanced Cluster Management for Kubernetes](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest) and use it as your cluster installation hub. 

## Important First Steps

1. Read and understand the [prerequisites](prerequisites/index.md) associated with installing a POC environment for OpenShift. 
2. Communicate your intent to all the major stakeholders in your organization. The infrastructure, networking, security, and application development teams will all be interested in learning and understanding the impacts of OpenShift on the organization's processes. Invite them to join the conversation early. 
3. Follow the recommendations in this guide. The documentation here does a very good job pointing out time-wasting mistakes that happen during the install or initial configuration of the environment. 

[Let's Get Started](prerequisites/index.md)