# Seminar on VLSI Verification with System Verilog

## Table of Contents

- [Overview on System Verilog](#overview-on-system-verilog)
- [Simple Testbench explanation with EDA playground](#simple-testbench-explanation-with-eda-playground)
- [SystemVerilog Laboratory Exercises](#systemverilog-laboratory-exercises)
- [EDA Playground](#eda-playground)
- [Resources](#resources)
- [Directory Structure](#directory-structure)

### Overview on System Verilog 

- [Agenda](https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/agenda.md)

### Simple Testbench explanation with EDA playground 

- [EDA Playground](https://github.com/johnson-amalraj/asic_dv/tree/master/kcet_seminar_18_apr/eda)

### SystemVerilog Laboratory Exercises

- [Laboratory Exercises](https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs)

#### List of Experiments

| Sl.No. | Experiment Details                                       | Github Link                                                                                                      |
| ------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------                 |
| 1      | Design a Testbench for 2x1 Mux Using Gates               | [mux_2_1.sv](https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/mux_2_1.sv)         |
| 2      | Implementation of a Mailbox by Allocating Memory         | [mailbox_mem.sv](https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/mailbox_mem.sv) |
| 3      | Implementation and Testing of Semaphore for a Simple DUT | [semaphore.sv](https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/semaphore.sv)     |
| 4      | Implementation of Scoreboard for a Simple DUT            | [scoreboard.sv](https://github.com/johnson-amalraj/asic_dv/blob/master/kcet_seminar_18_apr/labs/scoreboard.sv)   |

#### Course Outcome (for Laboratory)

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

## Directory Structure (13 directories, 86 files)

```tree
.
├── README.md
├── agenda.md
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
├── labs
│   ├── docs
│   │   ├── ECE_jS1tDVE-48-50.pdf
│   │   └── T1-System Verilog for Verification_ A Guide to Learning the Testbench Language Features.pdf
│   ├── ex1_mux_2_1
│   │   ├── basic_test.sv
│   │   ├── design.sv
│   │   ├── driver.sv
│   │   ├── environment.sv
│   │   ├── ex1_mux_2_1.sv
│   │   ├── generator.sv
│   │   ├── interface.sv
│   │   ├── testbench.sv
│   │   └── transaction.sv
│   ├── ex2_mailbox
│   │   ├── mail.sv
│   │   └── mailbox_mem.sv
│   ├── ex3_semaphore
│   │   ├── sem.sv
│   │   └── semaphore.sv
│   └── ex4_scoreboard
│       ├── default_rd_test.sv
│       ├── design.sv
│       ├── driver.sv
│       ├── environment.sv
│       ├── ex4_scoreboard.sv
│       ├── generator.sv
│       ├── interface.sv
│       ├── monitor.sv
│       ├── random_test.sv
│       ├── scoreboard.sv
│       ├── testbench.sv
│       ├── transaction.sv
│       └── wr_rd_test.sv
└── tree.sv

```
