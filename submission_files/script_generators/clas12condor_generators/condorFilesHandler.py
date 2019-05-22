# Handles the file moves and transfer
#
# Notice: hardcoding the name and path: CLAS12_OCRDB.db until DB_path is handled properly
# (Assuming it's in the same dir as where condor submit is executed)
#

def condorFilesHandler(scard,**kwargs):

  farm_name = scard.data.get('farm_name')
  # if it's a test, the Database should be copied
  # for now, copying it anyway, but path is hardcoded
  # transfer_input_files={0}, condor_wrapper


  # OSG Farm: condor wrapper is not needed
  strnInput = """
# Input files
transfer_input_files=CLAS12_OCRDB.db
"""
  # MIT Farm: condor wrapper is needed. Notice, path is needed? Can we assume this 
  if farm_name == 'MIT_Tier2':
    strnInput = """
# Input files
transfer_input_files=CLAS12_OCRDB.db, condor_wrapper
"""


  strnOutput = """
# Output directory
transfer_output_files = out_{0}

# How to handle output
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
""".format(kwargs['GcardID'])

  strnQueue = """
# QUEUE is the "start button" - it launches any jobs that have been
# specified thus far. 1 means launch only 1 job
Queue {0}\n

""".format(scard.data['jobs'])

  return strnInput + strnOutput + strnQueue
