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
import csv
import yaml
import argparse

# Add local libs to path
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(current_dir, 'lib')
sys.path.append(lib_path)

import printc

sys.path.append('eda_tools/vivado/parser')
sys.path.append('eda_tools/design_compiler/parser')

asic_functions = ['get_total_area', 'get_cell_area', 'get_comb_area', 'get_noncomb_area', 'get_buf_inv_area', 'get_macro_area', 'get_net_area', 'get_cell_count']
fpga_functions = ['get_slice_lut', 'get_slice_reg', 'get_bram', 'get_dsp']
misc_functions = ['get_fmax', 'get_dynamic_pow', 'get_static_pow']

from os.path import exists

######################################
# Settings
######################################

fieldnames_fpga = ['', 'architecture', 'variant', '', 'Fmax', '', 'LUTs', 'Regs', 'Tot Ut', '', 'DynP', 'StaP', 'TotP']
fieldnames_asic = ['', 'architecture', 'variant', '', 'Fmax', '', 'Cells', 'Area', 'Tot Area', '', 'DynP', 'StaP', 'TotP']

status_done = 'Done: 100%'

bad_value = ' /   '
format_mode = 'fpga'

script_name = os.path.basename(__file__)

######################################
# Misc functions
######################################

def corrupted_directory(target, variant):
  printc.warning(target + "/" + variant + " => synthesis has not finished or directory has been corrupted", script_name)

def safe_cast(val, to_type, default=None):
  try:
      return to_type(val)
  except (ValueError, TypeError):
      return default

def parse_arguments():
  parser = argparse.ArgumentParser(description='Process FPGA or ASIC results')
  parser.add_argument('-i', '--input', default='work',
                      help='Input path (default: work/<tool>)')
  parser.add_argument('-o', '--output', default='results',
                      help='Output path (default: results')
  #parser.add_argument('-m', '--mode', choices=['fpga', 'asic'], default='fpga',
  #                    help='Select the mode (fpga or asic, default: fpga)')
  parser.add_argument('-t', '--tool', choices=['vivado', 'design_compiler'], default='vivado',
                      help='eda tool in use (default: vivado)')
  parser.add_argument('-f', '--format', choices=['csv', 'yml', 'all'], default='yml',
                      help='Output format: csv, yml, or all (default: yml)')
  parser.add_argument('-b', '--benchmark', action='store_true',
                      help='Use benchmark values in yaml file')
  parser.add_argument('-B', '--benchmark_file', default='results/benchmark.yml',
                      help='Benchmark file (default: results/benchmark.yml')
  return parser.parse_args()

def import_result_parser(tool):
  try:
    if tool == 'vivado':
      import parse_vivado_results as selected_parser
    elif tool == 'design_compiler':
      import parse_design_compiler_results as selected_parser
    else:
      printc.error("the tool \"" + tool + "\" is not supported by this tool", script_name)
      sys.exit()
  except:
    printc.error("could not find a parser for tool \"" + tool + "\"", script_name)
    printc.note("check if the python parser \"eda_tools/" + tool + "/parser/parse_" + tool + "_results.py\" exists and is valid", script_name)
    sys.exit()
  return selected_parser

def check_parser(parser, format_mode, tool):
  function_to_test = misc_functions
  if format_mode == 'fpga':
    function_to_test.extend(fpga_functions)
  elif format_mode == 'asic':
    function_to_test.extend(asic_functions)

  for function in function_to_test:
    if not hasattr(parser, function):
        printc.error("function \"" + str(function) + "\" is not defined in parser lib \"parse_" + tool + "_results.py\"", script_name)
        sys.exit(1)

######################################
# Parsing functions
######################################

def get_dmips_per_mhz(architecture, variant, benchmark_data, benchmark_file):
  try:
    dmips_value = benchmark_data[architecture][variant]['dmips_per_MHz']
    return dmips_value
  except KeyError as e:
    #printc.error(f"could not find key in benchmark file: {e}", script_name)
    return None
  except Exception as e:
    printc.error("could not read benchmark file \"" + benchmark_file + " : " + str(e), script_name)
    return None

######################################
# Format functions
######################################

def cast_to_int(input):
  if input == bad_value:
    return '/'
  else:
    return safe_cast(input, int, 0)

def cast_to_float(input):
  if input == bad_value:
    return '/'
  else:
    return safe_cast(input, float, 0.0)

def write_to_yaml(args, output_file, parser, benchmark_data):
  yaml_data = {}

  for target in sorted(next(os.walk(args.input))[1]):
    yaml_data[target] = {}
    for arch in sorted(next(os.walk(os.path.join(args.input, target)))[1]):
      yaml_data[target][arch] = {}
      for variant in sorted(next(os.walk(os.path.join(args.input, target, arch)))[1]):
        cur_path = os.path.join(args.input, target, arch, variant)

        # Vérification de la complétion de la synthèse
        if not exists(os.path.join(cur_path, 'log/status.log')):
          corrupted_directory(target, arch+'/'+variant)
          continue

        with open(os.path.join(cur_path, 'log/status.log'), "r") as f:
          if not status_done in f.read():
            corrupted_directory(target, arch+'/'+variant)
            continue

        # Extraction des valeurs
        fmax = parser.get_fmax(cur_path)
        if format_mode == 'fpga':
          slice_lut = parser.get_slice_lut(cur_path)
          slice_reg = parser.get_slice_reg(cur_path)
          bram = parser.get_bram(cur_path)
          dsp = parser.get_dsp(cur_path)
          dynamic_pow = parser.get_dynamic_pow(cur_path)
          static_pow = parser.get_static_pow(cur_path)
          total_ut = safe_cast(slice_lut, int, 0) + safe_cast(slice_reg, int, 0)
          total_pow = safe_cast(static_pow, float, 0.0) + safe_cast(dynamic_pow, float, 0.0)

          yaml_data[target][arch][variant] = {
            'Fmax_MHz': cast_to_int(fmax),
            'LUT_count': cast_to_int(slice_lut),
            'Reg_count': cast_to_int(slice_reg),
            'BRAM_count': cast_to_int(bram),
            'DSP_count': cast_to_int(dsp),
            'Total_LUT_reg': cast_to_int(total_ut),
            'Dynamic_Power': cast_to_float(dynamic_pow),
            'Static_Power': cast_to_float(static_pow),
            'Total_Power': cast_to_float("%.3f" % total_pow)
          }

        elif format_mode == 'asic':
          total_area = parser.get_total_area(cur_path)
          cell_area = parser.get_cell_area(cur_path)
          comb_area = parser.get_comb_area(cur_path)
          noncomb_area = parser.get_noncomb_area(cur_path)
          buf_inv_area = parser.get_buf_inv_area(cur_path)
          macro_area = parser.get_macro_area(cur_path)
          net_area = parser.get_net_area(cur_path)
          cell_count = parser.get_cell_count(cur_path)

          yaml_data[target][arch][variant] = {
            'Fmax_MHz': cast_to_int(fmax),
            'Cell_count': cast_to_int(cell_count),
            'Total_area_um2': cast_to_float(total_area),
            'Cell_area_um2': cast_to_float(cell_area),
            'Comb_area_um2': cast_to_float(comb_area),
            'Non_comb_area_um2': cast_to_float(noncomb_area),
            'Buf_inv_area_um2': cast_to_float(buf_inv_area),
            'Macro_area_um2': cast_to_float(macro_area),
            'Net_area_um2': cast_to_float(net_area)
          }

        # benchmark
        if args.benchmark:
          dmips_per_mhz = get_dmips_per_mhz(arch, variant, benchmark_data, args.benchmark_file)
          if dmips_per_mhz != None:
            dmips = safe_cast(fmax, float, 0.0) * safe_cast(dmips_per_mhz, float, 0.0)

            yaml_data[target][arch][variant].update({
              'DMIPS_per_MHz': cast_to_float("%.3f" % dmips_per_mhz),
              'DMIPS': cast_to_float("%.2f" % dmips)
          })

  with open(output_file, 'w') as file:
    yaml.dump(yaml_data, file, default_flow_style=False, sort_keys=False)
    printc.say("Results written to \"" + output_file + "\"", script_name=script_name)

def write_to_csv(args, output_file, parser, fieldnames):
  with open(output_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter='\t')

    for target in sorted(next(os.walk(args.input))[1]):
      writer.writerow([])
      writer.writerow([target])
      for arch in sorted(next(os.walk(args.input+'/'+target))[1]):
        writer.writerow(fieldnames)
        for variant in sorted(next(os.walk(args.input+'/'+target+'/'+arch))[1]):
          cur_path=args.input+'/'+target+'/'+arch+'/'+variant

          # check if synthesis is complete
          if not exists(cur_path+'/log/status.log'):
            corrupted_directory(target, arch+'/'+variant)
          else:
            f = open(cur_path+'/log/status.log', "r")
            if not status_done in f.read():
              corrupted_directory(target, arch+'/'+variant)

          # get values
          fmax = parser.get_fmax(cur_path)        
          if format_mode == 'fpga':
            slice_lut = parser.get_slice_lut(cur_path)
            slice_reg = parser.get_slice_reg(cur_path)
            dynamic_pow = parser.get_dynamic_pow(cur_path)
            static_pow = parser.get_static_pow(cur_path)
            try:
              total_ut = int(slice_lut) + int(slice_reg)
            except:
              total_ut = ' /  '
            try:
              total_pow = '%.3f'%(float(static_pow) + float(dynamic_pow))
            except:
              total_pow = ' /  '
          elif format_mode == 'asic':
            area = parser.get_cell_area(cur_path)
            cell_count = parser.get_cell_count(cur_path)
          
          # write the line
          if format_mode == 'fpga':
            writer.writerow(['', arch, variant, '', fmax+'  ', '', slice_lut+' ', slice_reg+'  ', total_ut, '', dynamic_pow+' ', static_pow, total_pow])
          elif format_mode == 'asic':
            writer.writerow(['', arch, variant, '', fmax+'  ', '', cell_count, '            ', '' + area, '', '', '', ''])
        writer.writerow([])
  printc.say("Results written to \"" + output_file + "\"", script_name=script_name)

######################################
# Main
######################################

if __name__ == "__main__":
  args = parse_arguments()

  if args.tool == 'vivado':
    format_mode = 'fpga'
  elif args.tool == 'design_compiler':
    format_mode = 'asic'
  else:
    printc.error("unsupported tool (" + args.tool + " ) selected, please choose 'vivado' or 'design_compiler'", script_name)
    sys.exit(1)

  print(printc.colors.CYAN + "Export " +  args.tool + " results" + printc.colors.ENDC)

  parser = import_result_parser(args.tool)
  check_parser (parser, format_mode, args.tool)

  if format_mode == 'fpga':
    fieldnames = fieldnames_fpga
  elif format_mode == 'asic':
    fieldnames = fieldnames_asic
  else:
    printc.error("invalid format mode (" + format_mode + ") selected. Please choose 'fpga' or 'asic'", script_name)
    sys.exit(1)

  if not args.input.endswith(('/vivado', '/design_compiler')):
    args.input = args.input + "/" + args.tool

  if not os.path.isdir(args.input):
    printc.error("input directory \"" + args.input + "\" does not exist", script_name)
    sys.exit(1)

  benchmark_data = None
  if args.benchmark:
    if not exists(args.benchmark_file):
      args.benchmark = False
      printc.warning("cannot find benchmark file \"" + args.benchmark_file + "\", benchmark export disabled", script_name)
    else:
      with open(args.benchmark_file, 'r') as file:
        benchmark_data = yaml.safe_load(file)

  if args.format in ['csv', 'all']:
    csv_file = args.output + "/results_" + args.tool + ".csv"
    write_to_csv(args, csv_file, parser, fieldnames)

  if args.format in ['yml', 'all']:
    yaml_file = args.output + "/results_" + args.tool + ".yml"
    write_to_yaml(args, yaml_file, parser, benchmark_data)

  print()