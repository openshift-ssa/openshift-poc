# Day 2 Operations

Configure the cluster for production use after installation completes.

## Operations Summary

1. Configure identity provider (OIDC)
2. Remove kubeadmin user
3. Configure infrastructure nodes
4. Install OpenShift GitOps
5. Configure persistent storage
6. Configure monitoring and alerting
7. Configure cluster certificates

---

## Identity Provider (OIDC)

Configure OpenID Connect authentication. This example is provider-agnostic and works with any OIDC-compliant provider (Keycloak, Azure AD, Okta, etc.).

```bash
oc apply -f - <<EOF
apiVersion: config.openshift.io/v1
kind: OAuth
metadata:
  name: cluster
spec:
  identityProviders:
    - name: oidc-provider
      mappingMethod: claim
      type: OpenID
      openID:
        clientID: <client_id>
        clientSecret:
          name: oidc-client-secret
        issuer: https://<oidc-provider-url>/realms/<realm>
        claims:
          preferredUsername:
            - preferred_username
          name:
            - name
          email:
            - email
          groups:
            - groups
EOF
```

Create the client secret:

```bash
oc create secret generic oidc-client-secret \
  --from-literal=clientSecret=<client_secret> \
  -n openshift-config
```

After verifying OIDC login works, remove kubeadmin:

```bash
oc delete secrets kubeadmin -n kube-system
```

## Infrastructure Nodes

Move infrastructure workloads to dedicated nodes:

```bash
oc label node <infra-node> node-role.kubernetes.io/infrastructure=""
oc adm taint nodes <infra-node> node-role.kubernetes.io/infrastructure:NoSchedule
```

Move the router to infrastructure nodes:

```bash
oc patch ingresscontroller/default -n openshift-ingress-operator --type=merge \
  -p '{"spec":{"nodePlacement":{"nodeSelector":{"matchLabels":{"node-role.kubernetes.io/infrastructure":""}},"tolerations":[{"key":"node-role.kubernetes.io/infrastructure","effect":"NoSchedule"}]}}}'
```

## OpenShift GitOps

Install the OpenShift GitOps operator for cluster and application management:

```bash
oc apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-gitops-operator
  labels:
    openshift.io/cluster-monitoring: "true"
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openshift-gitops-operator
  namespace: openshift-gitops-operator
spec:
  upgradeStrategy: Default
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-gitops-operator
  namespace: openshift-gitops-operator
spec:
  channel: latest
  installPlanApproval: Automatic
  name: openshift-gitops-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

## Cluster Certificates

Replace the default ingress certificate with a trusted certificate:

```bash
oc create secret tls custom-ingress-cert \
  --cert=/path/to/fullchain.pem \
  --key=/path/to/privkey.pem \
  -n openshift-ingress

oc patch ingresscontroller/default -n openshift-ingress-operator --type=merge \
  -p '{"spec":{"defaultCertificate":{"name":"custom-ingress-cert"}}}'
```

## Monitoring

Configure persistent storage for the monitoring stack:

```bash
oc apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    prometheusK8s:
      retention: 15d
      volumeClaimTemplate:
        spec:
          storageClassName: <storage_class>
          resources:
            requests:
              storage: 50Gi
    alertmanagerMain:
      volumeClaimTemplate:
        spec:
          storageClassName: <storage_class>
          resources:
            requests:
              storage: 10Gi
EOF
```
