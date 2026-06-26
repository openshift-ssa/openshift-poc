# OpenShift GitOps

[Red Hat OpenShift GitOps Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/latest)

## Install the Operator

```bash
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-gitops-operator
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

Wait for the operator to install:

```bash
oc wait --for=condition=Ready pods --all -n openshift-gitops-operator --timeout=300s
```

The operator automatically creates a default Argo CD instance in the `openshift-gitops` namespace.

## Verify the Installation

```bash
oc get pods -n openshift-gitops
```

## Access the Argo CD Console

```bash
oc get route openshift-gitops-server -n openshift-gitops -o jsonpath='{.spec.host}'
```

You can log in using OpenShift OAuth. To get the default `admin` password:

```bash
oc extract secret/openshift-gitops-cluster -n openshift-gitops --to=-
```

## Grant Argo CD Access to a Namespace

```bash
oc label namespace {{ namespace }} argocd.argoproj.io/managed-by=openshift-gitops
```

## Create an Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: openshift-gitops
spec:
  project: default
  source:
    repoURL: https://github.com/example/my-app.git
    targetRevision: main
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

```bash
oc apply -f application.yaml
```
