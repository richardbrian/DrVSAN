#!/usr/bin/python
import time
import csv
import re
import logging
from pyVim import connect
import readHcl
import sys, getopt


vcUserName = 'root'
vcPwd = 'test'

VCIP = "X.X.X.X"


testDatacenterName = "xDatacenter"
testClusterName = "vsanCluster"
#testDatastoreName = "localDatastore32"
#testDatastoreName = "vsanDatastore"
testsHostName = "Y.Y.Y.Y"

#fileName = 'hardwareInfo.csv'

#Final csv for tools consumption
targetFile = '/home/master/boraThon/temp.csv'
logging.basicConfig(filename='/home/master/boraThon/vsanHCL.log',format='%(asctime)s %(message)s',level=logging.DEBUG)

# This will redirect the logged message to console.
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console)

csvHeader = [ 'Compatibility',          # Is the hardware compatible for VSAN.
              'DCname',                 # Datacenter Name
              'ClName',                 # Cluster name
              'HostName',               # Hostname

              'DeviceType',             # IO controller, SSD, MD, Server
              'memorySize',             # ESX memory 
              'cpuModel',               # cpu make and model

              'vendorName',             # Vendor name
              'model',                  # model name
              #'deviceName',             # naa.id
              #'device',                 # vmhba1,vmhba2,vmhba3
              'driver',                 # sata_pix

              'diskCanonicalName',   # naa id
              'diskCapacityInBytes', # 10045056060
              'diskBlockSize',       # 512
              #'isLocal',             # true or false
              'serialNumber',        #
              'adapterName',
             ]

# This will update the first line of the csv
def updateCSVHeader(vsanInventoryFile, rowInfo):
   logging.info("Updating the CSV file")
   with open(vsanInventoryFile, 'wb') as csvfile:
      j=csv.writer(csvfile, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
      j.writerow(rowInfo)

# accepts Dictionary and structures the data as per the columns.
def updateFieldsInCSV(vsanInventoryFile, dataDict):
   rowInfo = []
   for eachColumn in csvHeader:
      if not eachColumn in dataDict:
         rowInfo.append('None')
      else:
         rowInfo.append(dataDict[eachColumn])

   with open(vsanInventoryFile, 'a') as csvfile:
      j=csv.writer(csvfile, delimiter=' ',quotechar='|', quoting=csv.QUOTE_MINIMAL)
      j.writerow(rowInfo)

# IO controller information is updated here.
def updateIOControllerInfo(vsanInventoryFile, hostSystem, dataHash):
   adapterList = []
   logging.info("Working on host %s" % hostSystem.name)
   logging.warning("Fetching hardware info from the host %s..." % hostSystem.name)
   hardwareInfo = hostSystem.hardware
   logging.debug("Fetching pci device info from the host  %s..." % hostSystem.name)
   pciDeviceInHost = hardwareInfo.pciDevice

   # Config manager
   configMgr = hostSystem.configManager
   storageSystemMgr = configMgr.storageSystem
   storageDeviceInfoHere = storageSystemMgr.storageDeviceInfo
   localHba=storageDeviceInfoHere.hostBusAdapter

   localDeviceModel = []
   logging.debug("Printing local adapter info...")
   for eachAdapter in localHba:
      #adapterStringMatch=re.findall('BlockHba', eachAdapter.key)
      #driverName = eachAdapter.driver
      #if  adapterStringMatch and driverName != 'usb-storage':
      match = re.search('BlockHba', eachAdapter.key)
      thisIsUSB = re.search('usb', eachAdapter.driver)
      if match and not thisIsUSB:
         logging.debug(eachAdapter.model)
         dataHash['DeviceType'] = 'IO Controller'
         dataHash['model'] = eachAdapter.model
         dataHash['driver'] = eachAdapter.driver
         dataHash['adapterName'] = eachAdapter.device
         adapterList.append(eachAdapter.device)
         for eachPciDevice in pciDeviceInHost:
            if eachPciDevice.deviceName == eachAdapter.model:
               dataHash['vendorName'] = eachPciDevice.vendorName
         updateFieldsInCSV( vsanInventoryFile, dataHash)
   return adapterList

def updateDeviceInfo(vsanInventoryFile, hostSystem, dataHash, adapterNameList):
   logging.info("Executing updateDeviceInfo on %s..." % hostSystem.name)
   logging.warning("Device info from the host %s..." % hostSystem.name)
   #import pdb;pdb.set_trace()

   if not adapterNameList:
      logging.warning("There are not local adapters on the host" % hostSystem.name)
   
   # Config manager
   configMgr = hostSystem.configManager
   storageSystemMgr = configMgr.storageSystem
   storageDeviceInfo = storageSystemMgr.storageDeviceInfo

   # Create a list consisting of objects that are accessed through adapterNameList
   multipathInfo = storageDeviceInfo.multipathInfo
   lun = multipathInfo.lun 

   deviceList = []  
   for eachDevice in lun:
      #if (len(eachDevice.path) > 0) and ('BlockHba' in eachDevice.path[0].adapter):
      if (len(eachDevice.path) > 0):
         for type in ('BlockHba', 'ParallelScsi'):
            if (re.search(type, eachDevice.path[0].adapter, re.IGNORECASE)):
               deviceList.append(eachDevice.lun)

   scsiLuns = storageDeviceInfo.scsiLun
   for eachDevice in scsiLuns:
      if eachDevice.key in deviceList and eachDevice.lunType == 'disk':
         dataHash['diskCanonicalName'] = eachDevice.canonicalName
         dataHash['diskCapacityInBytes']= eachDevice.capacity.block
         dataHash['diskBlockSize'] = eachDevice.capacity.blockSize
         dataHash['model'] = eachDevice.model
         dataHash['vendorName'] = eachDevice.vendor
         dataHash['serialNumber'] = eachDevice.serialNumber
         if eachDevice.ssd:
            dataHash['DeviceType'] = 'SSD'
         else:
            dataHash['DeviceType'] = 'MD'
         updateFieldsInCSV( vsanInventoryFile, dataHash)

def updateServerHardwareInfo(vsanInventoryFile,hostSystem,dataHash):
   logging.info("Executing updateDeviceInfo on %s..." % hostSystem.name)
   hardwareInfo = hostSystem.summary.hardware
   dataHash['DeviceType'] = 'Server'
   dataHash['vendorName'] = hardwareInfo.vendor
   dataHash['model'] = hardwareInfo.model
   dataHash['memorySize'] = hardwareInfo.memorySize
   dataHash['cpuModel']   = hardwareInfo.cpuModel
   updateFieldsInCSV( vsanInventoryFile, dataHash)
       
def runHclValidationTest(targetName,userName,password,hclFile,vsanInventoryFile):
   start_time = time.time()
   
   updateCSVHeader(vsanInventoryFile, csvHeader)
   logging.debug("Making a connection to the target....")
   si = connect.Connect(targetName, 443, userName, password, "vpxd", "SOAP", namespace="vim25/5.0")
   if si:
      logging.debug("Successfully connected to the target.")
      logging.debug("Target is a VC")
   #import pdb;pdb.set_trace()
   logging.info("#######################################################################################")
   logging.info("VSAN HCL validation start")
   logging.debug("#######################################################################################")

   logging.debug("Retrieving service instance....")
   retrieveContent=si.RetrieveContent()
   #import pdb;pdb.set_trace()
   logging.debug("Geting the datacenter information...")
   ListOfAllDataCenters = retrieveContent.rootFolder.childEntity

   if not list:
      logging.debug("Found %s datacenters..." % len(ListOfAllDataCenters))

   dataHash = {}
   dataHash1 = {}
   dataHash2 = {}
   for myDatacenter in ListOfAllDataCenters:
      dataHash['DCname'] = myDatacenter.name
      hostFolder = myDatacenter.hostFolder
      hostList= hostFolder.childEntity
      dataHash['ClName'] = 'None'

      for clusterObj in hostList:
         dataHash['ClName'] = clusterObj.name
         hostArray=clusterObj.host
         for hostSystem in hostArray:
            dataHash['HostName'] = hostSystem.name
            localHbaNames = updateIOControllerInfo(vsanInventoryFile, hostSystem, dataHash)

            dataHash1['DCname'] = myDatacenter.name
            dataHash1['ClName'] = clusterObj.name
            dataHash1['HostName'] = hostSystem.name
            updateServerHardwareInfo(vsanInventoryFile, hostSystem, dataHash1)

            dataHash2['DCname'] = myDatacenter.name
            dataHash2['ClName'] = clusterObj.name
            dataHash2['HostName'] = hostSystem.name
            updateDeviceInfo(vsanInventoryFile, hostSystem, dataHash2, localHbaNames)
   readHcl.checkHCL(hclFile, vsanInventoryFile, targetFile)
   logging.debug("%s seconds " % (time.time() - start_time))

def main(argv):
   targetName = ''
   userName = ''
   password = ''
   inputCsv = 'NewhardwareInfoOld.csv'
   try:
      #import pdb;pdb.set_trace()
      opts, args = getopt.getopt(argv,"hi:u:p:c:",["targetName=","userName=","password=","inputCsv="])
   except getopt.GetoptError:
      print 'vsanTool.py -i <targetName> -u <userName> -p <password> -c <inputCsv>'
      return
   for opt, arg in opts:
      if opt == '-h':
         print 'test.py -i <targetName> -u <userName> -p <password> -c <inputCsv>'
         sys.exit()
      elif opt in ("-i","--targetName"):
         targetName = arg
      elif opt in ("-u","--userName"):
         userName = arg
      elif opt in ("-p","--password"):
         password = arg
      elif opt in ("-c","--inputCsv"):
         inputCsv = arg
   print 'Input file is "',targetName
   print 'Output file is "',userName
   print 'Password is "',password
   print 'inputCsv is "',inputCsv
   
   logging.debug("Executing runHclValidationTest...")
   runHclValidationTest(targetName,userName,password,inputCsv,'/home/master/boraThon/hardwareInventory.csv')
   
if __name__ == "__main__":
   main(sys.argv[1:])
