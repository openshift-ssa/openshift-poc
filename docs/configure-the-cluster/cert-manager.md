# cert-manager

[cert-manager Operator for Red Hat OpenShift](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/security_and_compliance/cert-manager-operator-for-red-hat-openshift)

The cert-manager Operator for Red Hat OpenShift issues and renews TLS certificates in the cluster. This page installs that operator, creates a certificate authority, and uses it to replace two certificates:

- The **default ingress certificate**, which the router presents for the web console and for routes that use the default certificate
- The **external API server certificate**, which clients receive when they connect to `api.{{ cluster_name }}.{{ base_domain }}`

| Hostname                                       | What serves it                                    |
| ---------------------------------------------- | ------------------------------------------------- |
| `api.{{ cluster_name }}.{{ base_domain }}`     | cert-manager named certificate on the API server  |
| `api-int.{{ cluster_name }}.{{ base_domain }}` | Cluster CA. Leave this hostname unchanged         |
| `*.apps.{{ cluster_name }}.{{ base_domain }}`  | cert-manager default ingress certificate          |

The hostnames come from the records in [DNS](../prerequisites/dns.md).

!!! warning "Schedule this outside a demo"
    Two steps interrupt the cluster. Adding the CA to the cluster trust bundle restarts kubelet and CRI-O on each node, so nodes report `NotReady` until those services are back. On a single-node cluster that takes the API and the console offline until the node is `Ready` again. Adding the API named certificate for the first time rolls out new API server pods.

!!! warning "Leave api-int on the cluster CA"
    A named certificate for `api-int.{{ cluster_name }}.{{ base_domain }}` leaves the cluster degraded. Nodes use that hostname to reach the API. This procedure adds a certificate only for `api.{{ cluster_name }}.{{ base_domain }}`.

This procedure uses a CA issuer so it works with private POC DNS. A public ACME server such as Let's Encrypt needs the HTTP-01 challenge to reach the cluster on port 80 from the internet.

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "cert-manager Operator for Red Hat OpenShift" -> click that tile
2. Click Install
3. Set the channel to `stable-v1`
4. Set the installation mode to **All namespaces on the cluster**
5. Set the installed namespace to `cert-manager-operator`. The console creates the namespace if it is missing
6. Set update approval to Automatic and click Install
7. Wait until Ecosystem -> Installed Operators shows **Succeeded** for cert-manager Operator for Red Hat OpenShift

!!! info
    The install form can ask for cloud credential fields such as an AWS role ARN. Those fields come from the operator's catalog metadata. On a bare-metal POC, enter any placeholder. The operator ignores the values the console collects there.

??? note "Install the Operator via YAML (click to expand)"

    ```yaml
    apiVersion: v1
    kind: Namespace
    metadata:
      name: cert-manager-operator
    ---
    apiVersion: operators.coreos.com/v1
    kind: OperatorGroup
    metadata:
      name: openshift-cert-manager-operator
      namespace: cert-manager-operator
    spec: {}
    ---
    apiVersion: operators.coreos.com/v1alpha1
    kind: Subscription
    metadata:
      name: openshift-cert-manager-operator
      namespace: cert-manager-operator
    spec:
      channel: stable-v1
      name: openshift-cert-manager-operator
      source: redhat-operators
      sourceNamespace: openshift-marketplace
      installPlanApproval: Automatic
    ```

    An empty `spec` on the `OperatorGroup` installs the operator in all namespaces. That is the supported mode for cert-manager Operator 1.15 and later.

    ```bash
    oc apply -f cert-manager-operator.yaml
    ```

    Wait for the operator:

    ```bash
    oc get csv -n cert-manager-operator -w
    ```

    Stop the watch when the cert-manager CSV `PHASE` is `Succeeded`.

## Verify the operand

The operator creates the `cert-manager` namespace and starts the controller, webhook, and CA injector. Wait until all three deployments are available:

```bash
oc rollout status deployment/cert-manager -n cert-manager
oc rollout status deployment/cert-manager-webhook -n cert-manager
oc rollout status deployment/cert-manager-cainjector -n cert-manager
oc get pods -n cert-manager
```

Each pod should be `1/1 Running`. Create issuers only after these pods are up.

## Create an issuer

Create one issuer. The rest of this page uses a `ClusterIssuer` named `cluster-ca`. The CA secret for a `ClusterIssuer` must live in the `cert-manager` namespace, which is where the controller runs.

Run the remaining commands from a working directory:

```bash
mkdir -p ~/cert-manager
cd ~/cert-manager
```

=== "Self-signed root CA"

    Use this when you want cert-manager to create the root CA for the POC. Browsers and `oc` trust the issued certificates after `ca.crt` is imported.

    ```yaml
    apiVersion: cert-manager.io/v1
    kind: ClusterIssuer
    metadata:
      name: selfsigned
    spec:
      selfSigned: {}
    ---
    apiVersion: cert-manager.io/v1
    kind: Certificate
    metadata:
      name: cluster-ca
      namespace: cert-manager
    spec:
      isCA: true
      commonName: cluster-ca
      secretName: cluster-ca
      duration: 87600h # 10 years
      renewBefore: 720h
      rotationPolicy: Never
      privateKey:
        algorithm: RSA
        size: 2048
        encoding: PKCS1
      issuerRef:
        name: selfsigned
        kind: ClusterIssuer
    ---
    apiVersion: cert-manager.io/v1
    kind: ClusterIssuer
    metadata:
      name: cluster-ca
    spec:
      ca:
        secretName: cluster-ca
    ```

    ```bash
    oc apply -f cluster-ca.yaml
    oc wait --for=condition=Ready certificate/cluster-ca -n cert-manager --timeout=180s
    oc wait --for=condition=Ready clusterissuer/cluster-ca --timeout=180s
    oc extract secret/cluster-ca -n cert-manager --keys=ca.crt --to=- > ca.crt
    ```

    `rotationPolicy: Never` keeps the same root key if this CA certificate is ever renewed. `ca.crt` is the public root. Leave the private key in the secret.

=== "Corporate or intermediate CA"

    Use this when you have an intermediate certificate, its unencrypted private key, and the root that signed the intermediate. Clients that already trust that root trust the issued certificates. Put the intermediate key in the cluster. Keep the corporate root key offline.

    Skip this command when `intermediate.key` is already an unencrypted PEM. If the key is encrypted, decrypt it before the checks below:

    ```bash
    openssl rsa -in intermediate-encrypted.key -out intermediate.key
    ```

    Build a chain file with the intermediate first and the root second. Confirm the key matches the intermediate. The two MD5 lines must be identical:

    ```bash
    cat intermediate.crt root.crt > intermediate-chain.crt
    openssl x509 -in intermediate.crt -noout -modulus | openssl md5
    openssl rsa -in intermediate.key -noout -modulus | openssl md5
    ```

    Store the chain and key in the `cert-manager` namespace, then point a `ClusterIssuer` at that secret:

    ```bash
    oc create secret tls cluster-ca \
      --cert=intermediate-chain.crt \
      --key=intermediate.key \
      -n cert-manager \
      --dry-run=client -o yaml | oc apply -f -
    ```

    ```yaml
    apiVersion: cert-manager.io/v1
    kind: ClusterIssuer
    metadata:
      name: cluster-ca
    spec:
      ca:
        secretName: cluster-ca
    ```

    ```bash
    oc apply -f cluster-ca-issuer.yaml
    oc wait --for=condition=Ready clusterissuer/cluster-ca --timeout=180s
    cp root.crt ca.crt
    ```

    `ca.crt` in this directory must be the root certificate only. The secret's `tls.crt` keeps the intermediate followed by the root, so certificates cert-manager issues contain the full chain.

## Trust the CA in the cluster

In-cluster clients use this bundle to verify the new ingress certificate and the external API certificate. The config map key must be `ca-bundle.crt`, and the file should contain the root CA.

See whether the cluster already has a trusted CA:

```bash
oc get proxy cluster -o jsonpath='{.spec.trustedCA.name}{"\n"}'
```

If that prints a blank line, create a config map and set it on the proxy. If a name was printed, skip these two commands and use the note below.

```bash
oc create configmap cluster-ca \
  --from-file=ca-bundle.crt=ca.crt \
  -n openshift-config \
  --dry-run=client -o yaml | oc apply -f -

oc patch proxy/cluster \
  --type=merge \
  --patch='{"spec":{"trustedCA":{"name":"cluster-ca"}}}'
```

??? note "If a config map name was printed (click to expand)"

    Append `ca.crt` to that existing bundle. The proxy already references the config map, so replacing its data is enough:

    ```bash
    CM=$(oc get proxy cluster -o jsonpath='{.spec.trustedCA.name}')
    oc extract "configmap/${CM}" -n openshift-config --keys=ca-bundle.crt --to=- > ca-bundle.crt
    echo >> ca-bundle.crt
    cat ca.crt >> ca-bundle.crt
    oc create configmap "$CM" \
      --from-file=ca-bundle.crt=ca-bundle.crt \
      -n openshift-config \
      --dry-run=client -o yaml | oc replace -f -
    ```

The machine config pools then push the updated bundle. Nodes do not reboot when `trustedCA` is the only proxy change. Watch the pools and press Ctrl-C when every pool shows `UPDATED=True`, `UPDATING=False`, and `DEGRADED=False`:

```bash
oc get mcp -w
```

```bash
oc get nodes
```

Continue when every node is `Ready`.

## Replace the default ingress certificate

Create the certificate in the `openshift-ingress` namespace. cert-manager writes the secret. The secret name is what the Ingress Controller references.

[Replacing the default ingress certificate](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/security_and_compliance/configuring-certificates#replacing-default-ingress_replacing-default-ingress)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ingress-cert
  namespace: openshift-ingress
spec:
  secretName: ingress-cert
  commonName: apps.{{ cluster_name }}.{{ base_domain }}
  dnsNames:
    - apps.{{ cluster_name }}.{{ base_domain }}
    - "*.apps.{{ cluster_name }}.{{ base_domain }}"
  duration: 8760h # 1 year
  renewBefore: 360h # 15 days
  privateKey:
    algorithm: RSA
    size: 2048
    encoding: PKCS1
  issuerRef:
    name: cluster-ca
    kind: ClusterIssuer
```

```bash
oc apply -f ingress-cert.yaml
oc wait --for=condition=Ready certificate/ingress-cert -n openshift-ingress --timeout=180s
```

Confirm the secret exists, then point the default Ingress Controller at it. Changing `defaultCertificate` rolls the router pods. Later renewals update this same secret in place, and the router reloads the files without another rollout.

```bash
oc get secret ingress-cert -n openshift-ingress
oc patch ingresscontroller.operator.openshift.io default \
  --type=merge \
  -p '{"spec":{"defaultCertificate":{"name":"ingress-cert"}}}' \
  -n openshift-ingress-operator
oc rollout status deployment/router-default -n openshift-ingress
```

`commonName` must be 64 characters or fewer. If the certificate stays `False` and the description says the common name is too long, delete the `commonName` field and apply the certificate again. Clients match the DNS names in `dnsNames`.

## Add the API server certificate

Create this certificate in the `openshift-config` namespace. The API server only reads serving certificates from that namespace.

[Adding API server certificates](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/security_and_compliance/configuring-certificates#customize-certificates-api-add-named_api-server-certificates)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-cert
  namespace: openshift-config
spec:
  secretName: api-cert
  commonName: api.{{ cluster_name }}.{{ base_domain }}
  dnsNames:
    - api.{{ cluster_name }}.{{ base_domain }}
  duration: 8760h # 1 year
  renewBefore: 360h # 15 days
  privateKey:
    algorithm: RSA
    size: 2048
    encoding: PKCS1
  issuerRef:
    name: cluster-ca
    kind: ClusterIssuer
```

```bash
oc apply -f api-cert.yaml
oc wait --for=condition=Ready certificate/api-cert -n openshift-config --timeout=180s
oc get secret api-cert -n openshift-config
```

The installer's kubeconfig trusts the cluster CA only. After the API server starts presenting the new certificate, that kubeconfig fails TLS verification for `api.{{ cluster_name }}.{{ base_domain }}`. During the rollout, some API pods still present the cluster certificate and some present the new one. Add both CAs to the kubeconfig before patching the API server. `awk` writes the decoded cluster CA with a trailing newline so `ca.crt` starts on its own line. Confirm `oc` still works:

```bash
cp "${KUBECONFIG:-$HOME/.kube/config}" "${KUBECONFIG:-$HOME/.kube/config}.bak"
CLUSTER=$(oc config view --minify -o jsonpath='{.contexts[0].context.cluster}')
oc config view --raw --minify \
  -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
  | base64 -d | awk '1' > cluster-ca.crt
cat cluster-ca.crt ca.crt > api-trust-bundle.crt
oc config set-cluster "$CLUSTER" \
  --certificate-authority=api-trust-bundle.crt \
  --embed-certs=true
oc whoami
```

If `oc whoami` fails, put the backup back and stop:

```bash
cp "${KUBECONFIG:-$HOME/.kube/config}.bak" "${KUBECONFIG:-$HOME/.kube/config}"
```

Patch the API server. The `names` entry is the hostname only, without `:6443`. This sets the full `namedCertificates` list. On a fresh POC that list is empty.

```bash
oc patch apiserver cluster --type=merge -p "$(cat <<'EOF'
{
  "spec": {
    "servingCerts": {
      "namedCertificates": [
        {
          "names": ["api.{{ cluster_name }}.{{ base_domain }}"],
          "servingCertificate": {
            "name": "api-cert"
          }
        }
      ]
    }
  }
}
EOF
)"
```

Watch the operator. The first time you add a named certificate, `PROGRESSING` becomes `True` while new API server pods roll out. Press Ctrl-C when `AVAILABLE` is `True` and `PROGRESSING` is `False`. Leave the API server alone until then:

```bash
oc get clusteroperators kube-apiserver -w
```

After the rollout, confirm the admin session still reaches the API. This kubeconfig trusts both the cluster CA and `ca.crt`. Leave that bundle in place so a later rollback still verifies:

```bash
oc whoami
```

A different workstation can log in with the issuing CA:

```bash
oc login \
  --server=https://api.{{ cluster_name }}.{{ base_domain }}:6443 \
  --certificate-authority=ca.crt \
  -u kubeadmin \
  -p {{ password }}
```

## Verify

Both certificates should be `Ready`:

```bash
oc get certificate -n openshift-ingress
oc get certificate -n openshift-config
oc get ingresscontroller default -n openshift-ingress-operator -o jsonpath='{.spec.defaultCertificate.name}{"\n"}'
```

The Ingress Controller name should be `ingress-cert`.

Check the certificate the router and the API server present. `Verify return code: 0 (ok)` means the chain validates against `ca.crt`. The ingress SAN list should include `*.apps.{{ cluster_name }}.{{ base_domain }}`. The API SAN list should include `api.{{ cluster_name }}.{{ base_domain }}`.

```bash
APP_HOST=console-openshift-console.apps.{{ cluster_name }}.{{ base_domain }}
echo | openssl s_client -connect "${APP_HOST}:443" -servername "${APP_HOST}" -CAfile ca.crt 2>&1 \
  | grep -E "subject=|issuer=|Verify return code"
echo | openssl s_client -connect "${APP_HOST}:443" -servername "${APP_HOST}" 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName

API_HOST=api.{{ cluster_name }}.{{ base_domain }}
echo | openssl s_client -connect "${API_HOST}:6443" -servername "${API_HOST}" -CAfile ca.crt 2>&1 \
  | grep -E "subject=|issuer=|Verify return code"
echo | openssl s_client -connect "${API_HOST}:6443" -servername "${API_HOST}" 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName
```

For the self-signed root, import `ca.crt` into the browser or operating system trust store on each workstation that opens the console. A corporate root that those workstations already trust needs no extra import.

## Renewal

cert-manager renews each leaf certificate 15 days before the one-year expiry in these examples. Renewal replaces `tls.crt` and `tls.key` in the existing secret and keeps the secret name.

- The router reloads the ingress secret when the files change. Router pods stay up.
- The API server reloads an existing named certificate when the secret changes. That renewal does not roll out a new API server revision.

Renewing a leaf signed by the same CA leaves the cluster trust bundle and the workstation trust stores as they are. Update those stores when the root CA itself changes.

## Return to the cluster-managed certificates

Remove the Ingress Controller reference. The router rolls back to the certificate signed by the cluster ingress CA:

```bash
oc patch ingresscontroller.operator.openshift.io default \
  -n openshift-ingress-operator \
  --type=json \
  -p '[{"op":"remove","path":"/spec/defaultCertificate"}]'
oc rollout status deployment/router-default -n openshift-ingress
```

Remove the API named certificate. The API server rolls out again and presents the cluster CA certificate for `api.{{ cluster_name }}.{{ base_domain }}`. Press Ctrl-C when `PROGRESSING` returns to `False`. The admin kubeconfig from the steps above still contains the cluster CA, so `oc` keeps working:

```bash
oc patch apiserver cluster --type=json \
  -p '[{"op":"remove","path":"/spec/servingCerts/namedCertificates"}]'
oc get clusteroperators kube-apiserver -w
```

Leave the trusted CA config map in place. An extra trusted root does not change which certificate the router or the API server presents.

## Troubleshooting

- **`clusterissuer/cluster-ca` stays `False`.** The CA secret is missing, is not named `cluster-ca`, or is in a namespace other than `cert-manager`. `oc describe clusterissuer cluster-ca` prints the reason.
- **A leaf certificate stays `False`.** `oc describe certificate <name> -n <namespace>` shows the signing error. A common name longer than 64 characters is rejected. Delete `commonName` and keep `dnsNames`.
- **`openssl` reports `unable to get local issuer certificate`.** The served chain is missing the root or the intermediate. For a corporate CA, recreate the `cluster-ca` secret so `tls.crt` is the intermediate followed by the root, then delete the leaf secret so cert-manager reissues it:

    ```bash
    oc delete secret ingress-cert -n openshift-ingress
    oc delete secret api-cert -n openshift-config
    oc wait --for=condition=Ready certificate/ingress-cert -n openshift-ingress --timeout=180s
    oc wait --for=condition=Ready certificate/api-cert -n openshift-config --timeout=180s
    ```

    Deleting those secrets is safe after the Ingress Controller and the API server already reference those names. cert-manager recreates them, and the router and API server reload the new files.
