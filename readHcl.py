#!/usr/bin/python
import time
import csv
import re
import logging
from pyVim import connect

vcUserName = 'root'
vcPwd = 'vmware'

VCIP='xxxx'

#hclFile = 'vi_vsan_guide-partial.csv'
logging.basicConfig(filename='vsanHCL.log',format='%(asctime)s %(message)s',level=logging.DEBUG)

replateStringDataHash = {
                        'Hewlett-Packard Company': 'HP',
                        'Intel Corporation': 'Intel',
                        'LSI Logic / Symbios Logic' : 'LSI',
                        }
vsphereInventoryFile = 'NewhardwareInfoOld.csv'

# This will redirect the logged message to console.
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console)

def istheDeviceInHcl(lineFromInventory, hclFile):
   # escape reading first line:
   #import pdb;pdb.set_trace()
   #lineFromInventoryListAfterSplitAcrossComma = re.split('  | ,',lineFromInventory)
   #hclStringSplitAfterComma = ''.join([str(item) for item in lineFromInventoryListAfterSplitAcrossComma])
   #hclStringList = hclStringSplitAfterComma.split(' ')
   hclStringList = lineFromInventory.split(' ')
   with open(hclFile, 'rb') as csvfile:
      spamreader = csv.reader(csvfile, delimiter=' ', quoting=csv.QUOTE_MINIMAL)
      spamreader.next()
      for row in spamreader:
         singleStringHclLine = ''.join([str(item) for item in row])
         match = False
         count = 0;
         for hclWord in hclStringList:
            if not re.search(hclWord, singleStringHclLine, re.IGNORECASE):
               break
            else:
               count = count + 1;
         if count == len(hclStringList):
            #print 'found %s in %s' % (hclStringList, singleStringHclLine)
            logging.info("found %s in %s" % (hclStringList, singleStringHclLine))
            return True
   return match

def readHcl(testFile):
   with open(testFile, 'rb') as csvfile:
      spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
      for row in spamreader:
         #print len(row)
         logging.info("%s" % row)
         
def readCsvHeader(hclFile):
   with open(hclFile, 'rb') as csvfile:
      spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
      for row in spamreader:
         return row
         break

def checkHCL(hclFile, sourceFile, targetFile):
   sourceFileHandle = open(sourceFile, 'rb')
   targetFileHandle = open(targetFile, 'wb')
   readerPointer = csv.reader(sourceFileHandle, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
   #writerPointer = csv.writer(targetFileHandle, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
   writerPointer = csv.writer(targetFileHandle, delimiter=',',quoting=csv.QUOTE_MINIMAL)
   for row in readerPointer:
      #import pdb;pdb.set_trace()
      #spamreader = csv.reader(readerPointer, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
      if row[0] == 'Compatibility':
         writerPointer.writerow(row)
         #readerPointer.next()
      else:
      #with open(vsphereInventoryFile, 'rb') as checkConponentCompliance:
      #   spamreader = csv.reader(checkConponentCompliance, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
         #spamreader = csv.reader(readerPointer, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
         #spamreader.next()
         lineFromInventory = '%s %s' % (row[7],row[8])
         replace = row[7]
         if row[7] in replateStringDataHash.keys():
            replace = replateStringDataHash[row[7]]
         lineFromInventory = '%s %s' % (replace,row[8])
         if istheDeviceInHcl(lineFromInventory, hclFile):
            row[0] = 'Y'
         else:
            #row[0] = 'N'
            if re.search('ST91000640NS', row[8], re.IGNORECASE):
               row[0] = 'Y'
            else:
               row[0] = 'N'
         writerPointer.writerow(row)
   sourceFileHandle.close()
   targetFileHandle.close()

'''
def generateIntermediateCsv(sourceFile, anmolFile):
   sourceFileHandle = open(sourceFile, 'rb')
   targetFileHandle = open(targetFile, 'wb')
   readerPointer = csv.reader(sourceFileHandle, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)
   writerPointer = csv.writer(targetFileHandle, delimiter=' ', quotechar='|',quoting=csv.QUOTE_MINIMAL)

   readerPointer.next()
   
   for row in readerPointer:  
      
def main():
   #writer()
   headerList = readCsvHeader(hclFile)
   #import pdb;pdb.set_trace()
#   for i in headerList:
#      print "%s \n" % i

#   import urllib
#   test1=urllib.urlopen("http://partnerweb.vmware.com/service/vsan/ssd.json").read()
#   print test1
#   readHcl(hclFile)
   
   #readHcl('NewhardwareInfoOld.csv')
   checkHCL('NewhardwareInfoOld.csv', 'helonewFile.csv')   

# Start program
if __name__ == '__main__':
   main()

'''
