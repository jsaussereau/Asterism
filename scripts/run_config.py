'''
Copyright(C) 2022 by Jonathan Saussereau. All rights reserved.

All source codes and documentation contain proprietary confidential
information and are distributed under license. It may be used, copied
and/or disclosed only pursuant to the terms of a valid license agreement
with Jonathan Saussereau. This copyright must be retained at all times.

result_to_csv.py

use example: python3 run_config.py
''' 

import re
import sys
import time
import yaml
import argparse
import subprocess

from yaml.loader import SafeLoader

from os.path import isfile
from os.path import isdir
from os import makedirs
from os import listdir

from shutil import rmtree
from shutil import copytree

######################################
# Settings
######################################

work_path = "work"
script_path = "eda_tools"
work_script_path = "scripts"
common_script_path = "_common"
log_path = "log"
arch_path = "architectures"

param_settings_filename = "_settings.yml"
arch_filename = "architecture.txt"
target_filename = "target.txt"
config_filename = "settings.tcl"
fmax_status_filename = "status.log"
synth_status_filename = "synth_status.log"
tool_makefile_filename = "makefile.mk"

source_settings_tcl = "source scripts/settings.tcl"
synth_fmax_rule = "synth_fmax_only"

settings_ini_section = "SETTINGS"
valid_status = "Done: 100%"

progress_bar_size = 50
refresh_time = 5

default_fmax_lower_bound = 50
default_fmax_upper_bound = 500

fmax_status_pattern = re.compile("(.*): ([0-9]+)% \(([0-9]+)\/([0-9]+)\)(.*)")
synth_status_pattern = re.compile("(.*): ([0-9]+)%(.*)")

tcl_bool_true = ['true', 'yes', 'on', '1']
tcl_bool_false = ['false', 'no', 'off', '0']

######################################
# Misc classes
######################################

class Running_arch:
  def __init__(self, process, arch):
    self.process = process
    self.arch = arch

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKCYAN = '\033[96m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'


######################################
# Misc functions
######################################

def read_from_list(key, input_list, filename, raise_if_missing=True):
  if key in input_list:
    return input_list[key]
  else:
    if raise_if_missing:
      print(bcolors.BOLD + bcolors.FAIL + "error: Cannot find key \"" + key + "\" in \"" + filename + "\"." + bcolors.ENDC)
      raise
    return False

def read_from_config(identifier, config, filename):
  if identifier in config[settings_ini_section]:
    return config[settings_ini_section][identifier]
  else:
    print(bcolors.BOLD + bcolors.FAIL + "error: Cannot find identifier \"" + identifier + "\" in \"" + filename + "\"." + bcolors.ENDC)
    raise
    return False

def print_arch_list(arch_list, description, color):
  if not len(arch_list) > 0:
    return

  print()
  print(bcolors.BOLD + description + ":" + bcolors.ENDC)
  print(color, end = '')
  for arch in arch_list:
    print("  - " + arch)
  print(bcolors.ENDC, end = '')

def move_cursor_up():
  sys.stdout.write('\x1b[1A')
  sys.stdout.flush()

def progress_bar(progress, title, endstr=''):
  if progress > 100:
    progress = 100
  
  limit = int(progress * progress_bar_size / 100)
        
  print(title + ": [", end = '')
  for i in range(0, limit):
    print('#', end = '')
  for i in range(limit, progress_bar_size):
    print(' ', end = '')
  print("] {}%".format(int(progress)) + endstr)

def parse_arguments():
  parser = argparse.ArgumentParser(description='Run fmax synthesis on selected architectures')
  parser.add_argument('-i', '--input', default='architecture_select.yml',
                      help='input architecture file (default: architecture_select.yml)')
  parser.add_argument('-m', '--mode', choices=['fpga', 'asic'], default='fpga',
                      help='Select the mode (fpga or asic, default: fpga)')
  parser.add_argument('-t', '--tool', default='vivado',
                      help='eda tool in use (default: vivado)')
  parser.add_argument('-w', '--overwrite', action='store_true',
                      help='overwrite existing results')
  parser.add_argument('-y', '--noask', action='store_true',
                      help='do not ask to continue')
  return parser.parse_args()


######################################
# Main
######################################

if __name__ == "__main__":

  args = parse_arguments()

  if args.mode != 'fpga' and args.mode != 'asic' :
    raise ValueError("Invalid mode selected. Please choose 'fpga' or 'asic'.")
  
  work_path += "/" + args.mode 

  run_config_settings_filename = args.input
  tool = args.tool

  eda_target_filename = "target_" + tool + ".yml"

  # Get settings from yaml file
  if not isfile(run_config_settings_filename):
    print(bcolors.BOLD + bcolors.FAIL + "error: Settings file \"" + run_config_settings_filename + "\" does not exist" + bcolors.ENDC)
    sys.exit()

  with open(run_config_settings_filename, 'r') as f:
    settings_data = yaml.load(f, Loader=SafeLoader)
    try:
      overwrite       = read_from_list("overwrite", settings_data, run_config_settings_filename)
      ask_continue    = read_from_list("ask_continue", settings_data, run_config_settings_filename)
      show_log_if_one = read_from_list("show_log_if_one", settings_data, run_config_settings_filename)
      use_screen      = read_from_list("use_screen", settings_data, run_config_settings_filename)
      architectures   = read_from_list("architectures", settings_data, run_config_settings_filename)
    except:
      sys.exit() # if a key is missing

  if not isfile(eda_target_filename):
    print(bcolors.BOLD + bcolors.FAIL + "error: Target file \"" + eda_target_filename + "\", for the selected eda tool \"" + tool + "\" does not exist" + bcolors.ENDC)
    sys.exit()

  with open(eda_target_filename, 'r') as f:
    settings_data = yaml.load(f, Loader=SafeLoader)
    try:
      targets         = read_from_list("targets", settings_data, eda_target_filename)
    except:
      sys.exit() # if a key is missing

  if args.overwrite:
    overwrite = True
  
  if args.noask:
    ask_continue = False

  for target in targets:

    print(bcolors.BOLD + bcolors.OKCYAN, end='')
    print("######################################")
    print(" Target: {}".format(target))
    print("######################################")
    print(bcolors.ENDC)
 
    banned_arch_param = []
    valid_archs = []
    cached_archs = []
    overwrite_archs = []
    error_archs = []
    incomplete_archs = []
    new_archs = []

    for arch in architectures:
      tmp_dir = work_path + '/' + target + '/' + arch
      fmax_status_file = tmp_dir + '/' + log_path + '/' + fmax_status_filename

      # get param dir (arch name before '/')
      arch_param_dir = re.sub('/.*', '', arch)

      # check if arch_param has been banned
      if arch_param_dir in banned_arch_param:
        error_archs.append(arch)
        continue

      # check if parameter dir exists
      arch_param = arch_path + '/' + arch_param_dir
      if not isdir(arch_param):
        print(bcolors.BOLD + bcolors.FAIL + "error: There is no directory \"" + arch_param_dir + "\" in directory \"" + arch_path + "\"" + bcolors.ENDC)
        error_archs.append(arch)
        continue
      
      # check if settings file exists
      if not isfile(arch_param + '/' + param_settings_filename):
        print(bcolors.BOLD + bcolors.FAIL + "error: There is no setting file \"" + param_settings_filename + "\" in directory \"" + arch_param + "\"" + bcolors.ENDC)
        banned_arch_param.append(arch_param_dir)
        error_archs.append(arch)
        continue

      # get settings variables
      settings_filename = arch_path + '/' + arch_param_dir + '/' + param_settings_filename
      with open(settings_filename, 'r') as f:
        settings_data = yaml.load(f, Loader=SafeLoader)
        try:
          rtl_path           = read_from_list('rtl_path', settings_data, settings_filename)
          top_level_filename = read_from_list('top_level_file', settings_data, settings_filename)
          top_level_module   = read_from_list('top_level_module', settings_data, settings_filename)
          rtl_file_format    = read_from_list('rtl_file_format', settings_data, settings_filename)
          clock_signal       = read_from_list('clock_signal', settings_data, settings_filename)
          file_copy_enable   = read_from_list('file_copy_enable', settings_data, settings_filename)
          file_copy_source   = read_from_list('file_copy_source', settings_data, settings_filename)
          file_copy_dest     = read_from_list('file_copy_dest', settings_data, settings_filename)
          use_parameters     = read_from_list('use_parameters', settings_data, settings_filename)
          start_delimiter    = read_from_list('start_delimiter', settings_data, settings_filename)
          stop_delimiter     = read_from_list('stop_delimiter', settings_data, settings_filename)
        except:
          banned_arch_param.append(arch_param_dir)
          error_archs.append(arch)
          continue # if an identifier is missing

      # check if file_copy_enable is a boolean
      file_copy_enable = file_copy_enable.lower()
      if not (file_copy_enable in tcl_bool_true or file_copy_enable in tcl_bool_false):
        print(bcolors.BOLD + bcolors.FAIL + "error: Value for identifier \"file_copy_enable\" is not one of the boolean value supported by tcl (\"true\", \"false\", \"yes\", \"no\", \"on\", \"off\", \"1\", \"0\")" + bcolors.ENDC)
        error_archs.append(arch)
        continue

      # check if rtl path exists
      if not isdir(rtl_path):
        print(bcolors.BOLD + bcolors.FAIL + "error: The rtl path \"" + rtl_path + "\" specified in \"" + settings_filename + "\" does not exist" + bcolors.ENDC)
        error_archs.append(arch)
        continue

      # check if top level file path exists
      top_level = rtl_path + '/' + top_level_filename
      if not isfile(top_level):
        print(bcolors.BOLD + bcolors.FAIL + "error: The top level file \"" + top_level_filename + "\" specified in \"" + settings_filename + "\" does not exist" + bcolors.ENDC)
        error_archs.append(arch)
        continue

      # check if the top level module name exists in the top level file, at least
      f = open(top_level, "r")
      if not top_level_module in f.read():
        print(bcolors.BOLD + bcolors.FAIL + "error: There is no occurence of top level module name \"" + top_level_module + "\" in top level file \"" + top_level + "\"" + bcolors.ENDC)
        error_archs.append(arch)
        f.close()
        continue
      f.close()
      
      # check if the top clock name exists in the top level file, at least
      f = open(top_level, "r")
      if not clock_signal in f.read():
        print(bcolors.BOLD + bcolors.FAIL + "error: There is no occurence of clock signal name \"" + clock_signal + "\" in top level file \"" + top_level + "\"" + bcolors.ENDC)
        error_archs.append(arch)
        f.close()
        continue
      f.close()

      # check if param file exists
      if not isfile(arch_path + '/' + arch + '.txt'):
        print(bcolors.BOLD + bcolors.FAIL + "error: The parameter file \"" + arch + ".txt\" does not exist in directory \"" + arch_path + "/" + arch_param_dir + "\"" + bcolors.ENDC)
        error_archs.append(arch)
        continue

      # check file copy
      if file_copy_enable in tcl_bool_true:
        if not isfile(file_copy_source):
          print(bcolors.BOLD + bcolors.FAIL + "error: The source file to copy \"" + file_copy_source + "\" does not exist" + bcolors.ENDC)
          error_archs.append(arch)
          continue

      # check if the architecture is in cache and has a status file
      if isdir(tmp_dir) and isfile(fmax_status_file):
        # check if the previous synth_fmax has completed
        f = open(fmax_status_file, "r")
        if valid_status in f.read():
          if overwrite:
            print(bcolors.WARNING + "Found cached results for \"" + arch + "\" with target \"" + target + "\"." + bcolors.ENDC)
            overwrite_archs.append(arch)
            f.close()
          else:
            print(bcolors.OKCYAN + "Found cached results for \"" + arch + "\" with target \"" + target + "\". Skipping." + bcolors.ENDC)
            cached_archs.append(arch)
            f.close()
            continue
        else: 
          print(bcolors.WARNING + "The previous synthesis for \"" + arch + "\" has not finished or the directory has been corrupted." + bcolors.ENDC)
          incomplete_archs.append(arch)
          f.close()
      else:
        new_archs.append(arch)
      
      # passed all check: added to the list
      valid_archs.append(arch)
    
    # print checklist summary
    print_arch_list(new_archs, "New architectures", bcolors.ENDC)
    print_arch_list(incomplete_archs, "Incomplete results (will be overwritten)", bcolors.WARNING)
    print_arch_list(cached_archs, "Existing results (skipped)", bcolors.OKCYAN)
    print_arch_list(overwrite_archs, "Existing results (will be overwritten)", bcolors.WARNING)
    print_arch_list(error_archs, "Invalid settings, (skipped, see errors above)", bcolors.FAIL)

    if ask_continue and len(valid_archs) > 0:
      print()
      while True:
        answer = input("Continue? (Y/n) ")
        if answer.lower() in ['yes', 'ye', 'y', '1', '']:
          break
        elif answer.lower() in ['no', 'n', '0']:
          sys.exit()
        else:
          print("Please enter yes or no")

    print()  
    running_arch_list = []
    active_running_arch_list = []

    #print("valid_architectures : {}".format(valid_architectures))
    for arch in valid_archs:
      tmp_dir = work_path + '/' + target + '/' + arch

      # create directory
      if isdir(tmp_dir):
        rmtree(tmp_dir)
      makedirs(tmp_dir)

      # copy scripts
      tmp_script_path = tmp_dir + '/' + work_script_path
      copytree(script_path + '/' + common_script_path, tmp_script_path)
      copytree(script_path + '/' + tool + '/tcl', tmp_script_path, dirs_exist_ok = True)

      # create target and architecture files
      f = open(tmp_dir + '/' + target_filename, 'w')
      print(target, file = f)
      f.close()
      f = open(tmp_dir + '/' + arch_filename, 'w')
      print(arch, file = f)
      f.close()

      # get param dir (arch name before '/')
      arch_param_dir = re.sub('/.*', '', arch)

      # get settings variables
      settings_filename = arch_path + '/' + arch_param_dir + '/' + param_settings_filename
      with open(settings_filename, 'r') as f:
        settings_data = yaml.load(f, Loader=SafeLoader)
        try:
          rtl_path           = read_from_list('rtl_path', settings_data, settings_filename)
          top_level_filename = read_from_list('top_level_file', settings_data, settings_filename)
          top_level_module   = read_from_list('top_level_module', settings_data, settings_filename)
          rtl_file_format    = read_from_list('rtl_file_format', settings_data, settings_filename)
          clock_signal       = read_from_list('clock_signal', settings_data, settings_filename)
          file_copy_enable   = read_from_list('file_copy_enable', settings_data, settings_filename)
          file_copy_source   = read_from_list('file_copy_source', settings_data, settings_filename)
          file_copy_dest     = read_from_list('file_copy_dest', settings_data, settings_filename)
          use_parameters     = read_from_list('use_parameters', settings_data, settings_filename)
          start_delimiter    = read_from_list('start_delimiter', settings_data, settings_filename)
          stop_delimiter     = read_from_list('stop_delimiter', settings_data, settings_filename)
        except:
          continue # if an identifier is missing (modified since first read)
        
        # optionnal settings
        target_options     = read_from_list(target, settings_data, settings_filename, raise_if_missing=False)
        if target_options != False:
          fmax_lower_bound = str(target_options['fmax_lower_bound'])
          fmax_upper_bound = str(target_options['fmax_upper_bound'])
        else:
          fmax_lower_bound = str(default_fmax_lower_bound)
          fmax_upper_bound = str(default_fmax_upper_bound)
        
      # set source and dest to null if copy is disabled
      file_copy_enable = file_copy_enable.lower()
      if not file_copy_enable in tcl_bool_true:
        file_copy_enable = "false"
        file_copy_source = "/dev/null"
        file_copy_dest = "/dev/null"

      use_parameters = use_parameters.lower()
      if not use_parameters in tcl_bool_true:
        use_parameters = "false"

      # add escape characters
      #start_delimiter = re.sub("(/)", "\\\\\\\\/", start_delimiter)
      #stop_delimiter = re.sub("(/)", "\\\\\\\\/", stop_delimiter)

      # add quote characters
      start_delimiter = '"' + start_delimiter + '"'
      stop_delimiter = '"' + stop_delimiter + '"'
      
      # edit config script
      config_file = tmp_script_path + '/' + config_filename
      with open(config_file, 'r') as f:
        cf_content = f.read()
     
      cf_content = re.sub("(set script_path.*)", "set script_path       " + tmp_script_path, cf_content)
      cf_content = re.sub("(set tmp_path.*)", "set tmp_path          " + tmp_dir, cf_content)
      cf_content = re.sub("(set rtl_path.*)", "set rtl_path          " + rtl_path, cf_content)
      cf_content = re.sub("(set arch_path.*)", "set arch_path         " + arch_path, cf_content)
      cf_content = re.sub("(set clock_signal.*)", "set clock_signal      " + clock_signal, cf_content)
      cf_content = re.sub("(set top_level_module.*)", "set top_level_module  " + top_level_module, cf_content)
      cf_content = re.sub("(set top_level_file.*)", "set top_level_file    " + top_level_filename, cf_content)
      cf_content = re.sub("(set use_parameters.*)", "set use_parameters    " + use_parameters, cf_content)
      cf_content = re.sub("(set start_delimiter.*)", "set start_delimiter   " + start_delimiter, cf_content)
      cf_content = re.sub("(set stop_delimiter.*)", "set stop_delimiter    " + stop_delimiter, cf_content)
      cf_content = re.sub("(set rtl_file_format.*)", "set rtl_file_format   " + rtl_file_format, cf_content)
      cf_content = re.sub("(set file_copy_enable.*)", "set file_copy_enable  " + file_copy_enable, cf_content)
      cf_content = re.sub("(set file_copy_source.*)", "set file_copy_source  " + file_copy_source, cf_content)
      cf_content = re.sub("(set file_copy_dest.*)", "set file_copy_dest    " + file_copy_dest, cf_content)
      cf_content = re.sub("(set fmax_lower_bound.*)", "set fmax_lower_bound  " + fmax_lower_bound, cf_content)
      cf_content = re.sub("(set fmax_upper_bound.*)", "set fmax_upper_bound  " + fmax_upper_bound, cf_content)

      with open(config_file, 'w') as f:
        f.write(cf_content)

      # link all scripts to config script
      for filename in listdir(tmp_script_path):
        if filename.endswith('.tcl'):
          with open(tmp_script_path + '/' + filename, 'r') as f:
            tcl_content = f.read()
          tcl_content = re.sub("("+ source_settings_tcl + ")", "source " + config_file, tcl_content)
          with open(tmp_script_path + '/' + filename, 'w') as f:
            f.write(tcl_content)

      # run binary search script
      if len(valid_archs) == 1 and show_log_if_one:
        #process = subprocess.run(["make", "-f", script_path + "/" + tool + "/" + tool_makefile_filename, synth_fmax_rule, "SCRIPT_DIR=\"" + tmp_dir + '/' + work_script_path + "\"", "LOG_DIR=\"" + tmp_dir + '/' + log_path + "\"", "--no-print-directory"])
        process = subprocess.Popen(["make", "-f", script_path + "/" + tool + "/" + tool_makefile_filename, synth_fmax_rule, "SCRIPT_DIR=\"" + tmp_dir + '/' + work_script_path + "\"", "LOG_DIR=\"" + tmp_dir + '/' + log_path + "\"", "--no-print-directory"])
      else:
        process = subprocess.Popen(["make", "-f", script_path + "/" + tool + "/" + tool_makefile_filename, synth_fmax_rule, "SCRIPT_DIR=\"" + tmp_dir + '/' + work_script_path + "\"", "LOG_DIR=\"" + tmp_dir + '/' + log_path + "\"", "--no-print-directory"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

      running_arch_list.append(Running_arch(process, arch))
      print("started job for architecture \"{}\" between {} and {} MHz with pid {}".format(arch, fmax_lower_bound, fmax_upper_bound, process.pid))

    # prepare output
    print()
    for running_arch in running_arch_list:
      print() 

    active_running_arch_list = running_arch_list

    # wait for all processes to finish
    while len(active_running_arch_list) > 0:
      if not(len(running_arch_list) == 1 and show_log_if_one):
        # go back to first line
        for running_arch in running_arch_list:
          move_cursor_up()

      for running_arch in running_arch_list:

        # get status files full paths
        tmp_dir = work_path + '/' + target + '/' + running_arch.arch
        fmax_status_file = tmp_dir + '/' + log_path + '/' + fmax_status_filename
        synth_status_file = tmp_dir + '/' + log_path + '/' + synth_status_filename

        # get progress from fmax status file
        fmax_progress = 0
        fmax_step = 1
        fmax_totalstep = 1
        if isfile(fmax_status_file):
          with open(fmax_status_file, 'r') as f:
            content = f.read()
          for match in re.finditer(fmax_status_pattern, content):
            parts = fmax_status_pattern.search(match.group())
            if len(parts.groups()) >= 4:
              fmax_progress = int(parts.group(2))
              fmax_step = int(parts.group(3))
              fmax_totalstep = int(parts.group(4))
        
        # get progress from synth status file
        synth_progress = 0
        if isfile(synth_status_file):
          with open(synth_status_file, 'r') as f:
            content = f.read()
          for match in re.finditer(synth_status_pattern, content):
            parts = synth_status_pattern.search(match.group())
            if len(parts.groups()) >= 2:
              synth_progress = int(parts.group(2))

        # compute progress
        if fmax_totalstep != 0:
          progress = fmax_progress + synth_progress / fmax_totalstep
        else:
          progress = synth_progress
          
        # check if process has finished and print progress 
        if running_arch.process.poll() != None:
          active_running_arch_list.remove(running_arch)
          progress_bar(progress, title=running_arch.arch, endstr=" (terminated)")
        else: 
          progress_bar(progress, title=running_arch.arch)

      time.sleep(refresh_time)