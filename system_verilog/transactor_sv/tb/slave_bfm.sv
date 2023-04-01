// slave bfm
task slave_bfm;


  slave_state   = RESET_STATE;
  p_slave_state = RESET_STATE;

  while (slv_vif.sys_clk) begin // bfm start while sys_clk
 
    p_slave_state = slave_state;

    if (slave_state != p_slave_state) begin
      $display("\tSLAVE BFM \tCurrent state = %0s",slave_state);
    end

    case (slave_state)

        RESET_STATE : begin
          // This branch executes when <variable> = <value1>
          // wait(slv_vif.rst_n);
        end // RESET_STATE

        INIT_0_STATE : begin
          // This branch executes when <variable> = <value2>
        end // INIT_0_STATE

        INIT_1_STATE : begin
          // This branch executes when <variable> = <value2>
        end // INIT_0_STATE

        POWER_UP_STATE : begin
          // This branch executes when <variable> = <value2>
        end // POWER_UP_STATE 

        STABLE_STATE : begin
          // This branch executes when <variable> = <value2>
        end // STABLE_STATE 

        CMD_STATE : begin
          // This branch executes when <variable> = <value2>
        end // CMD_STATE 

        NOP_CMD_STATE : begin
          // This branch executes when <variable> = <value2>
        end // NOP_CMD_STATE 

        WR_CMD_STATE : begin
          // This branch executes when <variable> = <value2>
        end // WR_CMD_STATE 

        RD_CMD_STATE : begin
          // This branch executes when <variable> = <value2>
        end // RD_CMD_STATE 

        DATA_STATE : begin
          // This branch executes when <variable> = <value2>
        end // DATA_STATE 

        default : begin
          // This branch executes in all other cases
        end
    endcase

  end // bfm start while loop

endtask
