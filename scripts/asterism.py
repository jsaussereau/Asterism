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
import sys
import yaml
import argparse

from settings import AsterismSettings
from motd import *
import run_simulations as run_sim
import run_fmax_synthesis as run_synth
import export_results as exp_res
import export_benchmark as exp_bench
import clean as cln

# Add local libs to path
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(current_dir, 'lib')
sys.path.append(lib_path)

from utils import *

######################################
# Settings
######################################

EXIT_SUCCESS = 0

prog = os.path.basename(sys.argv[0])
script_name = os.path.basename(__file__)

######################################
# Parse Arguments
######################################

class ArgParser:

  def add_nobanner(parser):
    parser.add_argument('-Q', '--nobanner', action='store_true', help='suppress printing of banner')

  def parse_arguments():
    formatter = AsterismHelpFormatter
    ArgParser.parser = argparse.ArgumentParser(
      conflict_handler="resolve", 
      formatter_class=formatter,
      add_help=False
    )
    ArgParser.parser.add_argument('-v', '--version', action='store_true', help='show version and exit')
    ArgParser.parser.add_argument('-h', '--help', action='store_true', help='show this help message and exit')
    #ArgParser.parser.add_argument('-s', '--settings', action='store_true', help='generate a asterism.yml settings file')
    args, remaining_args = ArgParser.parser.parse_known_args()

    # Parse other arguments
    subparsers = ArgParser.parser.add_subparsers(dest="command")
    
    # Define parser for the 'synth' command
    ArgParser.synth_parser = subparsers.add_parser("synth", help="run synthesis", formatter_class=formatter)
    run_synth.add_arguments(ArgParser.synth_parser)
    ArgParser.synth_parser.add_argument('-e', '--noexport', action='store_true', help='do not export results after synthesis')
    ArgParser.add_nobanner(ArgParser.synth_parser)

    # Define parser for the 'sim' command
    ArgParser.sim_parser = subparsers.add_parser("sim", help="run simulations", formatter_class=formatter)
    run_sim.add_arguments(ArgParser.sim_parser)
    ArgParser.add_nobanner(ArgParser.sim_parser)

    # Define parser for the 'results' command
    ArgParser.res_parser = subparsers.add_parser("results", help="export benchmark results", formatter_class=formatter)
    ArgParser.res_parser.add_argument('-i', '--input', default='work', help='Input path (default: work)')
    ArgParser.res_parser.add_argument('-o', '--output', default='results', help='Output path (default: results')
    ArgParser.res_parser.add_argument('-t', '--tool', default='vivado', help='eda tool in use (default: vivado)')
    ArgParser.res_parser.add_argument('-f', '--format', choices=['csv', 'yml', 'all'], default='yml',help='Output format: csv, yml, or all (default: yml)')
    ArgParser.res_parser.add_argument('-s', '--sim_file', default='log/sim.log', help='simulation log file (default: log/sim.log)')
    ArgParser.res_parser.add_argument('-u', '--use_benchmark', action='store_true', help='Use benchmark values in yaml file')
    ArgParser.res_parser.add_argument('-b', '--benchmark', choices=['dhrystone'], default='dhrystone', help='benchmark to parse (default: dhrystone)')
    ArgParser.res_parser.add_argument('-B', '--benchmark_file', default='results/benchmark.yml', help='Benchmark file (default: results/benchmark.yml')
    ArgParser.add_nobanner(ArgParser.res_parser)

    # Define parser for the 'res_benchmark' command
    ArgParser.bm_res_parser = subparsers.add_parser("res_benchmark", help="export benchmark results", formatter_class=formatter)
    exp_bench.add_arguments(ArgParser.bm_res_parser)
    ArgParser.add_nobanner(ArgParser.bm_res_parser)

    # Define parser for the 'res_synth' command
    ArgParser.exp_res_parser = subparsers.add_parser("res_synth", help="export synthesis results")
    exp_res.add_arguments(ArgParser.exp_res_parser)
    ArgParser.add_nobanner(ArgParser.exp_res_parser)

    # Define parser for the 'clean' command
    ArgParser.clean_parser = subparsers.add_parser("clean", help="clean directory", formatter_class=formatter)
    cln.add_arguments(ArgParser.clean_parser)
    ArgParser.add_nobanner(ArgParser.clean_parser)

    # Parse arguments
    return ArgParser.parser.parse_args()

  def help():
    full_header(description="Asterism - a FPGA/ASIC toolbox for design space exploration")
    printc.bold("Global:\n  ", printc.colors.CYAN, end="")
    ArgParser.parser.print_help()
    print()
    printc.bold("Synthesis:\n  ", printc.colors.CYAN, end="")
    ArgParser.synth_parser.print_help()
    print()
    printc.bold("Simulation:\n  ", printc.colors.CYAN, end="")
    ArgParser.sim_parser.print_help()
    print()
    printc.bold("Results:", printc.colors.CYAN)
    printc.cyan("- All Results:\n  ", end="")
    ArgParser.res_parser.print_help()
    print()
    printc.cyan("- Benchmark Results:\n  ", end="")
    print(ArgParser.bm_res_parser.format_usage(), end="")
    print("  run ", end="")
    printc.bold(prog + " res_benchmark -h", end="")
    print(" for more details")
    print()
    printc.cyan("- Synthesis Results:\n  ", end="")
    print(ArgParser.exp_res_parser.format_usage(), end="")
    print("  run ", end="")
    printc.bold(prog + " res_synth -h", end="")
    print(" for more details")
    print()
    printc.bold("Clean:\n  ", printc.colors.CYAN, end="")
    ArgParser.clean_parser.print_help()
    print()

class AsterismHelpFormatter(argparse.HelpFormatter):
  def __init__(self, prog):
    super().__init__(
      prog=prog,
      max_help_position=8
    )
    self._current_indent = 2

  def _format_action_invocation(self, action):
    parts = super()._format_action_invocation(action).split(", ")
    parts = [printc.colors.BOLD + part + printc.colors.ENDC for part in parts]
    return ", ".join(parts)

######################################
# Run functions
######################################

def run_simulations(args):
  success = True
  try:
    run_sim.main(args)
  except SystemExit as e:
    if e.code != EXIT_SUCCESS:
      success = False
  except Exception as e:
    printc.error(str(e), script_name=run_sim.script_name)
    success = False
  return success

def run_synthesis(args):
  success = True
  try:
    run_synth.main(args)
  except SystemExit as e:
    if e.code != EXIT_SUCCESS:
      success = False
  except Exception as e:
    printc.error(str(e), script_name=run_synth.script_name)
    success = False
  if success and not args.noexport:
    newargs = argparse.Namespace(
      tool = args.tool,
      format = exp_res.DEFAULT_FORMAT,
      use_benchmark = None,
      benchmark_file = None,
      work = args.work,
      respath = None,
      config = args.config,
    )
    print()
    export_results(newargs)
  return success

def export_benchmark(args):
  success = True
  try:
    exp_bench.main(args)
  except SystemExit as e:
    if e.code != EXIT_SUCCESS:
      success = False
  except Exception as e:
    printc.error(str(e))
    success = False

def export_results(args):
  success = True
  try:
    exp_res.main(args)
  except SystemExit as e:
    if e.code != EXIT_SUCCESS:
      success = False
  except Exception as e:
    printc.error(str(e), script_name=exp_res.script_name)
    success = False
  return success

def export_all_results(args):
  success = True
  try:
    if args.use_benchmark:
      exp_bench.export_benchmark(
        input=args.input + "/simulation",
        output=args.output + "/benchmark.yml",
        benchmark=args.benchmark,
        sim_file=args.sim_file
      )
    exp_res.export_results(
      input=args.input + '/' + args.tool,
      output=args.output,
      tool=args.tool,
      format=args.format,
      use_benchmark=args.use_benchmark, 
      benchmark_file=args.benchmark_file
    )
  except SystemExit as e:
    if e.code != EXIT_SUCCESS:
      success = False
  except Exception as e:
    printc.error(str(e), script_name=exp_bench.script_name)
    success = False
  return success

def clean(args):
  success = True
  try:
    cln.main(args)
  except SystemExit as e:
    if e.code != EXIT_SUCCESS:
      success = False
  except Exception as e:
    printc.error(str(e))
    success = False

######################################
# Main
######################################

def main(args):

  # Display the version if requested
  if args.version:
    print_version()
    sys.exit(0)

  # Display help if requested
  if args.help:
    ArgParser.help()
    sys.exit(0)

  # If no command is selected 
  if args.command is None:
    full_header()
    print("run ", end="")
    printc.bold(prog + " -h", end="")
    print(" to get a list of useful commands")
    sys.exit(0)

  # Display the banner
  if not args.nobanner:
    motd()
    print()
  
  # Dispatch the command to the appropriate function
  if args.command == "sim":
    success = run_simulations(args)
  elif args.command == "synth":
    success = run_synthesis(args)
  elif args.command == "results":
    success = export_all_results(args)
  elif args.command in "res_benchmark":
    success = export_benchmark(args)
  elif args.command in "res_synth":
    success = export_results(args)
  elif args.command in "clean":
    success = clean(args)

if __name__ == "__main__":
  args = ArgParser.parse_arguments()
  main(args)
