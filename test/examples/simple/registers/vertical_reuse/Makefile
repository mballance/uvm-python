###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

# Makefile for testing python-uvm

# Usage:
# To execute tests in given file using given verilog source, you can do:
# >$ make MODULE=py_mod_name VLOG=hdl/my_vlog.v SIM_ARGS='-aaa +bbb'
#

TOPLEVEL_LANG ?= verilog
UVM_PYTHON ?= $(WPWD)/../../../../../src

PWD=$(shell pwd)

ifeq ($(OS),Msys)
WPWD=$(shell sh -c 'pwd -W')
PYTHONPATH := $(WPWD)/model:$(PYTHONPATH):.:../../../integrated
PYTHONPATH := $(UVM_PYTHON):$(UVM_PYTHON)/base:$(PYTHONPATH)
PYTHONPATH := $(WPWD)/../../../..:$(PYTHONPATH)
else
WPWD=$(shell pwd)
PYTHONPATH := $(WPWD)/model:$(PYTHONPATH):.:../../../integrated
PYTHONPATH := $(UVM_PYTHON):$(PYTHONPATH)
PYTHONPATH := $(WPWD)/../../../..:$(PYTHONPATH)
endif


ifeq ($(TOPLEVEL_LANG),verilog)
    ifeq ($(IMG),BLK)
        VERILOG_SOURCES ?= $(WPWD)/blk_dut.sv
    else
        VERILOG_SOURCES ?= $(WPWD)/sys_dut.sv
    endif
else
    $(error "A valid value (verilog) was not provided for TOPLEVEL_LANG=$(TOPLEVEL_LANG)")
endif


ifneq ($(VLOG),)
	VERILOG_SOURCES := $(VLOG)
endif

#PLUSARGS=+UVM_TESTNAME=ubus_example_base_test +UVM_CONFIG_DB_TRACE=1 +UVM_VERBOSITY=UVM_HIGH
#PLUSARGS=+UVM_TESTNAME=test_2m_4s +UVM_CONFIG_DB_TRACE=1 +UVM_VERBOSITY=UVM_HIGH
PLUSARGS=+UVM_CONFIG_DB_TRACE=1 +UVM_VERBOSITY=UVM_HIGH
ifneq ($(UVM_TEST),)
    PLUSARGS += +UVM_TESTNAME=$(UVM_TEST)
else
    PLUSARGS += +UVM_TESTNAME=sys_R_test 
endif

ifneq ($(SIMARGS),)
    PLUSARGS += $(SIMARGS)
endif

ifeq ($(IMG),BLK)
    TOPLEVEL := blk_dut
    MODULE   ?= blk_run
else
    TOPLEVEL := sys_dut
    MODULE   ?= sys_run
endif

ifeq ($(SIM),$(filter $(SIM),ius xcelium))
    EXTRA_ARGS=-gpg "PBASE_ADDR => 'h100"
else
    EXTRA_ARGS="-PBASE_ADDR='h100"
endif

include $(shell cocotb-config --makefiles)/Makefile.inc
include $(shell cocotb-config --makefiles)/Makefile.sim
