#****************************************************************
"""
# This distribuits job sumbissions to HTCondor, SLURM, etc. based off what the node runs.
"""
#****************************************************************

from __future__ import print_function
import argparse, os, sqlite3, subprocess, sys, time
from subprocess import PIPE, Popen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/../../utils')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))+'/../submission_files')
#Could also do the following, but then python has to search the
#sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import htcondor_submit, slurm_submit
import Submit_batch
import file_struct, utils

def update_users_statistics(scard,params):
  strn = "SELECT Total_Batches FROM Users WHERE User = '{0}';".format(params['username'])
  batches_total = utils.sql3_grab(strn)[0][0]
  batches_total += 1
  strn = "UPDATE Users SET Total_Batches = '{0}' WHERE User = '{1}';".format(batches_total,params['username'])
  utils.sql3_exec(strn)

  strn = "SELECT Total_Jobs FROM Users WHERE User = '{0}';".format(params['username'])
  jobs_total = utils.sql3_grab(strn)[0][0]
  jobs_total += int(scard.data['jobs'])
  strn = "UPDATE Users SET Total_Jobs = '{0}' WHERE User = '{1}';".format(jobs_total,params['username'])
  utils.sql3_exec(strn)

  if 'nevents' in scard.data:
    strn = "SELECT Total_Events FROM Users WHERE User = '{0}';".format(params['username'])
    events_total = utils.sql3_grab(strn)[0][0]
    events_total += int(scard.data['jobs'])*int(scard.data['nevents'])
    strn = "UPDATE Users SET Total_Events = '{0}' WHERE User = '{1}';".format(events_total,params['username'])
    utils.sql3_exec(strn)
  else:
    print("""No explicit events number found, this will be handled in future. This does not affect the simulation, and
            only means that you are using a custom LUND file.""")

  strn = "UPDATE Users SET Most_Recent_Active_Date = '{0}' WHERE User = '{1}';".format(utils.gettime(),params['username'])
  utils.sql3_exec(strn)

"""The below can be extended in a better way for more farms, e.g. create a dictionary"""
def farm_submission_manager(args,GcardID,file_extension,scard,params):
  if scard.data['farm_name'] == "MIT_Tier2" or scard.data['farm_name'] == "OSG":
    utils.printer("Passing to htcondor_submit")
    htcondor_submit.htcondor_submit(args,GcardID,file_extension)
    update_users_statistics(scard,params)
  elif scard.data['farm_name'] == "JLab":
    utils.printer("Passing to slurm_submit")
    slurm_submit.slurm_submit(args,GcardID,file_extension)
    update_users_statistics(scard,params)
  else:
    print('Invalid farm name in scard, please check that the desired farm is spelled correctly and is supported')
    exit()
