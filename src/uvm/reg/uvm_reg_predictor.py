#// -------------------------------------------------------------
#//    Copyright 2004-2009 Synopsys, Inc.
#//    Copyright 2010-2011 Mentor Graphics Corporation
#//    Copyright 2010-2011 Cadence Design Systems, Inc.
#//    Copyright 2019 Tuomas Poikela (tpoikela)
#//    All Rights Reserved Worldwide
#//
#//    Licensed under the Apache License, Version 2.0 (the
#//    "License"); you may not use this file except in
#//    compliance with the License.  You may obtain a copy of
#//    the License at
#//
#//        http://www.apache.org/licenses/LICENSE-2.0
#//
#//    Unless required by applicable law or agreed to in
#//    writing, software distributed under the License is
#//    distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
#//    CONDITIONS OF ANY KIND, either express or implied.  See
#//    the License for the specific language governing
#//    permissions and limitations under the License.
#// -------------------------------------------------------------
#//

from ..base.sv import sv
from ..base.uvm_component import UVMComponent
from ..base.uvm_pool import UVMPool
from ..base.uvm_globals import *
from ..tlm1 import UVMAnalysisImp, UVMAnalysisPort
from ..macros import uvm_component_utils, uvm_info, uvm_fatal, uvm_error
from .uvm_reg_model import *
from .uvm_reg_item import UVMRegItem, UVMRegBusOp
from .uvm_reg_indirect import UVMRegIndirectData

#//------------------------------------------------------------------------------
#// TITLE: Explicit Register Predictor
#//------------------------------------------------------------------------------
#//
#// The <uvm_reg_predictor> class defines a predictor component,
#// which is used to update the register model's mirror values
#// based on transactions explicitly observed on a physical bus.
#//------------------------------------------------------------------------------

#class uvm_predict_s
class UVMPredictS():
    #   bit addr[uvm_reg_addr_t]
    #   uvm_reg_item reg_item

    def __init__(self):
        self.addr = {}
        self.reg_item = None
    #endclass

#//------------------------------------------------------------------------------
#//
#// CLASS: uvm_reg_predictor
#//
#// Updates the register model mirror based on observed bus transactions
#//
#// This class converts observed bus transactions of type ~BUSTYPE~ to generic
#// registers transactions, determines the register being accessed based on the
#// bus address, then updates the register's mirror value with the observed bus
#// data, subject to the register's access mode. See <uvm_reg::predict> for details.
#//
#// Memories can be large, so their accesses are not predicted.
#//
#//------------------------------------------------------------------------------

#class uvm_reg_predictor #(type BUSTYPE=int) extends uvm_component
class UVMRegPredictor(UVMComponent):
    #
    #
    #  // Variable: bus_in
    #  //
    #  // Observed bus transactions of type ~BUSTYPE~ are received from this
    #  // port and processed.
    #  //
    #  // For each incoming transaction, the predictor will attempt to get the
    #  // register or memory handle corresponding to the observed bus address.
    #  //
    #  // If there is a match, the predictor calls the register or memory's
    #  // predict method, passing in the observed bus data. The register or
    #  // memory mirror will be updated with this data, subject to its configured
    #  // access behavior--RW, RO, WO, etc. The predictor will also convert the
    #  // bus transaction to a generic <uvm_reg_item> and send it out the
    #  // ~reg_ap~ analysis port.
    #  //
    #  // If the register is wider than the bus, the
    #  // predictor will collect the multiple bus transactions needed to
    #  // determine the value being read or written.
    #  //
    #  uvm_analysis_imp #(BUSTYPE, uvm_reg_predictor #(BUSTYPE)) bus_in

    #
    #
    #  // Variable: reg_ap
    #  //
    #  // Analysis output port that publishes <uvm_reg_item> transactions
    #  // converted from bus transactions received on ~bus_in~.
    #  uvm_analysis_port #(uvm_reg_item) reg_ap

    #
    #
    #  // Variable: map
    #  //
    #  // The map used to convert a bus address to the corresponding register
    #  // or memory handle. Must be configured before the run phase.
    #  //
    #  uvm_reg_map map

    #
    #
    #  // Variable: adapter
    #  //
    #  // The adapter used to convey the parameters of a bus operation in
    #  // terms of a canonical <UVMRegBusOp> datum.
    #  // The <uvm_reg_adapter> must be configured before the run phase.
    #  //
    #  uvm_reg_adapter adapter

    #
    #
    #  // Function: new
    #  //
    #  // Create a new instance of this type, giving it the optional ~name~
    #  // and ~parent~.
    #  //
    def __init__(self, name, parent):
        UVMComponent.__init__(self, name, parent)
        self.bus_in = UVMAnalysisImp("bus_in", self)
        self.reg_ap = UVMAnalysisPort("reg_ap", self)
        self.m_pending = UVMPool()  # uvm_predict_s [uvm_reg]
        self.adapter = None
        self.map = None

    #  // This method is documented in uvm_object
    #  static string type_name = ""
    type_name = ""

    #  virtual function string get_type_name()
    #    if (type_name == ""):
    #      BUSTYPE t
    #      t = BUSTYPE::type_id::create("t")
    #      type_name = {"uvm_reg_predictor #(", t.get_type_name(), ")"}
    #    end
    #    return type_name
    #  endfunction
    #

    #  // Function: pre_predict
    #  //
    #  // Override this method to change the value or re-direct the
    #  // target register
    #  //
    #  virtual function void pre_predict(uvm_reg_item rw)
    def pre_predict(self, rw):
        pass
        #  endfunction

    #  // Function- write
    #  //
    #  // not a user-level method. Do not call directly. See documentation
    #  // for the ~bus_in~ member.
    #  //
    #  virtual function void write(BUSTYPE tr)
    def write(self, tr):
        rg = None
        rw = UVMRegBusOp()
        if self.adapter is None:
            uvm_fatal("REG/WRITE/None","write: adapter handle is None")

        uvm_info("REG_PREDICTOR", "write(): Received " + tr.convert2string(),
            UVM_MEDIUM)
        # In case they forget to set byte_en
        rw.byte_en = -1
        rw = self.adapter.bus2reg(tr, rw)
        rg = self.map.get_reg_by_offset(rw.addr, (rw.kind == UVM_READ))

        # TODO: Add memory look-up and call <uvm_mem::XsampleX()>

        if rg is not None:
            print("OOO reg_predict 1")
            found = False
            reg_item = None  # uvm_reg_item
            local_map = None  # uvm_reg_map
            map_info = None  # uvm_reg_map_info
            predict_info = None  # uvm_predict_s
            ir = None  # uvm_reg

            if not self.m_pending.exists(rg):
                item = UVMRegItem()
                predict_info = UVMPredictS()
                item.element_kind = UVM_REG
                item.element      = rg
                item.path         = UVM_PREDICT
                item.map          = self.map
                item.kind         = rw.kind
                predict_info.reg_item = item
                self.m_pending[rg] = predict_info
            predict_info = self.m_pending[rg]
            reg_item = predict_info.reg_item

            if rw.addr in predict_info.addr:
                uvm_error("REG_PREDICT_COLLISION", "Collision detected for register '"
                        + rg.get_full_name() + "'")
                # TODO: what to do with subsequent collisions?
                self.m_pending.delete(rg)

            local_map = rg.get_local_map(self.map,"predictor::write()")
            map_info = local_map.get_reg_map_info(rg)
            # TODO how to solve this
            # ir=($cast(ireg, rg))?ireg.get_indirect_reg():rg
            ir = rg
            ireg = []  # uvm_reg_indirect_data
            if sv.cast(ireg, rg, UVMRegIndirectData):
                ireg = ireg[0]
                ir = ireg.get_indirect_reg()

            for i in range(len(map_info.addr)):
                if (rw.addr == map_info.addr[i]):
                    found = True
                    print("OOO reg_predict 2 found is True")
                    reg_item.value[0] |= rw.data << (i * self.map.get_n_bytes()*8)
                    predict_info.addr[rw.addr] = 1
                    if len(predict_info.addr) == len(map_info.addr):
                        print("OOO reg_predict 3 len matches OK")
                        # We've captured the entire abstract register transaction.
                        predict_kind = UVM_PREDICT_READ
                        if (reg_item.kind == UVM_WRITE):
                            predict_kind = UVM_PREDICT_WRITE

                        is_ok = False
                        if (reg_item.kind == UVM_READ and
                                local_map.get_check_on_read() and
                                reg_item.status != UVM_NOT_OK):
                            print("OOO reg_predict 3.1 calling rg.do_check")
                            is_ok = rg.do_check(ir.get_mirrored_value(), reg_item.value[0], local_map)

                        self.pre_predict(reg_item)

                        ir.XsampleX(reg_item.value[0], rw.byte_en,
                                    reg_item.kind == UVM_READ, local_map)

                        blk = rg.get_parent()  # uvm_reg_block 
                        blk.XsampleX(map_info.offset,
                                     reg_item.kind == UVM_READ,
                                     local_map)

                        rg.do_predict(reg_item, predict_kind, rw.byte_en)
                        if (reg_item.kind == UVM_WRITE):
                            uvm_info("REG_PREDICT", "Observed WRITE transaction to register "
                                     + ir.get_full_name() + ": value='h"
                                     + sv.sformatf("%0h",reg_item.value[0]) + " : updated value = 'h"
                                     + sv.sformatf("%0h",ir.get()), UVM_HIGH)
                        else:
                            uvm_info("REG_PREDICT", "Observed READ transaction to register "
                                     + ir.get_full_name() + ": value='h" +
                                     sv.sformatf("%0h", reg_item.value[0]),UVM_HIGH)
                        self.reg_ap.write(reg_item)
                        self.m_pending.delete(rg)
                    else:
                        print("OOO reg_predict 4 len DID NOT MATCH")
                    break

            if found is False:
                uvm_error("REG_PREDICT_INTERNAL", "Unexpected failed address lookup for register '"
                       + rg.get_full_name() + "'")
        else:
            uvm_info("REG_PREDICT_NOT_FOR_ME",
               "Observed transaction does not target a register: " +
                 sv.sformatf("%p",tr), UVM_FULL)
        #  endfunction


    #
    #
    #  // Function: check_phase
    #  //
    #  // Checks that no pending register transactions are still queued.
    #  virtual function void check_phase(uvm_phase phase)
    def check_phase(self, phase):
        q = []  # [$]
        UVMComponent.check_phase(self, phase)
        
        for l in self.m_pending.key_list():
            rg = l
            q.append(sv.sformatf("\n%s",rg.get_full_name()))
        
        if self.m_pending.num() > 0:
            uvm_error("PENDING REG ITEMS",
            	sv.sformatf(
                    "There are %0d incomplete register transactions still pending completion:%s",
                    self.m_pending.num(), UVM_STRING_QUEUE_STREAMING_PACK(q)))
        #  endfunction

    #
    #endclass
#uvm_component_param_utils(uvm_reg_predictor#(BUSTYPE))
uvm_component_utils(UVMRegPredictor)
