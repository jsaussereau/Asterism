#**********************************************************************#
#                               Asterism                               #
#**********************************************************************#
#
# Copyright (C) 2022 Jonathan Saussereau
#
# This file is part of Asterism.
# Asterism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Asterism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Asterism. If not, see <https://www.gnu.org/licenses/>.
#

import os
import re
import sys
import yaml
import argparse

# add local libs to path
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(current_dir, 'lib')
sys.path.append(lib_path)

import printc
from replace_params import replace_params

from simulation_handler import SimulationHandler
from settings import AsterismSettings
from utils import *
from prepare_work import *
from run_parallel import *
from run_settings import *

######################################
# Settings
######################################

work_path = "work/simulation"
work_script_path = "scripts"
common_script_path = "_common"
log_path = "log"
arch_path = "architectures"
sim_path = "simulations"
rtl_path = "rtl"

nb_jobs = 4

param_settings_filename = "_settings.yml"
sim_settings_filename = "_settings.yml"
sim_makefile_filename = "Makefile"
sim_rule = "sim"

progress_bar_size = 50
refresh_time = 5

default_fmax_lower_bound = 50
default_fmax_upper_bound = 500

fmax_status_pattern = re.compile(r"(.*): ([0-9]+)% \(([0-9]+)\/([0-9]+)\)(.*)")
synth_status_pattern = re.compile(r"(.*): ([0-9]+)%(.*)")

script_name = os.path.basename(__file__)

######################################
# Parse Arguments
######################################

def add_arguments(parser):
  parser.add_argument('-o', '--overwrite', action='store_true', help='overwrite existing results')
  parser.add_argument('-y', '--noask', action='store_true', help='do not ask to continue')
  parser.add_argument('-i', '--input', help='input settings file')
  parser.add_argument('-a', '--archpath', help='architecture directory')
  parser.add_argument('-s', '--simpath', help='simulation directory')
  parser.add_argument('-w', '--work', help='simulation work directory')
  parser.add_argument('-c', '--config', default=AsterismSettings.DEFAULT_SETTINGS_FILE, help='global settings file for asterism (default: ' + AsterismSettings.DEFAULT_SETTINGS_FILE + ')')

def parse_arguments():
  parser = argparse.ArgumentParser(description='Run parallel simulations')
  add_arguments(parser)
  return parser.parse_args()


######################################
# Run Simulations
######################################

def run_simulations(run_config_settings_filename, arch_path, sim_path, work_path, overwrite, noask):
  _overwrite, ask_continue, show_log_if_one, nb_jobs, simulations = get_sim_settings(run_config_settings_filename)

  if overwrite:
    overwrite = True
  else:
    overwrite = _overwrite
  
  if noask:
    ask_continue = False

  Running_arch.set_patterns(fmax_status_pattern, synth_status_pattern)

  sim_handler = SimulationHandler(
    work_path = work_path,
    arch_path = arch_path,
    sim_path = sim_path,
    work_script_path = work_script_path,
    log_path = log_path,
    overwrite = overwrite,
    param_settings_filename = param_settings_filename,
    sim_settings_filename = sim_settings_filename,
    sim_makefile_filename = sim_makefile_filename
  )

  if simulations is None:
    printc.note("No simulation selected. Exiting.", script_name)
    sys.exit(-1)
    
  try:
    simulation_instances = sim_handler.get_simulations(simulations)
  except Exception as e:
    printc.error("Could not get list \"simulations\" from \"" + run_config_settings_filename + "\".", script_name=script_name)
    printc.note("Is the YAML file valid? Are you missing a ':'? Is the indentation correct?", script_name=script_name)
    printc.cyan("error details: ", end="", script_name=script_name)
    print(str(e))
    sys.exit(-1)

  # print checklist summary
  sim_handler.print_summary()

  # split architecture in chunks, depending on the number of jobs
  simulation_instances_chunks, nb_chunks = sim_handler.get_chuncks(nb_jobs)

  # ask to quit or continue
  if sim_handler.get_valid_sim_count() > 0:
    if ask_continue:
      print()
      ask_to_continue()
  else:
    sys.exit(-1)

  print()

  for i_chunk in range(nb_chunks):
    running_arch_list = []
    active_running_arch_list = []
    
    if nb_chunks == 1:
      simulation_instances_chunk = simulation_instances
    else:
      simulation_instances_chunk = simulation_instances_chunks[i_chunk]

    for i_sim in simulation_instances_chunk:

      # create directory
      create_dir(i_sim.tmp_dir)

      # copy simulation sources
      copytree(i_sim.source_sim_dir, i_sim.tmp_dir, dirs_exist_ok = True)
     
      # copy design 
      if i_sim.architecture.design_path != -1:
        try:
          copytree(i_sim.architecture.design_path, i_sim.tmp_dir, dirs_exist_ok = True)
        except:
          printc.error("Could not copy \"" + i_sim.architecture.design_path + "\" into work directory \"" + i_sim.tmp_dir + "\"", script_name)
          printc.note("make sure there are no file or folder named identically in the two directories", script_name)
          continue

      # copy rtl (if exists) 
      if not i_sim.architecture.generate_rtl:
        copytree(i_sim.architecture.rtl_path, i_sim.tmp_dir + '/' + 'rtl', dirs_exist_ok = True)

      # replace parameters
      if i_sim.architecture.use_parameters:
        #printc.subheader("Replace parameters")
        param_target_file = i_sim.tmp_dir + '/' + i_sim.architecture.param_target_filename
        param_filename = arch_path + '/' + i_sim.architecture.arch_name + '.txt'
        replace_params(
          base_text_file=param_target_file, 
          replacement_text_file=param_filename, 
          output_file=param_target_file, 
          start_delimiter=i_sim.architecture.start_delimiter, 
          stop_delimiter=i_sim.architecture.stop_delimiter, 
          replace_all_occurrences=False,
          silent=True
        )
        #print()

      # run generate command
      if i_sim.architecture.generate_rtl:
        try:
          print()
          printc.subheader("Run generate command for " + i_sim.architecture.arch_display_name)
          printc.bold(" > " + i_sim.architecture.generate_command)
          result = subprocess.run([i_sim.architecture.generate_command], cwd=i_sim.tmp_dir, shell=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
          print()
          printc.error("rtl generation failed", script_name)
          printc.note("look for earlier error to solve this issue", script_name)
          print()
          continue

      # replace parameters again (override)
      if i_sim.override_parameters:
        #printc.subheader("Replace parameters")
        param_target_file = i_sim.tmp_dir + '/' + i_sim.override_param_target_filename
        param_file = i_sim.tmp_dir + '/' + i_sim.override_param_filename
        replace_params(
          base_text_file=param_target_file, 
          replacement_text_file=param_file, 
          output_file=param_target_file, 
          start_delimiter=i_sim.override_start_delimiter, 
          stop_delimiter=i_sim.override_stop_delimiter, 
          replace_all_occurrences=False,
          silent=True
        )

      # run simulation command
      sim_makefile_file = i_sim.tmp_dir + "/" + sim_makefile_filename
      command = "make " + sim_rule + " RTL_DIR=\"" + rtl_path + "\" ASTERISM_DIR=\"" + current_dir + "/.." + "\" --no-print-directory"
      #printc.subheader("Run simulation command for " + i_sim.sim_display_name)
      #printc.bold(" > " + command)
      process = run_parallel(
        command = command,
        nb_process = len(simulation_instances_chunk),
        show_log_if_one = show_log_if_one,
        directory = i_sim.tmp_dir
      )

      running_arch_list.append(
        Running_arch(
          process=process,
          target="",
          arch="",
          display_name=i_sim.sim_display_name,
          status_file="",
          progress_file="",
          tmp_dir=i_sim.tmp_dir
        )
      )
      printc.say("started job for simulation \"{}\" with pid {}".format(i_sim.sim_display_name, process.pid), script_name)

    show_progress(running_arch_list, refresh_time, show_log_if_one, mode="simulation")

######################################
# Main
######################################

def main(args, settings=None):

  # Get settings
  if settings is None:
    settings = AsterismSettings(args.config)
    if not settings.valid:
      sys.exit(-1)

  if args.input is not None:
    run_config_settings_filename  = args.input
  else:
    run_config_settings_filename = settings.simulation_settings_file

  if args.archpath is not None:
    arch_path = args.archpath
  else:
    arch_path = settings.arch_path

  if args.simpath is not None:
    sim_path = args.simpath
  else:
    sim_path = settings.sim_path

  if args.work is not None:
    work_path = args.work
  else:
    work_path = settings.sim_work_path

  overwrite = args.overwrite
  noask = args.noask

  run_simulations(run_config_settings_filename, arch_path, sim_path, work_path, overwrite, noask)

if __name__ == "__main__":
  args = parse_arguments()
  main(args)
