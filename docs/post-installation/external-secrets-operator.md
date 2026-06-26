# External Secrets Operator

The External Secrets Operator integrates external secret management systems (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault, Google Secret Manager, IBM Cloud Secrets Manager) with OpenShift. It fetches secrets from external providers and provisions them as native Kubernetes `Secret` resources.

[Red Hat Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/security_and_compliance/external-secrets-operator-for-red-hat-openshift)

!!! warning
    Do not run more than one External Secrets Operator in a cluster. If you have the community operator installed, uninstall it first.

## Install the Operator

```bash
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: external-secrets-operator
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openshift-external-secrets-operator
  namespace: external-secrets-operator
spec:
  targetNamespaces: []
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-external-secrets-operator
  namespace: external-secrets-operator
spec:
  channel: stable-v1
  name: openshift-external-secrets-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
EOF
```

Wait for the operator:

```bash
oc get csv -n external-secrets-operator -w
```

## Deploy the Operand

The operator does not deploy the external-secrets pods automatically. Create an `ExternalSecretsConfig` resource:

```bash
cat <<EOF | oc apply -f -
apiVersion: operator.openshift.io/v1alpha1
kind: ExternalSecretsConfig
metadata:
  name: cluster
spec:
  controllerConfig:
    networkPolicies:
      - componentName: ExternalSecretsCoreController
        egress:
          - {}
        name: allow-external-secrets-egress
EOF
```

Verify the operand pods are running:

```bash
oc get pods -n external-secrets
```

## Configure a SecretStore

### Example: HashiCorp Vault

```bash
oc create secret generic vault-token \
  --from-literal=token=<vault-token> \
  -n my-namespace
```

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-store
  namespace: my-namespace
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        tokenSecretRef:
          name: vault-token
          key: token
```

### Example: AWS Secrets Manager

```bash
oc create secret generic aws-credentials \
  --from-literal=access-key=<access-key-id> \
  --from-literal=secret-access-key=<secret-access-key> \
  -n my-namespace
```

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-store
  namespace: my-namespace
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        secretRef:
          accessKeyIDSecretRef:
            name: aws-credentials
            key: access-key
          secretAccessKeySecretRef:
            name: aws-credentials
            key: secret-access-key
```

## Create an ExternalSecret

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-secret
  namespace: my-namespace
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-store
    kind: SecretStore
  target:
    name: my-k8s-secret
    creationPolicy: Owner
  data:
    - secretKey: password
      remoteRef:
        key: path/to/secret
        property: password
```

Verify:

```bash
oc get secret my-k8s-secret -n my-namespace
oc get externalsecret my-secret -n my-namespace
```

The `STATUS` should show `SecretSynced`.
