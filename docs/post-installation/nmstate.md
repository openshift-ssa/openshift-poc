# Kubernetes NMState Operator

[Kubernetes NMState Operator Official Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/networking_operators/k8s-nmstate-about-the-k8s-nmstate-operator)


The Kubernetes NMState Operator manages node network configuration on the cluster. It is required for configuring advanced networking such as bonds, VLANs, and OVS bridges on bare metal nodes.

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "nmstate" -> click "Kubernetes NMState Operator" tile
2. Click Install
3. Leave all the defaults and click Install
4. After the operator is installed, go to Ecosystem -> Installed Operators -> and click on "Kubernetes NMState Operator"
5. Click on the NMState tab at the top and then click "Create NMState" button
6. Don't change anything. Click "Create" button.
7. The screen will refresh because of the updated console plugin for NMState. 
8. Check the Networking menu item has been updated with a bunch of new options. click on "Node network configuration" to view your cluster network setup. 

## Install the Operator via YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-nmstate
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openshift-nmstate
  namespace: openshift-nmstate
spec:
  targetNamespaces:
    - openshift-nmstate
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: kubernetes-nmstate-operator
  namespace: openshift-nmstate
spec:
  channel: stable
  installPlanApproval: Automatic
  name: kubernetes-nmstate-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

```bash
oc apply -f nmstate-operator.yaml
```

Wait for the operator to install:

```bash
oc wait --for=condition=Available deployment/nmstate-operator -n openshift-nmstate --timeout=120s
```

## Create the NMState Instance

After the operator is running, create the NMState custom resource to deploy the state controller across all nodes:

```yaml
apiVersion: nmstate.io/v1
kind: NMState
metadata:
  name: nmstate
```

```bash
oc apply -f nmstate-instance.yaml
```

## Verify

```bash
oc get nmstate
oc get daemonset -n openshift-nmstate
```

All nodes should have a running NMState handler pod:

```bash
oc get pods -n openshift-nmstate
```