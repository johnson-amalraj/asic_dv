// --------------------------
// master bfm
// --------------------------
task master_bfm;
  bit m_stable_clk_cnt_i; // Variable for stable clock count

    master_state       = RESET_STATE;
    p_master_state     = RESET_STATE;
    m_stable_clk_cnt_i = `LOW;

    forever begin // bfm start
      @ (posedge mst_vif.sys_clk); // bfm start while sys_clk was generating
 
      p_master_state = master_state; // always assign current state to previous state

      if (master_state != p_master_state) begin
        $display("\tMASTER BFM \tCurrent state = %0s",master_state);
      end

      if (mst_vif.rst_n == `LOW) begin // if rst_n was not released
        master_state = RESET_STATE; // move to RESET_STATE 
      end

      case (master_state)
          // --------------------------
          // RESET_STATE :: this is the reset state
          // --------------------------
          RESET_STATE : begin
                      if (mst_vif.rst_n == `HIGH) begin // if rst_n was released
                        #50ns; // wait for 50 ns before moving to next state
                        m_stable_clk_cnt_i = 0;
                        master_state       = INIT_0_STATE; // move to INIT_0_STATE
                      end
          end // RESET_STATE
          // --------------------------
          // INIT_0_STATE :: this is the init0 state
          // --------------------------
          INIT_0_STATE : begin
                       if (mst_vif.rst_n == `HIGH) begin // if rst_n was released
                         #50ns; // wait for 50 ns before moving to next state
                         m_stable_clk_cnt_i = 0;
                         master_state       = INIT_1_STATE; // move to INIT_1_STATE
                       end
          end // INIT_0_STATE
          // --------------------------
          // INIT_1_STATE :: this is the init1 state
          // --------------------------
          INIT_1_STATE : begin
                       if (mst_vif.rst_n == `HIGH) begin // if rst_n was released
                         #50ns; // wait for 50 ns before moving to next state
                         m_stable_clk_cnt_i = 0;
                         master_state       = POWER_UP_STATE; // move to POWER_UP_STATE 
                       end
          end // INIT_1_STATE
          // --------------------------
          // POWER_UP_STATE :: this is the power state
          // --------------------------
          POWER_UP_STATE : begin
                         #50ns; // wait for 50 ns before moving to next state
                         m_stable_clk_cnt_i = 0;
                         master_state       = STABLE_STATE; // move to STABLE_STATE 
                         clk_en_b           = 1'b1; // Enable the clock generation
          end // POWER_UP_STATE 
          // --------------------------
          // STABLE_STATE :: this is the stable state
          // --------------------------
          STABLE_STATE : begin
                       if (clk_en_b == `HIGH) begin // if clk_en_b was high 
                         if (m_stable_clk_cnt_i >= `STABLE_CLK_CNT) begin // if stable clock count was higher than STABLE_CLK_CNT 
                           master_state = CMD_STATE; // move to CMD_STATE 
                           #50ns; // wait for 50 ns before moving to next state
                         end
                         m_stable_clk_cnt_i = m_stable_clk_cnt_i + 1;
                       end
          end // STABLE_STATE 
          // --------------------------
          // CMD_STATE :: this is the command state
          // --------------------------
          CMD_STATE : begin
          end // CMD_STATE 
          // --------------------------
          // NOP_STATE :: this is the no operation state
          // --------------------------
          NOP_CMD_STATE : begin
          end // NOP_CMD_STATE 
          // --------------------------
          // WR_CMD_STATE :: this is the write command state
          // --------------------------
          WR_CMD_STATE : begin
          end // WR_CMD_STATE 
          // --------------------------
          // RD_CMD_STATE :: this is the read command state
          // --------------------------
          RD_CMD_STATE : begin
          end // RD_CMD_STATE 
          // --------------------------
          // DATA_STATE :: this is the data state
          // --------------------------
          DATA_STATE : begin
          end // DATA_STATE 
          // --------------------------
          // default state :: this is the default state
          // --------------------------
          default : begin
          end
      endcase
    end // bfm start forever loop

endtask
