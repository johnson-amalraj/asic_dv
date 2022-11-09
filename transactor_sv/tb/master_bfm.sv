// master bfm
task master_bfm;


  master_state   = RESET_STATE;
  p_master_state = RESET_STATE;

  while (mst_vif.sys_clk) begin // bfm start while sys_clk
 
    p_master_state = master_state;

    if (master_state != p_master_state) begin
      $display("\tMASTER BFM \tCurrent state = %0s",master_state);
    end

    case (master_state)

        RESET_STATE : begin
          // This branch executes when <variable> = <value1>
          // wait(mst_vif.rst_n);
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
