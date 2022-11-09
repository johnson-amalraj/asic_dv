// ====================================================
/*
Project:     transactor
Engg Name:   johnson amalraj
File name:   defines.sv
Description: this is the defines file for transactor model
TODO :       Need to add the required defines
*/
// ====================================================
`define HIGH = 1;
`define LOW  = 0;

// Defines for FSM states
typedef enum {RESET_STATE, INIT_0_STATE, INIT_1_STATE, POWER_UP_STATE, STABLE_STATE, CMD_STATE, NOP_CMD_STATE, WR_CMD_STATE, RD_CMD_STATE, DATA_STATE} fsm_state; 
