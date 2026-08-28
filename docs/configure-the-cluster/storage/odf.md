# OpenShift Data Foundation

If you are looking at OpenShift Platform Plus (OPP) and are targeting ODF to be your storage provider, here's how to install it. This assumes your worker nodes have an additional data disk, as documented in the prerequisites. 

## Install Local Storage Operator

1. Go to Ecosystem -> Software Catalog -> filter for "Local Storage" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install

## Install OpenShift Data Foundation

1. Go to Ecosystem -> Software Catalog -> filter for "OpenShift Data Foundation" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Wait for the menu item on the left hand side to show Storage has a new Data Foundation item
6. Go to Storage -> Storage cluster -> click on "Configure Data Foundation"
7. Click on "Create Storage Cluster"
8. Select "Create a new StorageClass using local storage devices"

  -> Click Next

9. Select both `Use Ceph RBD as the default StorageClass` and `Set default StorageClass for virtualization`

  -> Click Next

10. Use "odf-local" for the LocalVolumeSet name, click "Disks on selected nodes" and select the nodes with the disks

  -> Click Next

11. On the capacity page, wait for the calculation to happen. Select Balanced or Performance mode.

  -> Click Next

12. Ignore security selections.

  -> Click Next

13. Click Finish
