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

########################################################
# Paths
########################################################

SCRIPT_DIR              = ./scripts
WORK_DIR                = ./work
LOG_DIR                 = $(WORK_DIR)/log

########################################################
# Files
########################################################

EXPORT_SCRIPT           = $(SCRIPT_DIR)/export_results.py
EXPLORE_SCRIPT          = $(SCRIPT_DIR)/explore_results.py
RUN_SCRIPT              = $(SCRIPT_DIR)/run_config.py

########################################################
# Text formatting
########################################################

_BOLD                   =\x1b[1m
_END                    =\x1b[0m
_RED                    =\x1b[31m
_BLUE                   =\x1b[34m
_CYAN                   =\x1b[36m
_YELLOW                 =\x1b[33m
_GREEN                  =\x1b[32m
_WHITE                  =\x1b[37m
_BLACK                  =\x1b[30m

VIVADO_COLOR            = "s/INFO/$(_CYAN)INFO$(_END)/;s/WARNING/$(_YELLOW)WARNING$(_END)/;s/ERROR/$(_RED)$(_BOLD)ERROR$(_END)/;s/<green>/$(_GREEN)/;s/<red>/$(_RED)/;s/<yellow>/$(_YELLOW)/;s/<cyan>/$(_CYAN)/;s/<bold>/$(_BOLD)/;s/<end>/$(_END)/"

########################################################
# General rules
########################################################

.PHONY: help
help: motd
	@echo -e "SYNTHESIS"
	@echo -e "\t$(_BOLD)make vivado$(_END): run synthesis + place&route in Vivado"	
	@echo -e "\t$(_BOLD)make dc$(_END): run synthesis + place&route in Design Compiler"	
	@echo -e "DATA EXPORT"
	@echo -e "\t$(_BOLD)make results$(_END): export synthesis results"
	@echo -e "DATA EXPLORATION"
	@echo -e "\t$(_BOLD)make explore$(_END): explore results in a web app"
	@echo -e "OTHERS"
	@echo -e "\t$(_BOLD)make help$(_END): display a list of useful commands"

.PHONY: motd
motd:
	@echo -ne "$(_BOLD)"
	@echo "********************************************************************"
	@echo "*                             Asterism                             *"
	@echo "********************************************************************"
	@echo -ne "$(_END)"
	@echo ""

.PHONY: clean
clean:
	@rm -rf .Xil
	@rm -f *.jou
	@rm -f vivado*.log
	@rm -f tight_setup_hold_pins.txt

########################################################
# Vivado
########################################################

.PHONY: vivado
vivado: motd run_vivado_only clean results_vivado_only

.PHONY: run_vivado
run_vivado: motd run_vivado_only

.PHONY: run_vivado_only
run_vivado_only:
	@python3 $(SCRIPT_DIR)/run_config.py --tool vivado

.PHONY: results_vivado_only
results_vivado_only:
	@python3 ./$(SCRIPT_DIR)/export_results.py --tool vivado --benchmark


########################################################
# Design Compiler
########################################################

.PHONY: dc
dc: motd run_dc_only clean results_dc_only

.PHONY: run_dc
run_dc: motd run_dc_only

.PHONY: run_dc_only
run_dc_only:
	@python3 $(SCRIPT_DIR)/run_config.py --tool design_compiler

.PHONY: results_dc_only
results_dc_only:
	@python3 ./$(SCRIPT_DIR)/export_results.py --tool design_compiler --benchmark

########################################################
# Generic
########################################################

# export results 

.PHONY: results
results: motd results_only

.PHONY: results_only
results_only: results_vivado_only results_dc_only


# explore results

.PHONY: explore
explore: motd explore_only

.PHONY: explore_only
explore_only:
	@python3 ./$(SCRIPT_DIR)/result_explorer.py&
