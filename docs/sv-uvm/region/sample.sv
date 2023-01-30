program sample;
   
   Region r;

   initial begin
      r = new();

  $display("\nSimpliest case - enter and exit");
 r.region_enter(Region::WAIT, 42);
  r.region_exit(42);

  $display("\nEnter, enter, exit, exit");
  r.region_enter(Region::WAIT, 43);
  r.region_enter(Region::WAIT, 44);
  r.region_exit(43);
  r.region_exit(44);
  
  $display("\nEnter, enter, exit, exit 2");
  r.region_enter(Region::WAIT, 33);
  r.region_enter(Region::WAIT, 34);
  r.region_exit(34);
  r.region_exit(33);

  $display("\nParallel 1");
  fork
  begin
    r.region_enter(Region::WAIT, 24);
    r.region_exit(24);
  end
  begin
    r.region_enter(Region::WAIT, 24);
    r.region_exit(24);
  end
  join

  $display("\nParallel 2 - delay A");
  fork
  begin
    r.region_enter(Region::WAIT, 24);
    #10;
    r.region_exit(24);
  end
  begin
    r.region_enter(Region::WAIT, 24);
    r.region_exit(24);
  end
  join

  $display("\nParallel 3 - delay B");
  fork
  begin
    r.region_enter(Region::WAIT, 24);
    r.region_exit(24);
  end
  begin
    r.region_enter(Region::WAIT, 24);
    #10;
    r.region_exit(24);
  end
  join

  $display("\nParallel 4 - delay A & B");
  fork
  begin
    r.region_enter(Region::WAIT, 24);
    #10;
    r.region_exit(24);
  end
  begin
    r.region_enter(Region::WAIT, 24);
    #10;
    r.region_exit(24);
  end
  join

  $display("\nEnd of test");
   end // initial begin
   
endprogram : sample


/*
Simpliest case - enter and exit

Enter, enter, exit, exit

Enter, enter, exit, exit 2

Parallel 1

Parallel 2 - delay A

Parallel 3 - delay B

Parallel 4 - delay A & B

End of test
*/
