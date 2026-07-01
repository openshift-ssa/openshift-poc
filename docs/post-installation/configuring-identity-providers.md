# Configuring Identity Providers

[Authentication and Authorization Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/authentication_and_authorization/index)

By default, only the `kubeadmin` user exists on the cluster. To allow users from your organization to log in, configure one or more identity providers in the OAuth custom resource.

## Supported Identity Providers

| Provider     | Type       | Use Case                                           |
| ------------ | ---------- | -------------------------------------------------- |
| LDAP         | `LDAP`     | Active Directory, OpenLDAP, FreeIPA                |
| HTPasswd     | `HTPasswd` | Simple file-based auth (good for POC admin users)  |
| OpenID Connect | `OpenID` | Keycloak, Azure AD, Okta, Google                   |
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

## LDAP Group Sync

OpenShift can sync LDAP groups to OpenShift Groups, enabling role-based access control based on your existing directory structure.

### Create the Group Sync Configuration

1. Create a sync configuration file. This example uses the RFC 2307 schema (common with Active Directory):

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

### Run the Sync

2. Preview what will be synced (dry run):

  ```bash
  oc adm groups sync --sync-config=sync.yaml
  ```

3. Run the sync:

  ```bash
  oc adm groups sync --sync-config=sync.yaml --confirm
  ```

4. Verify the groups were created:

  ```bash
  oc get groups
  ```

### Assign Roles to Groups

5. Grant cluster-admin to an admin group:

  ```bash
  oc adm policy add-cluster-role-to-group cluster-admin {{ admin_group_name }}
  ```

6. Grant view access to a read-only group across the cluster:

  ```bash
  oc adm policy add-cluster-role-to-group view {{ readonly_group_name }}
  ```

7. Grant edit access to a developer group in a specific namespace:

  ```bash
  oc adm policy add-role-to-group edit {{ dev_group_name }} -n {{ namespace }}
  ```

### Automate Group Sync with a CronJob

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
