# Provision a Bare Metal Cluster

[Red Hat ACM Documentation - Host Inventory](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest/html/clusters/cluster_mce_overview#host-inventory-intro)

This guide covers using ACM to provision a new bare metal OpenShift cluster. ACM handles the entire lifecycle: booting hosts with a discovery ISO via BMC, registering them as agents, and installing the cluster.

## Prerequisites

- ACM is [installed and configured](acm-install.md) on the hub cluster
- Bare metal provisioning is enabled
- BMC credentials available for all target hosts
- DNS records configured for the spoke cluster (API, Ingress, nodes)

## Create InfraEnv

The InfraEnv defines the discovery environment for spoke cluster hosts. ACM uses this to generate a discovery ISO and automatically attach it to hosts via BMC.

1. Create the namespace for the spoke cluster:

  ```bash
  oc create namespace {{ spoke_cluster_name }}
  ```

2. Create the pull secret in the spoke namespace:

  ```bash
  oc create secret generic pullsecret-{{ spoke_cluster_name }} \
    --from-file=.dockerconfigjson=~/pull-secret.txt \
    --type=kubernetes.io/dockerconfigjson \
    -n {{ spoke_cluster_name }}
  ```

3. Create the InfraEnv:

  ```yaml
  apiVersion: agent-install.openshift.io/v1beta1
  kind: InfraEnv
  metadata:
    name: {{ spoke_cluster_name }}
    namespace: {{ spoke_cluster_name }}
  spec:
    cpuArchitecture: x86_64
    ipxeScriptType: DiscoveryImageAlways
    nmStateConfigLabelSelector:
      matchLabels:
        infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    pullSecretRef:
      name: pullsecret-{{ spoke_cluster_name }}
    sshAuthorizedKey: {{ public_key }}
  ```

  ```bash
  oc apply -f infraenv.yaml
  ```

## Add Host Inventory via BMC

Once the InfraEnv is created, register bare metal hosts. ACM will automatically boot each host with the discovery ISO via Redfish virtual media — no manual ISO download or mounting is required.

!!! info "BMC Address Formats"
    The `bmc.address` field varies by hardware vendor:

    | Vendor       | Address Format                                                        |
    | ------------ | --------------------------------------------------------------------- |
    | HPE iLO      | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/1`            |
    | Dell iDRAC   | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/System.Embedded.1` |
    | Cisco CIMC   | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/WZP12345678` |

    The system ID at the end of the path is specific to your hardware. You can discover it by querying the Redfish API:

    ```bash
    curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/ -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
    ```

Repeat the following for each host in the spoke cluster:

1. Create the BMC secret:

  ```bash
  oc create secret generic {{ hostname }}-bmc-secret \
    --from-literal=username={{ bmc_username }} \
    --from-literal=password={{ bmc_password }} \
    -n {{ spoke_cluster_name }}
  ```

2. Create the BareMetalHost:

  ```yaml
  apiVersion: metal3.io/v1alpha1
  kind: BareMetalHost
  metadata:
    name: {{ hostname }}
    namespace: {{ spoke_cluster_name }}
    labels:
      infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
  spec:
    bmc:
      address: {{ bmc_address }}
      credentialsName: "{{ hostname }}-bmc-secret"
      disableCertificateVerification: true
    bootMACAddress: {{ boot_mac_address }}
    online: true
    automatedCleaningMode: disabled
  ```

  ```bash
  oc apply -f {{ hostname }}-bmh.yaml
  ```

3. Watch for hosts to boot and register as agents:

  ```bash
  oc get bmh -n {{ spoke_cluster_name }}
  oc get agents -n {{ spoke_cluster_name }} -w
  ```

  Each host will transition through: `registering` -> `inspecting` -> `available`. Once all hosts show as agents, you can create the cluster.

## Provision the Cluster

Once all hosts are registered as agents, create the cluster resources to trigger installation.

!!! tip "Choosing a ClusterImageSet"
    The `imageSetRef.name` must reference a `ClusterImageSet` that exists on the hub. ACM installs several automatically. List available versions with:

    ```bash
    oc get clusterimageset
    ```

    Pick the version that matches your target OpenShift release (e.g., `img4.17.12-x86-64`).

1. Create the ClusterDeployment and AgentClusterInstall:

  ```yaml
  apiVersion: hive.openshift.io/v1
  kind: ClusterDeployment
  metadata:
    name: {{ spoke_cluster_name }}
    namespace: {{ spoke_cluster_name }}
  spec:
    baseDomain: {{ base_domain }}
    clusterName: {{ spoke_cluster_name }}
    controlPlaneConfig:
      servingCertificates: {}
    installed: false
    clusterInstallRef:
      group: extensions.hive.openshift.io
      kind: AgentClusterInstall
      name: {{ spoke_cluster_name }}
      version: v1beta1
    platform:
      agentBareMetal:
        agentSelector:
          matchLabels:
            infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    pullSecretRef:
      name: pullsecret-{{ spoke_cluster_name }}
  ---
  apiVersion: extensions.hive.openshift.io/v1beta1
  kind: AgentClusterInstall
  metadata:
    name: {{ spoke_cluster_name }}
    namespace: {{ spoke_cluster_name }}
  spec:
    clusterDeploymentRef:
      name: {{ spoke_cluster_name }}
    imageSetRef:
      name: {{ cluster_image_set }}
    networking:
      clusterNetwork:
        - cidr: 10.128.0.0/14
          hostPrefix: 23
      serviceNetwork:
        - 172.30.0.0/16
      machineNetwork:
        - cidr: {{ machine_network_cidr }}
    provisionRequirements:
      controlPlaneAgents: 3
      workerAgents: 3
    sshPublicKey: {{ public_key }}
    apiVIP: {{ api_vip }}
    ingressVIP: {{ ingress_vip }}
  ```

  ```bash
  oc apply -f cluster-deployment.yaml
  ```

2. Monitor the installation:

  ```bash
  oc get agentclusterinstall {{ spoke_cluster_name }} -n {{ spoke_cluster_name }} -w
  ```

  The status will progress through `requirements-met` -> `installing` -> `installed`.

3. Once complete, retrieve the kubeconfig and credentials:

  ```bash
  oc get secret {{ spoke_cluster_name }}-admin-kubeconfig -n {{ spoke_cluster_name }} \
    -o jsonpath='{.data.kubeconfig}' | base64 -d > {{ spoke_cluster_name }}-kubeconfig

  oc get secret {{ spoke_cluster_name }}-admin-password -n {{ spoke_cluster_name }} \
    -o jsonpath='{.data.password}' | base64 -d
  ```

4. Verify the spoke cluster:

  ```bash
  oc --kubeconfig={{ spoke_cluster_name }}-kubeconfig get nodes
  oc --kubeconfig={{ spoke_cluster_name }}-kubeconfig get clusterversion
  ```
