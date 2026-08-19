#!/usr/bin/env python3
"""Generate the POC Checklist as a Word document.

Run during CI to keep the .docx in sync with the markdown checklist.
Output: docs/assets/downloads/poc-checklist.docx
"""

import os
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(10)

title = doc.add_heading('OpenShift POC Checklist', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_paragraph(
    'This checklist provides a complete end-to-end baseline for validating OpenShift '
    'in your environment. Not every item will apply to every environment — skip sections '
    'that are out of scope for your specific goals.'
)
doc.add_paragraph()


def add_phase_heading(text):
    doc.add_heading(text, level=1)


def add_section_heading(text):
    doc.add_heading(text, level=2)


def add_checklist_table(items):
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0].cells
    hdr[0].text = '#'
    hdr[1].text = 'Item'
    hdr[2].text = 'Status'
    hdr[3].text = 'Notes'

    for cell in hdr:
        cell.paragraphs[0].runs[0].bold = True

    for i, item in enumerate(items, 1):
        row = table.add_row().cells
        row[0].text = str(i)
        row[1].text = item
        row[2].text = '☐'
        row[3].text = ''

    for row in table.rows:
        row.cells[0].width = Cm(1)
        row.cells[1].width = Cm(12)
        row.cells[2].width = Cm(1.5)
        row.cells[3].width = Cm(4)

    doc.add_paragraph()


def add_validation_table(rows_data):
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0].cells
    hdr[0].text = 'Area'
    hdr[1].text = 'How We Measure Success'
    hdr[2].text = 'Status'
    hdr[3].text = 'Notes'

    for cell in hdr:
        cell.paragraphs[0].runs[0].bold = True

    for area, criteria in rows_data:
        row = table.add_row().cells
        row[0].text = area
        row[1].text = criteria
        row[2].text = ''
        row[3].text = ''

    doc.add_paragraph()


def add_results_table(rows_data):
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0].cells
    hdr[0].text = 'Category'
    hdr[1].text = 'What Was Tested'
    hdr[2].text = 'Expected Outcome'
    hdr[3].text = 'Actual Outcome'
    hdr[4].text = 'Result'

    for cell in hdr:
        cell.paragraphs[0].runs[0].bold = True

    for row_data in rows_data:
        row = table.add_row().cells
        for i, val in enumerate(row_data):
            row[i].text = val

    doc.add_paragraph()


def add_signoff_table():
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0].cells
    hdr[0].text = 'Role'
    hdr[1].text = 'Name'
    hdr[2].text = 'Signature'
    hdr[3].text = 'Date'

    for cell in hdr:
        cell.paragraphs[0].runs[0].bold = True

    roles = [
        'Customer Technical Lead',
        'Customer Infrastructure Lead',
        'Red Hat / Partner Engineer',
        'Project Sponsor',
    ]
    for role in roles:
        row = table.add_row().cells
        row[0].text = role

    for row in table.rows:
        row.cells[0].width = Cm(5)
        row.cells[1].width = Cm(4)
        row.cells[2].width = Cm(5)
        row.cells[3].width = Cm(3)

    doc.add_paragraph()


# Phase 1
add_phase_heading('Phase 1: Discovery and Scoping')
doc.add_paragraph(
    'Complete this phase before any technical work begins. '
    'Align on goals, boundaries, and what a successful outcome looks like.'
)

add_section_heading('Goals and Drivers')
add_checklist_table([
    'Define the core business problem OpenShift will address',
    'Document specific POC objectives with measurable outcomes',
    'Identify which applications or workloads will be evaluated',
    'Capture high-availability and recovery expectations',
    'Note any security, regulatory, or compliance constraints',
    'Understand target production timeline and anticipated scale',
])

add_section_heading('Boundaries and Assumptions')
add_checklist_table([
    'Agree on what is included in the POC and document it',
    'Explicitly list what is excluded (to prevent scope creep)',
    'Document assumptions and responsibilities (customer vs. Red Hat)',
    'Identify all participating teams (infra, network, security, dev)',
    'Set a timeline with key milestone dates',
])

add_section_heading('Exit Criteria')
doc.add_paragraph('Agree on pass/fail criteria before installation begins:')
add_validation_table([
    ('Installation', 'Cluster deployed, all nodes healthy'),
    ('Networking', 'Application traffic flows end-to-end'),
    ('Storage', 'Persistent volumes provision and bind on demand'),
    ('Security', 'Users authenticate and RBAC enforces permissions'),
    ('Applications', 'Sample and customer workloads run correctly'),
    ('Resilience', 'Cluster recovers from simulated failures'),
    ('Operations', 'Monitoring, logging, and backups function'),
    ('Migration', 'VMs migrated to OpenShift (if applicable)'),
])

# Phase 2
add_phase_heading('Phase 2: Prerequisites')
doc.add_paragraph('Complete these before scheduling the installation.')
add_checklist_table([
    'Red Hat account created and subscriptions allocated',
    'Compute nodes provisioned and meet minimum specs',
    'Management access to nodes confirmed (BMC, vCenter, cloud API)',
    'Firmware/BIOS settings validated (UEFI, virtualization extensions)',
    'Network subnets allocated for cluster traffic',
    'Firewall rules opened (API, ingress, registry access)',
    'NTP accessible from all nodes',
    'Load balancer configured (if required)',
    'api.<cluster>.<domain> DNS record resolves correctly',
    '*.apps.<cluster>.<domain> wildcard DNS resolves correctly',
    'Reverse DNS entries (PTR) configured',
    'Persistent storage backend provisioned and accessible',
    'Storage connectivity verified from node networks',
    'oc CLI installed on installation host',
    'Pull secret downloaded from Red Hat console',
    'SSH key pair generated',
])

# Phase 3
add_phase_heading('Phase 3: Installation')
add_checklist_table([
    'Installation method selected',
    'Cluster installation completed successfully',
    'All nodes showing Ready status',
    'All ClusterOperators Available=True, Degraded=False',
    'Cluster version matches target release',
    'Web console accessible',
    'kubeadmin credentials stored securely',
])

# Phase 4
add_phase_heading('Phase 4: Post-Installation (Required)')
doc.add_paragraph('These must be completed before deploying workloads.')
add_checklist_table([
    'Advanced networking operator installed (if using bonds/VLANs)',
    'Storage driver installed and StorageClasses created',
    'Default StorageClass set',
    'RWO PVC created and bound successfully',
    'RWX PVC created and bound successfully (if applicable)',
    'Internal image registry configured with persistent storage',
])

# Phase 5
add_phase_heading('Phase 5: Post-Installation (Optional)')
doc.add_paragraph('Install based on your POC goals. Each subsection is independent.')

add_section_heading('Networking')
add_checklist_table([
    'Additional network configuration applied (bridges, secondary NICs)',
    'Pod-to-pod communication verified across nodes',
    'Ingress/Route exposes an application externally',
    'DNS resolution works from within pods (internal and external)',
])

add_section_heading('Virtualization')
add_checklist_table([
    'OpenShift Virtualization operator installed',
    'HyperConverged CR created',
    'Live migration network configured (if applicable)',
    'Node health check and remediation operators installed',
    'Health check CRs created (workers and control plane)',
    'Descheduler operator installed and configured',
])

add_section_heading('Migration')
add_checklist_table([
    'Migration toolkit operator installed',
    'Source virtualization provider added',
    'Network and storage mappings configured',
])

add_section_heading('Backup and Restore')
add_checklist_table([
    'Backup operator installed',
    'Backup storage location configured',
    'DataProtectionApplication CR created',
])

add_section_heading('Observability')
add_checklist_table([
    'Cluster logging configured',
    'Network observability enabled',
    'Multi-cluster observability configured (if multi-cluster)',
])

add_section_heading('Developer Experience')
add_checklist_table([
    'Service mesh configured (if applicable)',
    'GitOps operator installed',
    'Web terminal enabled',
    'External secrets integration configured (if applicable)',
])

add_section_heading('Security and Access')
add_checklist_table([
    'Identity provider configured (LDAP, OIDC, etc.)',
    'RBAC groups mapped correctly (members get expected roles)',
    'kubeadmin secret removed after IdP verification (if desired)',
    'Non-production banner applied to the console',
])

# Phase 6
add_phase_heading('Phase 6: VM Migration')
doc.add_paragraph(
    'Validate that virtual machines can be migrated from an existing '
    'virtualization platform to OpenShift Virtualization.'
)
add_checklist_table([
    'Source virtualization environment accessible from OpenShift',
    'Migration provider connection healthy',
    'Target storage class selected',
    'Target network mapping configured',
    'VMs selected for migration',
    'Cold migration executed — VM boots on OpenShift',
    'Networking functional (IP, DNS, connectivity)',
    'Storage attached and data intact',
    'Applications inside the VM running correctly',
    'Warm migration tested — cutover with minimal downtime',
    'VM accessible via console and SSH post-migration',
])

# Phase 7
add_phase_heading('Phase 7: Workloads')
doc.add_paragraph('Deploy workloads to validate platform capabilities.')

add_section_heading('Container Workloads')
add_checklist_table([
    'Basic container deployed and accessible via Route',
    'Build from source — image built and app deploys',
    'Stateful application — data persists across pod restarts',
    'Multi-tier application — frontend and backend communicating',
    'Event streaming workload deployed (if applicable)',
    'Service mesh application validated (if mesh installed)',
    'Customer application deployed (if provided)',
])

add_section_heading('Virtual Machine Workloads')
add_checklist_table([
    'VM deployed from template — boots, SSH, storage functional',
    'Live migration tested (move VM between nodes without downtime)',
    'Snapshot and restore tested',
])

# Phase 8
add_phase_heading('Phase 8: Operational Validation')
doc.add_paragraph('Demonstrate Day 2 operations and resilience.')

add_section_heading('Failover and Resilience')
add_checklist_table([
    'Node failure simulated',
    'VM restarted on healthy node within target time',
    'Application recovered without manual intervention',
    'Container pod rescheduled to healthy node after failure',
    'Service remained available during failover',
])

add_section_heading('Backup and Restore')
add_checklist_table([
    'Application or VM backup completed successfully',
    'Restore to same or different namespace validated',
    'Data integrity confirmed after restore',
    'etcd backup taken and stored securely off-cluster',
])

add_section_heading('Scaling')
add_checklist_table([
    'Worker node added — new node joins cluster successfully',
    'Horizontal Pod Autoscaler validated (if applicable)',
])

add_section_heading('Cluster Lifecycle')
add_checklist_table([
    'SSH key rotation validated',
    'Node-level configuration change applied via MachineConfig',
    'Node drain and maintenance — cordon, drain, uncordon',
    'Cluster upgrade tested (minor version or z-stream)',
    'Workloads remained available during upgrade',
])

add_section_heading('Monitoring and Troubleshooting')
add_checklist_table([
    'Monitoring dashboards accessible',
    'Alerts fire correctly (trigger test alert, verify delivery)',
    'Diagnostic bundle collected and reviewed',
    'Log collection validated (node, pod, operator logs)',
    'Common failure modes understood by the customer team',
])

# Phase 9
add_phase_heading('Phase 9: Results and Recommendations')

add_section_heading('Final Validation Summary')
add_results_table([
    ('Installation', 'Cluster deploy', 'All nodes healthy', '', ''),
    ('Networking', 'Traffic flow', 'Routes reachable', '', ''),
    ('Storage', 'Volume lifecycle', 'PVCs provision and bind', '', ''),
    ('Security', 'Login and RBAC', 'Auth and roles enforced', '', ''),
    ('Applications', 'App deployment', 'Workloads run end-to-end', '', ''),
    ('Resilience', 'Node failure', 'Workloads recover', '', ''),
    ('Scaling', 'Add capacity', 'New node joins cluster', '', ''),
    ('Backup', 'Protect and restore', 'Data intact after restore', '', ''),
    ('Monitoring', 'Alert pipeline', 'Alerts delivered', '', ''),
    ('Migration', 'VM migration', 'VMs operational', '', ''),
    ('Upgrade', 'Version bump', 'Upgrade succeeds cleanly', '', ''),
])

add_section_heading('Sizing and Architecture for Production')
add_checklist_table([
    'Compute sizing documented (CPU, memory, disk per node role)',
    'Storage architecture and capacity plan defined',
    'Network topology and segmentation documented',
    'High-availability and DR strategy outlined',
    'Backup retention and RPO/RTO targets set',
    'Security hardening steps identified',
    'Alerting and on-call strategy documented',
    'Operational ownership model agreed (who runs what)',
])

add_section_heading('Subscription and Infrastructure Summary')
add_checklist_table([
    'Hardware bill of materials finalized',
    'Network allocation documented (subnets, IPs, firewall rules)',
    'Red Hat entitlements and subscription counts confirmed',
    'External dependencies cataloged (storage, load balancers, DNS)',
])

# Phase 10
add_phase_heading('Phase 10: Handoff and Closure')

add_section_heading('Operational Readiness of Customer Team')
doc.add_paragraph('The customer team has demonstrated the ability to:')
add_checklist_table([
    'Perform routine cluster administration',
    'Diagnose and resolve common issues',
    'Execute cluster upgrades',
    'Add or remove cluster capacity',
    'Run backup and restore procedures',
    'Deploy new applications to the platform',
])

add_section_heading('Artifacts Delivered')
add_checklist_table([
    'Architecture diagram',
    'Installation and configuration runbook',
    'Day 2 operations guide',
    'Troubleshooting reference',
    'Upgrade playbook',
    'Backup and recovery procedure',
    'Escalation and support contacts',
])

add_section_heading('Findings and Decision')
add_checklist_table([
    'Successful tests documented',
    'Failures documented with root cause and resolution',
    'Platform gaps identified (features not yet available)',
    'Infrastructure gaps identified (hardware, network, storage)',
    'Application gaps identified (app-specific constraints)',
    'POC-only limitations noted (not relevant to production)',
    'Lessons learned recorded for production planning',
    'Final go/no-go recommendation delivered and agreed',
])

add_section_heading('Formal Approval')
add_signoff_table()

# Save
output_dir = os.path.join(os.path.dirname(__file__), '..', 'docs', 'assets', 'downloads')
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'poc-checklist.docx')
doc.save(output_path)
print(f'Generated {output_path}')
