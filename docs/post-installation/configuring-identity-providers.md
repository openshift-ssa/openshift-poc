# Configuring Identity Providers

[Authentication and Authorization Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/authentication_and_authorization/index)

By default, only the `kubeadmin` user exists on the cluster. To allow users from your organization to log in, configure one or more identity providers in the OAuth custom resource.

!!! warning
    Regardless of your other configurations, do not delete the `kubeadmin` user.

## Supported Identity Providers

| Provider     | Type       | Use Case                                           |
| ------------ | ---------- | -------------------------------------------------- |
| LDAP         | `LDAP`     | Active Directory, OpenLDAP, FreeIPA                |
| OpenID Connect | `OpenID` | Keycloak, Azure AD, Okta, Google                   |
| HTPasswd     | `HTPasswd` | Simple file-based auth (good for POC admin users)  |
| GitHub       | `GitHub`   | GitHub or GitHub Enterprise                        |
| GitLab       | `GitLab`   | GitLab                                             |

## Mapping Methods

The `mappingMethod` controls how identities from the provider are mapped to OpenShift users:

| Method   | Behavior                                                                                     |
| -------- | -------------------------------------------------------------------------------------------- |
| `claim`  | Default. Provisions a new user with the identity's preferred username. Fails if already taken |
| `lookup` | Only maps to pre-existing users. Requires manual user provisioning                           |
| `add`    | Maps to existing user if username matches, or creates new. Use with multiple providers       |

## Configure LDAP Identity Provider

### Create the Bind Password Secret

1. Create a secret containing the LDAP bind password:

  ```bash
  oc create secret generic ldap-secret \
    --from-literal=bindPassword={{ ldap_bind_password }} \
    -n openshift-config
  ```

### Create the CA Certificate ConfigMap

2. If your LDAP server uses TLS (it should), create a ConfigMap with the CA certificate:

  ```bash
  oc create configmap ca-config-map \
    --from-file=ca.crt={{ path_to_ca_cert }} \
    -n openshift-config
  ```

### Apply the OAuth Configuration

3. Create or update the OAuth CR:

  ```yaml
  apiVersion: config.openshift.io/v1
  kind: OAuth
  metadata:
    name: cluster
  spec:
    identityProviders:
      - name: ldap
        mappingMethod: claim
        type: LDAP
        ldap:
          attributes:
            id:
              - dn
            email:
              - mail
            name:
              - cn
            preferredUsername:
              - sAMAccountName
          bindDN: "CN=svc-openshift,OU=Service Accounts,DC=example,DC=com"
          bindPassword:
            name: ldap-secret
          ca:
            name: ca-config-map
          insecure: false
          url: "ldaps://ldap.example.com/OU=Users,DC=example,DC=com?sAMAccountName?sub?(memberOf=CN=OpenShift-Users,OU=Groups,DC=example,DC=com)"
  ```

  !!! info "LDAP URL Format"
      The URL follows the format: `ldaps://host/baseDN?attribute?scope?(filter)`

      - **baseDN** — Where to start searching for users
      - **attribute** — The attribute to use as the username (e.g., `sAMAccountName` for AD, `uid` for OpenLDAP)
      - **scope** — `sub` for subtree search
      - **filter** — Optional filter to restrict which users can log in (e.g., membership in a specific group)

  ```bash
  oc apply -f oauth.yaml
  ```

4. Wait for the OAuth pods to redeploy:

  ```bash
  oc get pods -n openshift-authentication -w
  ```

### Verify

5. Test login with an LDAP user:

  ```bash
  oc login -u {{ ldap_username }} -p {{ ldap_password }} \
    --server=https://api.{{ cluster_name }}.{{ base_domain }}:6443
  ```

### LDAP Group Sync

OpenShift can sync LDAP groups to OpenShift Groups, enabling role-based access control based on your existing directory structure.

#### Create the Group Sync Configuration

6. Create a sync configuration file. This example uses the RFC 2307 schema (common with Active Directory):

  ```yaml
  kind: LDAPSyncConfig
  apiVersion: v1
  url: "ldaps://ldap.example.com"
  bindDN: "CN=svc-openshift,OU=Service Accounts,DC=example,DC=com"
  bindPassword:
    file: "/etc/secrets/bindPassword"
  ca: "/etc/config/ca.crt"
  insecure: false
  rfc2307:
    groupsQuery:
      baseDN: "OU=Groups,DC=example,DC=com"
      scope: sub
      filter: "(objectClass=group)"
      derefAliases: never
    groupUIDAttribute: dn
    groupNameAttributes:
      - cn
    groupMembershipAttributes:
      - member
    usersQuery:
      baseDN: "OU=Users,DC=example,DC=com"
      scope: sub
      derefAliases: never
    userUIDAttribute: dn
    userNameAttributes:
      - sAMAccountName
    tolerateMemberNotFoundErrors: true
    tolerateMemberOutOfScopeErrors: true
  ```

#### Run the Sync

7. Preview what will be synced (dry run):

  ```bash
  oc adm groups sync --sync-config=sync.yaml
  ```

8. Run the sync:

  ```bash
  oc adm groups sync --sync-config=sync.yaml --confirm
  ```

9. Verify the groups were created:

  ```bash
  oc get groups
  ```

#### Assign Roles to Groups

10. Grant cluster-admin to an admin group:

  ```bash
  oc adm policy add-cluster-role-to-group cluster-admin {{ admin_group_name }}
  ```

11. Grant view access to a read-only group across the cluster:

  ```bash
  oc adm policy add-cluster-role-to-group view {{ readonly_group_name }}
  ```

12. Grant edit access to a developer group in a specific namespace:

  ```bash
  oc adm policy add-role-to-group edit {{ dev_group_name }} -n {{ namespace }}
  ```

#### Automate Group Sync with a CronJob

To keep groups in sync automatically, create a CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: ldap-group-sync
  namespace: openshift-authentication
spec:
  schedule: "*/30 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: ldap-group-syncer
          restartPolicy: Never
          containers:
            - name: sync
              image: registry.redhat.io/openshift4/ose-cli:latest
              command:
                - /bin/bash
                - -c
                - oc adm groups sync --sync-config=/etc/config/sync.yaml --confirm
              volumeMounts:
                - name: sync-config
                  mountPath: /etc/config
                - name: ldap-secret
                  mountPath: /etc/secrets
          volumes:
            - name: sync-config
              configMap:
                name: ldap-group-sync-config
            - name: ldap-secret
              secret:
                secretName: ldap-secret
```

Create the required ServiceAccount and ClusterRoleBinding:

```bash
oc create serviceaccount ldap-group-syncer -n openshift-authentication

oc adm policy add-cluster-role-to-user cluster-admin \
  system:serviceaccount:openshift-authentication:ldap-group-syncer
```

## Configure OpenID Connect Identity Provider

OpenID Connect (OIDC) integrates with providers like Keycloak, Microsoft Entra ID (Azure AD), Okta, and Google. The provider must support OpenID Connect Discovery.

### Create the Client Secret

1. Register an OAuth client in your OIDC provider with the following callback URL:

  ```
  https://oauth-openshift.apps.{{ cluster_name }}.{{ base_domain }}/oauth2callback/{{ provider_name }}
  ```

  Where `{{ provider_name }}` matches the `name` field in the identity provider configuration below.

2. Create a secret containing the client secret:

  ```bash
  oc create secret generic oidc-client-secret \
    --from-literal=clientSecret={{ client_secret }} \
    -n openshift-config
  ```

### Create the CA Certificate ConfigMap (if needed)

3. If your OIDC provider uses a private CA or self-signed certificate:

  ```bash
  oc create configmap oidc-ca-config-map \
    --from-file=ca.crt={{ path_to_ca_cert }} \
    -n openshift-config
  ```

### Apply the OAuth Configuration

4. Create or update the OAuth CR:

  ```yaml
  apiVersion: config.openshift.io/v1
  kind: OAuth
  metadata:
    name: cluster
  spec:
    identityProviders:
      - name: {{ provider_name }}
        mappingMethod: claim
        type: OpenID
        openID:
          clientID: {{ client_id }}
          clientSecret:
            name: oidc-client-secret
          ca:
            name: oidc-ca-config-map
          issuer: https://{{ oidc_issuer_url }}
          claims:
            preferredUsername:
              - preferred_username
              - email
            name:
              - name
            email:
              - email
            groups:
              - groups
  ```

  !!! info "Claims Mapping"
      | Field                | Purpose                                          | Common Values                    |
      | -------------------- | ------------------------------------------------ | -------------------------------- |
      | `preferredUsername`  | Username in OpenShift                            | `preferred_username`, `email`, `upn` |
      | `name`              | Display name                                     | `name`, `given_name`             |
      | `email`             | Email address                                    | `email`                          |
      | `groups`            | Group memberships (maps to OpenShift Groups)     | `groups`, `roles`                |

      The `groups` claim allows the OIDC provider to pass group memberships directly in the token. OpenShift will automatically create Groups and assign users to them based on this claim.

  ```bash
  oc apply -f oauth.yaml
  ```

5. Wait for the OAuth pods to redeploy:

  ```bash
  oc get pods -n openshift-authentication -w
  ```

### Verify

6. Open the OpenShift console — you should see the new login option on the login page
7. Test login with an OIDC user:

  ```bash
  oc login --server=https://api.{{ cluster_name }}.{{ base_domain }}:6443
  ```

  Select the OIDC provider when prompted.

### Example: Microsoft Entra ID (Azure AD)

```yaml
apiVersion: config.openshift.io/v1
kind: OAuth
metadata:
  name: cluster
spec:
  identityProviders:
    - name: entra-id
      mappingMethod: claim
      type: OpenID
      openID:
        clientID: {{ azure_app_client_id }}
        clientSecret:
          name: oidc-client-secret
        issuer: https://login.microsoftonline.com/{{ tenant_id }}/v2.0
        claims:
          preferredUsername:
            - upn
            - email
          name:
            - name
          email:
            - email
          groups:
            - groups
```

!!! tip "Azure AD Group Claims"
    In Microsoft Entra ID, you must configure the app registration to include group claims in the token. Go to App Registration -> Token configuration -> Add groups claim -> Select "Security groups". For large organizations, consider filtering to specific groups to avoid token size limits.

### Example: Keycloak

```yaml
apiVersion: config.openshift.io/v1
kind: OAuth
metadata:
  name: cluster
spec:
  identityProviders:
    - name: keycloak
      mappingMethod: claim
      type: OpenID
      openID:
        clientID: openshift
        clientSecret:
          name: oidc-client-secret
        ca:
          name: oidc-ca-config-map
        issuer: https://keycloak.example.com/realms/{{ realm_name }}
        claims:
          preferredUsername:
            - preferred_username
          name:
            - name
          email:
            - email
          groups:
            - groups
```

!!! tip "Keycloak Group Mapper"
    In Keycloak, add a "Group Membership" mapper to your client scope with the token claim name set to `groups` and "Full group path" disabled. This passes group names directly in the ID token.

## Configure HTPasswd Identity Provider

HTPasswd is a simple file-based identity provider useful for POC environments, break-glass admin accounts, or situations where external identity systems are not yet available.

### Create the HTPasswd File

1. Install the `htpasswd` utility (if not already available):

  ```bash
  sudo dnf install -y httpd-tools
  ```

2. Create a new htpasswd file with the first user:

  ```bash
  htpasswd -c -B -b /tmp/htpasswd admin {{ admin_password }}
  ```

3. Add additional users:

  ```bash
  htpasswd -B -b /tmp/htpasswd developer {{ developer_password }}
  htpasswd -B -b /tmp/htpasswd viewer {{ viewer_password }}
  ```

  !!! info
      The `-B` flag uses bcrypt hashing which is the recommended algorithm. The `-b` flag takes the password from the command line (omit it for interactive prompts).

### Create the Secret

4. Create a secret from the htpasswd file:

  ```bash
  oc create secret generic htpass-secret \
    --from-file=htpasswd=/tmp/htpasswd \
    -n openshift-config
  ```

### Apply the OAuth Configuration

5. Create or update the OAuth CR:

  ```yaml
  apiVersion: config.openshift.io/v1
  kind: OAuth
  metadata:
    name: cluster
  spec:
    identityProviders:
      - name: htpasswd
        mappingMethod: claim
        type: HTPasswd
        htpasswd:
          fileData:
            name: htpass-secret
  ```

  ```bash
  oc apply -f oauth.yaml
  ```

6. Wait for the OAuth pods to redeploy:

  ```bash
  oc get pods -n openshift-authentication -w
  ```

### Verify

7. Test login:

  ```bash
  oc login -u admin -p {{ admin_password }} \
    --server=https://api.{{ cluster_name }}.{{ base_domain }}:6443
  ```

### Update Users

To add, remove, or change passwords for htpasswd users:

1. Extract the current htpasswd file:

  ```bash
  oc get secret htpass-secret -n openshift-config -o jsonpath='{.data.htpasswd}' | base64 -d > /tmp/htpasswd
  ```

2. Make changes:

  ```bash
  htpasswd -B -b /tmp/htpasswd newuser {{ new_password }}
  htpasswd -D /tmp/htpasswd olduser
  ```

3. Replace the secret:

  ```bash
  oc create secret generic htpass-secret \
    --from-file=htpasswd=/tmp/htpasswd \
    --dry-run=client -o yaml -n openshift-config | oc replace -f -
  ```

4. The OAuth pods will automatically redeploy. If a user was removed, also clean up the identity and user objects:

  ```bash
  oc delete user olduser
  oc delete identity htpasswd:olduser
  ```

### Assign Roles

```bash
oc adm policy add-cluster-role-to-user cluster-admin admin
```
