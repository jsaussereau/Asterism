#
# Copyright(C) 2022 by Jonathan Saussereau. All rights reserved.
# 
# All source codes and documentation contain proprietary confidential
# information and are distributed under license. It may be used, copied
# and/or disclosed only pursuant to the terms of a valid license agreement
# with Jonathan Saussereau. This copyright must be retained at all times.
#
# Last edited: 2022/07/07 13:10
#

if {[catch {

    source scripts/settings.tcl

    ######################################
    # Create a local copy of source files
    ######################################
    exec /bin/sh -c "rm -rf $tmp_path/rtl"
    exec /bin/sh -c "mkdir -p $tmp_path/rtl"
    exec /bin/sh -c "rsync -av --exclude=\".*\" $rtl_path/* $tmp_path/rtl"

    ######################################
    # copy file (optionnaly)
    ######################################
    # get target 
    set f [open $target_file]
    set target [gets $f]
    close $f

    if {bool($file_copy_enable) == bool(true)} {
        if {[file exists $file_copy_source]} {
            exec /bin/sh -c "cp $file_copy_source $tmp_path/$file_copy_dest"
        } else {
            error "analyze_script.tcl: <bold><red>error: target specified in '$target_file' ($target) has no assiociated target config file in './config' <end>"
            exit_error
        }
    }

    ######################################
    # update top level parameters
    ######################################
    # add escape characters
    set start_delimiter [exec /bin/sh -c "echo \"$start_delimiter\" | sed 's|/|\\\\\\\\/|g'"]
    set stop_delimiter [exec /bin/sh -c "echo \"$stop_delimiter\" | sed 's|/|\\\\\\\\/|g'"]

    # get architecture
    set f [open $architecture_file]
    set architecture [gets $f]
    close $f

    if {bool($use_parameters) == bool(true)} {
        if {[file exists ./${arch_path}/$architecture.txt]} {
            # check if there is a match
            set return_code_start [exec /bin/sh -c "sed -n '/$start_delimiter/p' $tmp_path/rtl/$top_level_file"]
            if {$return_code_start == ""} {
                puts "<green>analyze_script.tcl<end>: <bold><red>error: could not find start delimiter '$start_delimiter' for parameters in top level, exiting <end>"
                puts "<green>analyze_script.tcl<end>: <cyan>note: make sure start/stop delimiters specified in the '_settings.yml' file of the architecture match the top level description in '$top_level_file'<end>"
                exit_error
            }
            set return_code_stop [exec /bin/sh -c "sed -n '/$stop_delimiter/p' $tmp_path/rtl/$top_level_file"]
            if {$return_code_stop == ""} {
                puts "<green>analyze_script.tcl<end>: <bold><red>error: could not find stop delimiter '$stop_delimiter' for parameters in top level, exiting <end>"
                puts "<green>analyze_script.tcl<end>: <cyan>note: make sure start/stop delimiters specified in the '_settings.yml' file of the architecture match the top level description in '$top_level_file'<end>"
                exit_error
            }

            # copy to top level file
            if {[catch {exec /bin/sh -c "sed -i '/$start_delimiter/,/$stop_delimiter/!b;//!d;/$stop_delimiter/e cat ./${arch_path}/$architecture.txt' $tmp_path/rtl/$top_level_file"} errmsg]} {
                puts "<green>analyze_script.tcl<end>: <bold><red>error: error while copy parameters to top level file, exiting <end>"
                puts "<green>analyze_script.tcl<end>: <cyan>note: you might use unsupported characters<end>"
                puts "<green>analyze_script.tcl<end>: tool says -> $errmsg <end>"
                exit_error
            }
        } else {
            #puts "analyze_script.tcl: <bold><yellow>warning: architecture specified in '$architecture_file' ($target) has no assiociated target config file in directory '${arch_path}', using default parameters <end>"
            puts "<green>analyze_script.tcl<end>: <bold><red>error: architecture specified in '$architecture_file' ($target) has no assiociated parameter file in directory '${arch_path}', exiting <end>"
            puts "<green>analyze_script.tcl<end>: <cyan>note: make sure the file '$architecture.txt' in '${arch_path}'<end>"
            exit_error
        }
    }

    ######################################
    # Read source files
    ######################################
    #set filenames [split [exec find $rtl_path/ -type f ( -name *.sv -o -name *.v )] \n]
    #set filenames [split [exec find $rtl_path/core $rtl_path/soc -type f -name *.sv ! -name soc_config.sv ] \n]
    set filenames [split [exec find $tmp_path/rtl/ -type f -name *$rtl_file_format] \n]

    #read_verilog $filenames
    if {[catch {read_verilog $filenames} errmsg]} {
        puts "<green>analyze_script.tcl<end>: <bold><red>error: failed reading source files, exiting<end>"
        puts "<green>analyze_script.tcl<end>: tool says -> $errmsg"
        exit_error
    }

} ]} {
    puts "<green>analyze_script.tcl<end>: <bold><red>error: unhandled tcl error, exiting<end>"
    puts "<green>analyze_script.tcl<end>: <cyan>note: if you did not edit the tcl script, this should not append, please report this with the information bellow<end>"
    puts "<green>analyze_script.tcl<end>: <cyan>tcl error detail:<red>"
    puts "$errorInfo"
    puts "<cyan>^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^<end>"
    exit_error
}