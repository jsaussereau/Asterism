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

if {[catch {

    source scripts/settings.tcl

    puts "<green>analyze_script.tcl<end>: <cyan>note: you can safely ignore the error message (UID-4) below.<end>"

    if {[catch {
        source scripts/synopsys_dc_setup.tcl
    } errmsg]} {
        puts "<green>analyze_script.tcl<end>: <bold><red>error: could not source 'synopsys_dc_setup.tcl'<end>"
        puts "<green>analyze_script.tcl<end>: <cyan>note: design compiler needs a technology file, make sure you added one in 'target_design_compiler.yml'<end>"
        exit -1
    }

    ######################################
    # Read source files
    ######################################
    suppress_message { AUTOREAD-303 AUTOREAD-107 AUTOREAD-105 AUTOREAD-102 AUTOREAD-100 VER-26 }

    # read verilog source files
    puts "\n<green>analyze_script.tcl<end>: reading verilog...<end>"
    if {![
        analyze -library WORK -f verilog -autoread -recursive $tmp_path/rtl/
    ]} {
        puts "<green>analyze_script.tcl<end>: <cyan>note: failed reading verilog source files<end>"
        set verilog_error 1
    }

    # read systemverilog source files
    puts "\n<green>analyze_script.tcl<end>: reading system verilog...<end>"
    if {![
        analyze -library WORK -f sverilog -autoread -recursive $tmp_path/rtl/
    ]} {
        puts "<green>analyze_script.tcl<end>: <cyan>note: failed reading systemverilog source files<end>"
        set sverilog_error 1
    }

    # read vhdl source files
    puts "\n<green>analyze_script.tcl<end>: reading vhdl verilog...<end>"
    if {![
        analyze -library WORK -f vhdl -autoread -recursive $tmp_path/rtl/
    ]} {
        puts "<green>analyze_script.tcl<end>: <cyan>note: failed reading vhdl source files<end>"
        if {$verilog_error == 1 && $sverilog_error == 1} {
            puts "<green>analyze_script.tcl<end>:<red>error: failed reading verilog, system verilog and vhdl source files, exiting"
            exit -1
        }
    }

} ]} {
    puts "<green>analyze_script.tcl<end>: <bold><red>error: unhandled tcl error, exiting<end>"
    puts "<green>analyze_script.tcl<end>: <cyan>note: if you did not edit the tcl script, this should not append, please report this with the information bellow<end>"
    puts "<green>analyze_script.tcl<end>: <cyan>tcl error detail:<red>"
    puts "$errorInfo"
    puts "<cyan>^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^<end>"
    exit -1
}