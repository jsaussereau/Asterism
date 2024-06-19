# Welcome to Asterism!

Asterism is a toolbox designed to facilitate logical synthesis on various FPGA and ASIC tools such as Vivado and Design Compiler. 
It allows to easily find the maximum operating frequency of any digital architecture described with an HDL (VHDL, Verilog, SystemVerilog).

The primary feature of this framework lies in its capability to compare different architectural configurations using parameter files. 
With Asterism, users can effortlessly explore different architectural designs and evaluate their performance based on numerous metrics including Fmax, hardware resource utilization, power consumption, and more.

Asterism documentation can be found at [https://asterism.readthedocs.io/](https://asterism.readthedocs.io/)

## Key Features

- Synthesis: Easily conduct logical synthesis on diverse FPGA and ASIC tools for various targets.
- Fmax search: Find the maximum frequency of the design on a specific target.
- Architecture Comparison: Easily compare architectural configurations using parameters.
- Interactive Results Exploration: Visualize, compare, and explore architecture implementation results based on various metrics for each target.

## Supported EDA tools

| EDA Tool                 | Status              |
| :----------------------- | :------------------ |
| AMD Vivado               | ✔️ supported        |
| Synopsys Design Compiler | ✔️ supported        |
| Intel Quartus Prime      | 📅 planned          |

> [!NOTE]
> Please note that these tools are not included in Asterism and must be obtained separately.

## Installation

The detailed installation procedure can be found at the following link:
[https://asterism.readthedocs.io/en/latest/installation.html](https://asterism.readthedocs.io/en/latest/installation.html)

## Quick start guide

### Step 1: Choose the designs you want to implement
Uncomment the architectures you want to implement in `architecture_select.yml`

### Step 2: Choose your target device/technology
Select the target devide or technology in the yaml file corresponding to your EDA tool.

For Vivado the file is `target_vivado.yml`

### Step 3: Run the selected designs
For Vivado: 
```bash
make vivado
```
### Step 4: Visualize and explore the results
```bash
make explore
```

## Add your own design

### Step 1: Architecture folder
Create a folder named after your design in the `architectures` folder.

### Step 2: Setting file
- Add a `_settings.yml` in your newly created folder and fill it with the template bellow
```yaml
---
#rtl path, relative to "architectures" parent directory (Asterism root), not this directory
rtl_path: "examples/alu"

top_level_file: "alu_top.sv"
top_level_module: "alu_top"

clock_signal: "i_clk"

# copy a file into synthesis directory?
file_copy_enable: "false"
file_copy_source: "/dev/null"
file_copy_dest: "/dev/null"

# delimiters for parameter files
use_parameters: "true"
start_delimiter: "alu_top #("
stop_delimiter: ")("

# optionnal target-specific bounds (in MHz) to speed up fmax search
xc7s25-csga225-1:
  fmax_lower_bound: 100
  fmax_upper_bound: 450
xc7a100t-csg324-1:
  fmax_lower_bound: 150
  fmax_upper_bound: 450
xc7k70t-fbg676-2:
  fmax_lower_bound: 100
  fmax_upper_bound: 700
...
```
- Edit the file so it matches your design source files directory, top level filename, module name, and clock signal name.
- Set `start_delimiter` and `stop_delimiter` so it matches the delimiters of the parameter section in your top level source file.
- Add target-specific bounds for the binary search.
- A documentation of the keys for `_settings.yml` files can be found [here](https://github.com/jsaussereau/Asterism/tree/main/documentation#architecture-settings)

### Step 3: Parameter files
Add parameter files to the folder.
Parameter files should match the parameter section of your top-level source file with the desired values.

For instance, with the following Verilog module
```verilog
module alu_top #(
  parameter BITS = 8
)(
  input  wire            i_clk,
  input  wire            i_rst,
  input  wire      [4:0] i_sel_op,
  input  wire [BITS-1:0] i_op_a,
  input  wire [BITS-1:0] i_op_b,
  output wire [BITS-1:0] o_res
);
```
One of the parameter file could contain:
```verilog
  parameter BITS = 16
```
Another parameter file could contain:
```verilog
  parameter BITS = 32
```
You can create as many parameter files as you wish, with different parameter values.
There is no limit to the number of parameters in parameter files.
The only constraint is the strict correspondence between the contents of the parameter files and the parameter section of the top-level in terms of numbers and names.

## Contact

For any inquiries or support, feel free to contact me at jonathan.saussereau@ims-bordeaux.fr.

*Note: Asterism is under active development, and we appreciate your feedback and contributions to make it even more powerful and user-friendly.*
