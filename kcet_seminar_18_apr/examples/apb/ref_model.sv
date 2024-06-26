class ref_model #(parameter DEPTH = 5);
    mailbox #(transaction) ipmon2rm;
    mailbox #(transaction) rm2sb;

    const int ram_depth = 2**DEPTH;
    // Memory for 4KB RAM
    bit [31:0] ram_mem [];

    transaction trans, trans2sb;
    function new(mailbox #(transaction) ipmon2rm, mailbox #(transaction) rm2sb);
        this.ipmon2rm = ipmon2rm;
        this.rm2sb = rm2sb;

        trans = new;
        ram_mem = new[ram_depth];
    endfunction //new()
    
    task gen_op();
        if(trans.PRESETn == 0) begin
            foreach (ram_mem[i]) ram_mem[i] = 32'hffffffff;
            trans.PSLVERR = 0;
            //trans.PRDATA[0] = 32'b0;
            trans.PREADY = 0;
            return;
        end
        for(int i=0; i<trans.PADDR.size(); i++) begin
            if(trans.PADDR[i] >= ram_depth) begin
                trans.PSLVERR = 1;
                trans.PRDATA[i] = 32'b0;
                trans.PREADY = 1;
                continue;
            end

            if(trans.PWRITE == 1) begin
                if(trans.PWDATA[i] === 32'hx || trans.PWDATA[i] === 32'hz ) begin
                    trans.PRDATA[i] = 32'b0;
                    trans.PREADY = 1;
                    trans.PSLVERR = 1;
                    continue;
                end
                ram_mem [trans.PADDR[i]] = trans.PWDATA[i];
                trans.PRDATA[i] = 32'b0;
                trans.PREADY = 1;
                trans.PSLVERR = 0;
            end
            else begin
                if(ram_mem[trans.PADDR[i]] == 32'hffffffff) begin
                    trans.PRDATA[i] = 32'b0;
                    trans.PREADY = 1;
                    trans.PSLVERR = 1;
                    continue;
                end
                trans.PRDATA[i] = ram_mem [trans.PADDR[i]];
                trans.PREADY = 1;
                trans.PSLVERR = 0;
            end
                

        end
    endtask //gen_op

    task start();
        fork
            forever begin
                ipmon2rm.get(trans);
                gen_op();
                trans2sb = new trans;
                //trans2sb.printf("OUTPUT GENERATED BY RM");
                rm2sb.put(trans2sb);
            end
        join_none
    endtask //start
endclass //ref_model