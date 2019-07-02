#****************************************************************
"""
# This file will query the command line to see what BatchID it should use,
# or if no arguement is given on the CL, the most recent BatchID will be used
# This BatchID is used to identify the proper scard and gcards, and then submission
# files corresponding to each gcard are generated and stored in the database, as
# well as written out to a file with a unique name. This latter part will be passed
# to the server side in the near future.
"""
#****************************************************************
from __future__ import print_function
import os, sqlite3, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/../../utils')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/../submission_files')
import farm_submission_manager
import utils, file_struct, scard_helper, lund_helper, get_args
from script_generators.runscript_generators import runScriptHeader, runGenerator, runGemc, runEvio2hipo, runCooking, runScriptFooter
from script_generators.clas12condor_generators import condorHeader, condorJobDetails, condorFilesHandler
from script_generators.run_job_generators import run_job1

#Grabs all GCards from a corresponding Batch
def grab_gcards(BatchID):
  strn = "SELECT GcardID, gcard_text FROM Gcards WHERE BatchID = {0};".format(BatchID)
  gcards = utils.sql3_grab(strn)
  return gcards

#Grabs all GCards from a corresponding Batch
def grab_username(BatchID):
  strn = "SELECT User FROM Batches WHERE BatchID = {0};".format(BatchID)
  username = utils.sql3_grab(strn)
  return username

def grab_scard(BatchID):
  strn = "SELECT scard FROM Batches WHERE BatchID = {0};".format(BatchID)
  scard_text = utils.sql3_grab(strn)[0][0]
  return scard_text

#Generates a script by appending functions that output strings
def script_factory(args,script_obj,script_functions,function_names,scard,params,file_extension):

  script_text = ""
  runscript_filename=file_struct.runscript_file_obj.file_path+file_struct.runscript_file_obj.file_base
  runscript_filename= runscript_filename + file_extension + file_struct.runscript_file_obj.file_end
  runjob_filename=file_struct.run_job_obj.file_path+file_struct.run_job_obj.file_base
  runjob_filename= runjob_filename+ file_extension + file_struct.run_job_obj.file_end

  #In the below for loop, we loop through all script_generators for a certain submission script, appending the output of each function to a string
  for count, function in enumerate(script_functions):
    generated_text = getattr(function,function_names[count])(
                            scard,username=params['username'],gcard_loc=params['gcard_loc'],
                            GcardID = params['GcardID'],lund_dir = params['lund_dir'],
                            database_filename = params['database_filename'],file_extension = file_extension,
                            runscript_filename=runscript_filename, runjob_filename=runjob_filename,
                            using_sqlite = args.lite,)
    script_text += generated_text

  #This handles writing to disk and to SQL database
  if args.write_files:
    filename = script_obj.file_path+script_obj.file_base+file_extension+script_obj.file_end
    utils.printer("\tWriting submission file '{0}' based off of specifications of BatchID = {1}, GcardID = {2}".format(filename,
        params['BatchID'],params['GcardID']))
    if os.path.isfile(filename):
      subprocess.call(['rm',filename])
    with open(filename,"a") as file: file.write(script_text)
  str_script_db = script_text.replace('"',"'") #I can't figure out a way to write "" into a sqlite field without errors
  # For now, we can replace " with ', which works ok, but IDK how it will run if the scripts were submitted to HTCondor
  strn = 'UPDATE Submissions SET {0} = "{1}" WHERE GcardID = {2};'.format(script_obj.file_text_fieldname,str_script_db,params['GcardID'])
  utils.sql3_exec(strn)

def submission_script_maker(args,BatchID):
  file_struct.DEBUG = getattr(args,file_struct.debug_long)
  # Grabs batch and gcards as described in respective files
  gcards = grab_gcards(BatchID)
  username = grab_username(BatchID)[0][0]
  scard = scard_helper.scard_class(grab_scard(BatchID))

  """#***************************************************************************
  #There is probably some coding mechanism which will accomplish this block of code more effiently,
  #but I cannot think of it currently. Essentially, the import statements at the top of this file
  #specify a list of script_generators functions that will be run. There should be a way to pass
  #this list of functions to script_factory(), but I couldn't find a way to do it. Instead we have to
  #write out all the functions, and their names, and pass them to script_factory()
  """
  # script to be run inside the container
  funcs_rs = ( runScriptHeader ,  runGenerator ,  runGemc , runEvio2hipo , runCooking ,  runScriptFooter )
  fname_rs = ('runScriptHeader', 'runGenerator', 'runGemc','runEvio2hipo','runCooking', 'runScriptFooter')

  # condor submission script
  # note: to be executed only for OSG and MIT farms
  funcs_condor = ( condorHeader , condorJobDetails , condorFilesHandler)
  fname_condor = ('condorHeader','condorJobDetails','condorFilesHandler')

  # condor wrapper
  # note: to be executed only for OSG and MIT farms
  funcs_runjob = (run_job1,)
  fname_runjob = ('run_job1',)

  """#***************************************************************************"""

  if 'https://' in scard.data.get('generator'):
    lund_dir = lund_helper.Lund_Entry(scard.data.get('generator'))
    scard.data['genExecutable'] = "Null"
    scard.data['genOutput'] = "Null"
  else:
    lund_dir = 0
    scard.data['genExecutable'] = file_struct.genExecutable.get(scard.data.get('generator'))
    scard.data['genOutput'] = file_struct.genOutput.get(scard.data.get('generator'))

  for gcard in gcards:
    GcardID = gcard[0]

    if scard.data['gcards'] == file_struct.gcard_default:
      gcard_loc = scard.data['gcards']
    elif 'https://' in  scard.data['gcards']:
      utils.printer('Writing gcard to local file')
      newfile = "gcard_{0}_batch_{1}.gcard".format(GcardID,BatchID)
      gfile= file_struct.sub_files_path+file_struct.gcards_dir+newfile
      with open(gfile,"w") as file: file.write(gcard[1])
      gcard_loc = 'submission_files/gcards/'+newfile
    else:
      print('gcard not recognized as default option or online repository, please inspect scard')
      exit()

    file_extension = "_gcard_{0}_batch_{1}".format(GcardID,BatchID)

    if file_struct.use_mysql:
      DB_path = file_struct.MySQL_DB_path
    else:
      DB_path = file_struct.SQLite_DB_path

    params = {'table':'Scards','BatchID':BatchID,'GcardID':GcardID,'database_filename':DB_path+file_struct.DB_name,
              'username':username,'gcard_loc':gcard_loc,'lund_dir':lund_dir}

    script_factory(args,file_struct.runscript_file_obj,funcs_rs,fname_rs,scard,params,file_extension)
    script_factory(args,file_struct.condor_file_obj,funcs_condor,fname_condor,scard,params,file_extension)
    script_factory(args,file_struct.run_job_obj,funcs_runjob,fname_runjob,scard,params,file_extension)
    print("\tSuccessfully generated submission files for Batch {0} with GcardID {1}".format(BatchID,GcardID))

    submission_string = 'Submission scripts generated'.format(scard.data['farm_name'])
    strn = "UPDATE Submissions SET {0} = '{1}' WHERE BatchID = {2};".format('run_status',submission_string,BatchID)
    utils.sql3_exec(strn)

    if args.submit:
      print("\tSubmitting jobs to {0} \n".format(scard.data['farm_name']))
      farm_submission_manager.farm_submission_manager(args,GcardID,file_extension,scard,params)
      submission_string = 'Submitted to {0}'.format(scard.data['farm_name'])
      strn = "UPDATE Submissions SET {0} = '{1}' WHERE BatchID = {2};".format('run_status',submission_string,BatchID)
      utils.sql3_exec(strn)

def process_jobs(args):
  if args.BatchID != 'none':
    Batches = []
    strn = "SELECT BatchID FROM Batches;"
    Batches_array = utils.sql3_grab(strn)
    for i in Batches_array: Batches.append(i[0])
    if not int(args.BatchID) in Batches:
      print("The selected batch (BatchID = {0}) does not exist, exiting".format(args.BatchID))
      exit()
    else:
      BatchID = args.BatchID
      submission_script_maker(args,BatchID)
  else:
    if args.submit:
      strn = "SELECT BatchID FROM Submissions WHERE run_status NOT LIKE '{0}';".format("Submitted to%")
      batches_to_submit = utils.sql3_grab(strn)
      if len(batches_to_submit) == 0:
        print("There are no batches which have not yet been submitted to a farm")
    else:
      strn = "SELECT BatchID FROM Submissions WHERE run_status = '{0}';".format("Not Submitted")
      batches_to_submit = utils.sql3_grab(strn)
      if len(batches_to_submit) == 0:
        print("There are no batches which do not yet have submission scripts generated")
    if len(batches_to_submit) != 0:
      for Batch in batches_to_submit:
        BatchID = Batch[0]
        utils.printer("Generating scripts for batch with BatchID = {0}".format(str(BatchID)))
        submission_script_maker(args,BatchID)


if __name__ == "__main__":
  args = get_args.get_args()
  process_jobs(args)
