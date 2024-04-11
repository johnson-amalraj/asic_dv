# Seminar on VLSI Verification with System Veriolg

## Explanation about System Verilog (agenda.md)

## SystemVerilog Laboratory Exercises

## Table of Contents

- [List of Experiments](#list-of-experiments)
- [Course Outcome (for Laboratory)](#course-outcome-for-laboratory)
- [EDA Playground](#eda-playground)
- [Resources](#resources)
- [Directory Structure](#directory-structure)

### List of Experiments

| Sl.No. | Expreiement Details                                      | Github Link                                                                                      |
| ------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1      | Design a Testbench for 2x1 Mux Using Gates               | (https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/mux_2_1.sv)     |
| 2      | Implementation of a Mailbox by Allocating Memory         | (https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/mailbox_mem.sv) |
| 3      | Implementation and Testing of Semaphore for a Simple DUT | (https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/semaphore.sv)   |
| 4      | Implementation of Scoreboard for a Simple DUT            | (https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/scoreboard.sv)  |

### Course Outcome (for Laboratory)

After successful completion of the course, the students will be able to:

| Sl.No. | Course Outcome                                                     | Knowledge Level |
| ------ | ------------------------------------------------------------------ | --------------- |
| 1      | Design and verify various digital logic modules                    | K3              |
| 2      | Construct and implement mailbox by allocating memory               | K3              |
| 3      | Make use of Coverage & Assertion techniques for Verification of DUT| K3              |
| 4      | Create testbenches for digital device under test                   | K3              |
| 5      | Design a complete system model using System Verilog                | K3              |

### EDA Playground

Explore and simulate the provided SystemVerilog code using the Microchip EDA Playground:

[Microchip EDA Playground](https://www.edaplayground.com/confirmRegistration/3e021e16-904b-4c9e-a75a-af11e83d39fd)

For inquiries, contact: support@edaplayground.com

### Resources

- [EDA Playground](https://www.edaplayground.com)
- References:
  - [ChipVerify SystemVerilog Tutorial](https://www.chipverify.com/systemverilog/systemverilog-tutorial)
  - [Verification Guide SystemVerilog Tutorial](https://verificationguide.com/systemverilog/systemverilog-tutorial/)
  - [ASIC World SystemVerilog Tutorial](https://www.asic-world.com/systemverilog/tutorial.html)

## Directory Structure (9 directories, 64 files)

```tree
.
├── eda
│   ├── README.md
│   ├── default_rd_test.sv
│   ├── design.sv
│   ├── driver.sv
│   ├── env.sv
│   ├── generator.sv
│   ├── interface.sv
│   ├── random_test.sv
│   ├── tb_top.sv
│   ├── transaction.sv
│   └── wr_rd_test.sv
├── examples
│   ├── apb
│   │   ├── ARM_AMBA3_APB.pdf
│   │   ├── README.md
│   │   ├── apb_mem.sv
│   │   ├── driver.sv
│   │   ├── environment.sv
│   │   ├── generator.sv
│   │   ├── interface.sv
│   │   ├── ip_monitor.sv
│   │   ├── op_monitor.sv
│   │   ├── ref_model.sv
│   │   ├── run_do.sv
│   │   ├── scoreboard.sv
│   │   ├── tb_top.sv
│   │   ├── test.sv
│   │   └── transaction.sv
│   ├── axi
│   │   ├── LICENSE
│   │   ├── README.md
│   │   ├── axi_config_objs.svh
│   │   ├── axi_env.sv
│   │   ├── axi_interface.sv
│   │   ├── axi_m_driver.sv
│   │   ├── axi_m_monitor.sv
│   │   ├── axi_master.sv
│   │   ├── axi_package.svh
│   │   ├── axi_read_seq.sv
│   │   ├── axi_s_driver.sv
│   │   ├── axi_s_monitor.sv
│   │   ├── axi_scoreboard.sv
│   │   ├── axi_slave.sv
│   │   ├── axi_tb_top.sv
│   │   ├── axi_test.sv
│   │   ├── axi_transaction.sv
│   │   ├── axi_write_seq.sv
│   │   └── docs
│   │       ├── AMBA AXI4 Specification.pdf
│   │       └── AXI.png
│   └── burst
│       ├── README.md
│       ├── env.sv
│       ├── interface.sv
│       ├── mst_agnt.sv
│       ├── mst_drvr.sv
│       ├── slv_agnt.sv
│       ├── slv_drvr.sv
│       ├── test.sv
│       └── top.sv
└── labs
    ├── README.md
    ├── agenda.md
    ├── docs
    │   ├── ECE_jS1tDVE-48-50.pdf
    │   └── T1-System Verilog for Verification_ A Guide to Learning the Testbench Language Features.pdf
    ├── mailbox_mem.sv
    ├── mux_2_1.sv
    ├── scoreboard.sv
    └── semaphore.sv

```
