FILES = region.sv sample.sv
FLAGS = -sverilog -debug -I -ntb_opts svp

run:	simv
	simv -l sim.log

simv:   ${FILES}
	vcs ${FLAGS} -l comp.log ${FILES}

waves:	${FILES}
	vcs -sverilog -RI -debug_all +cfgfile+default.cfg -l simv.log ${FILES}

switch:	simv_switch
	./simv_switch

simv_switch:   assoc_array_string.v
	vcs ${FLAGS} -l comp.log assoc_array_string.v -o simv_switch

waves:	${FILES}

DIR = $(shell basename `pwd`)

tar:	clean
	cd ..; \
	tar cvf ${DIR}.tar ${DIR}

clean:
	@rm -rf simv* csrc* *.log *.key core* .__solver* vcdplus.vpd
	@rm -rf  vera*.rc  .vera_debugger_rc.lock *~ .__snps* *.bck
