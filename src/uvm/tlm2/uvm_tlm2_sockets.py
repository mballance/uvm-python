#//----------------------------------------------------------------------
#// Copyright 2010-2011 Mentor Graphics Corporation
#// Copyright 2010 Synopsys, Inc.
#// Copyright 2010-2018 Cadence Design Systems, Inc.
#// Copyright 2015-2018 NVIDIA Corporation
#//   Copyright 2019-2020 Tuomas Poikela (tpoikela)
#//   All Rights Reserved Worldwide
#//
#//   Licensed under the Apache License, Version 2.0 (the
#//   "License"); you may not use this file except in
#//   compliance with the License.  You may obtain a copy of
#//   the License at
#//
#//       http://www.apache.org/licenses/LICENSE-2.0
#//
#//   Unless required by applicable law or agreed to in
#//   writing, software distributed under the License is
#//   distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
#//   CONDITIONS OF ANY KIND, either express or implied.  See
#//   the License for the specific language governing
#//   permissions and limitations under the License.
#//----------------------------------------------------------------------


#from uvm.base.uvm_tlm_b_initiator_socket_base import *
#from uvm.base.uvm_tlm_b_target_socket_base import *
#from uvm.base.uvm_tlm_nb_initiator_socket_base import *
#from uvm.base.uvm_tlm_nb_target_socket_base import *
#from uvm.base.uvm_tlm_b_passthrough_initiator_socket_base import *
#from uvm.base.uvm_tlm_b_passthrough_target_socket_base import *
#from uvm.base.uvm_tlm_nb_passthrough_initiator_socket_base import *
#from uvm.base.uvm_tlm_nb_passthrough_target_socket_base import *

from ..macros.uvm_message_defines import (uvm_error_context, uvm_error)
from .uvm_tlm2_sockets_base import (UVMTlmBInitiatorSocketBase,
    UVMTlmBTargetSocketBase)
from .uvm_tlm2_imps import (UVM_TLM_B_TRANSPORT_IMP)

#//----------------------------------------------------------------------
#// Title -- NODOCS -- TLM Sockets
#//
#// Each uvm_tlm_*_socket class is derived from a corresponding
#// uvm_tlm_*_socket_base class.  The base class contains most of the
#// implementation of the class, The derived classes (in this file)
#// contain the connection semantics.
#//
#// Sockets come in several flavors: Each socket is either an initiator or a
#// target, a pass-through or a terminator. Further, any particular socket
#// implements either the blocking interfaces or the nonblocking interfaces.
#// Terminator sockets are used on initiators and targets as well as
#// interconnect components as shown in the figure above. Pass-through
#//  sockets are used to enable connections to cross hierarchical boundaries.
#//
#// There are eight socket types: the cross of blocking and nonblocking,
#// pass-through and termination, target and initiator
#//
#// Sockets are specified based on what they are (IS-A)
#// and what they contains (HAS-A).
#// IS-A and HAS-A are types of object relationships.
#// IS-A refers to the inheritance relationship and
#//  HAS-A refers to the ownership relationship.
#// For example if you say D is a B that means that D is derived from base B.
#// If you say object A HAS-A B that means that B is a member of A.
#//----------------------------------------------------------------------
#
#
#//----------------------------------------------------------------------
#// Class -- NODOCS -- UVMTlmBInitiatorSocket
#//
#// IS-A forward port; has no backward path except via the payload
#// contents
#//----------------------------------------------------------------------
from uvm.tlm2.uvm_tlm2_sockets_base import UVMTlmBPassthroughInitiatorSocketBase,\
    UVMTlmBPassthroughTargetSocketBase, UVMTlmBTargetSocketBase,\
    UVMTlmBInitiatorSocketBase, UVMTlmNbInitiatorSocketBase,\
    UVMTlmNbPassthroughInitiatorSocketBase, UVMTlmNbPassthroughTargetSocketBase,\
    UVMTlmNbTargetSocketBase
from uvm.base.sv import cat
from uvm.macros.uvm_message_defines import uvm_error
from uvm.tlm2.uvm_tlm2_imps import UVM_TLM_NB_TRANSPORT_FW_IMP,\
    UVM_TLM_B_TRANSPORT_IMP, UVMTlmNbTransportBwImp
from uvm.tlm2.uvm_tlm2_ports import UVMTlmNbTransportBwPort

class UVMTlmBInitiatorSocket(UVMTlmBInitiatorSocketBase):

    #  // Function: new
    #  // Construct a new instance of this socket
    def __init__(self, name, parent):
        super().__init__(name, parent)
  
    #// Function: Connect
    #//
    #// Connect this socket to the specified <uvm_tlm_b_target_socket>
    def connect(self, provider):
        valid_providers = (UVMTlmBPassthroughInitiatorSocketBase, 
            UVMTlmBPassthroughTargetSocketBase, UVMTlmBTargetSocketBase)
        
        super().connect(provider)
       
        if not isinstance(provider, valid_providers):
            print("TODO: uvm_error_context")
#             c = self.get_comp();
#             uvm_error_context(self.get_type_name(),
#                           "type mismatch in connect -- connection cannot be completed", c)
            pass

#//----------------------------------------------------------------------
#// Class -- NODOCS -- uvm_tlm_b_target_socket
#//
#// IS-A forward imp; has no backward path except via the payload
#// contents.
#//
#// The component instantiating this socket must implement
#// a b_transport() method with the following signature
#//
#//|   task b_transport(T t, uvm_tlm_time delay);
#//
#//----------------------------------------------------------------------
class UVMTlmBTargetSocket(UVMTlmBTargetSocketBase):

    #// Function: new
    #// Construct a new instance of this socket
    #// ~imp~ is a reference to the class implementing the
    #// b_transport() method.
    #// If not specified, it is assume to be the same as ~parent~.
    def __init__(self, name, parent, imp = None):
        super().__init__(name, parent)
        self.m_imp = parent if imp == None else imp
        if (self.m_imp == None):
            uvm_error("UVM/TLM2/NOIMP", cat("b_target socket ", name,
                                     " has no implementation"));

    #// Function: Connect
    #//
    #// Connect this socket to the specified <uvm_tlm_b_initiator_socket>
    def connect(self, provider):
        super().connect(provider)

        c = self.get_comp();
        # TODO:
#         uvm_error_context(get_type_name(),
#             "You cannot call connect() on a target termination socket", c)

UVM_TLM_B_TRANSPORT_IMP('m_imp', UVMTlmBTargetSocket)

#//----------------------------------------------------------------------
#// Class -- NODOCS -- uvm_tlm_nb_initiator_socket
#//
#// IS-A forward port; HAS-A backward imp
#//
#// The component instantiating this socket must implement
#// a nb_transport_bw() method with the following signature
#//
#//|   function uvm_tlm_sync_e nb_transport_bw(T t, ref P p, input uvm_tlm_time delay);
#//
#//----------------------------------------------------------------------

class UVMTlmNbInitiatorSocket(UVMTlmNbInitiatorSocketBase):

    #// Function: new
    #// Construct a new instance of this socket
    #// ~imp~ is a reference to the class implementing the
    #// nb_transport_bw() method.
    #// If not specified, it is assume to be the same as ~parent~.
    def __init__(self, name, parent, imp=None):
        super().__init__(name, parent)
        
        if (imp is None):
            imp = parent
        else:
            uvm_error("UVM/TLM2/NOIMP", cat("nb_initiator socket ", name,
                                     " has no implementation"));
        self.bw_imp = UVMTlmNbTransportBwImp("bw_imp", imp)

    #// Function: Connect
    #//
    #// Connect this socket to the specified <uvm_tlm_nb_target_socket>
    def connect(self, provider):
        valid_providers = (UVMTlmNbPassthroughInitiatorSocketBase,
            UVMTlmNbPassthroughInitiatorSocketBase, UVMTlmNbPassthroughTargetSocketBase)
        
        super().connect(provider)

        if not isinstance(provider, valid_providers):
            # TODO:
#             uvm_error_context(self.get_type_name(),
#                 "type mismatch in connect -- connection cannot be completed", 
#                self.get_comp())
            pass


#
#//----------------------------------------------------------------------
#// Class -- NODOCS -- uvm_tlm_nb_target_socket
#//
#// IS-A forward imp; HAS-A backward port
#//
#// The component instantiating this socket must implement
#// a nb_transport_fw() method with the following signature
#//
#//|   function uvm_tlm_sync_e nb_transport_fw(T t, ref P p, input uvm_tlm_time delay);
#//
#//----------------------------------------------------------------------

class UVMTlmNbTargetSocket(UVMTlmNbTargetSocketBase):

    #// Function: new
    #// Construct a new instance of this socket
    #// ~imp~ is a reference to the class implementing the
    #// nb_transport_fw() method.
    #// If not specified, it is assume to be the same as ~parent~.
    def __init__(self, name, parent, imp=None):
        super().__init__(name, parent)
        self.m_imp = parent if imp is None else imp
        self.bw_port = UVMTlmNbTransportBwPort("bw_port", self.get_comp())
        
        if (self.m_imp is None):
            uvm_error("UVM/TLM2/NOIMP", cat("nb_target socket ", name,
                                     " has no implementation"))

    #// Function: connect
    #//
    #// Connect this socket to the specified <uvm_tlm_nb_initiator_socket>
    def connect(self, provider):
        super().connect(provider)
        # TODO:
        #uvm_error_context(self.get_type_name(),
        #    "You cannot call connect() on a target termination socket", 
        #    self.get_comp())

UVM_TLM_NB_TRANSPORT_FW_IMP('m_imp', UVMTlmNbTargetSocket)


#//----------------------------------------------------------------------
#// Class -- NODOCS -- uvm_tlm_b_passthrough_initiator_socket
#//
#// IS-A forward port;
#//----------------------------------------------------------------------
#
class UVMTlmBPassthroughInitiatorSocket(UVMTlmBPassthroughInitiatorSocketBase):

    def __init__(self, name, parent):
        super().__init__(name, parent)

    #// Function : connect
    #//
    #// Connect this socket to the specified <uvm_tlm_b_target_socket>
    def connect(self, provider):
        valid_providers=(UVMTlmBPassthroughInitiatorSocketBase,
            UVMTlmBPassthroughTargetSocketBase, UVMTlmBTargetSocketBase)

        super.connect(provider);

        if not isinstance(provider, valid_providers):
            # TODO:
#            uvm_error_context(get_type_name(), 
#                "type mismatch in connect -- connection cannot be completed", 
#                self.get_comp())
            pass

#//----------------------------------------------------------------------
#// Class: uvm_tlm_b_passthrough_target_socket
#//
#// IS-A forward export;
#//----------------------------------------------------------------------
class UVMTlmBPassthroughTargetSocket(UVMTlmBPassthroughTargetSocketBase):

    def __init__(self, name, parent):
        super().__init__(name, parent)
   
    #// Function : connect
    #//
    #// Connect this socket to the specified <uvm_tlm_b_initiator_socket>
    def connect(self, provider):
        valid_providers=(UVMTlmBPassthroughTargetSocketBase,
            UVMTlmBTargetSocketBase)

        super().connect(provider)
        
        if not isinstance(provider, valid_providers):
            # TODO:
#            uvm_error_context(self.get_type_name(),
#               "type mismatch in connect -- connection cannot be completed", 
#               self.get_comp())
            pass


#//----------------------------------------------------------------------
#// Class -- NODOCS -- uvm_tlm_nb_passthrough_initiator_socket
#//
#// IS-A forward port; HAS-A backward export
#//----------------------------------------------------------------------

class UVMTlmNbPassthroughInitiatorSocket(UVMTlmNbPassthroughInitiatorSocketBase):

    def __init__(self, name, parent):
        super().__init__(name, parent)


    #// Function : connect
    #//
    #// Connect this socket to the specified <uvm_tlm_nb_target_socket>
    def connect(self, provider):
        valid_providers=(UVMTlmNbPassthroughInitiatorSocketBase,
            UVMTlmNbPassthroughTargetSocketBase, UVMTlmNbTargetSocketBase)

        super().connect(provider)

        if not isinstance(provider, valid_providers):
            # TODO:
#             uvm_error_context(self.get_type_name(),
#                 "type mismatch in connect -- connection cannot be completed", 
#                 self.get_comp())
            pass

#//----------------------------------------------------------------------
#// Class -- NODOCS -- uvm_tlm_nb_passthrough_target_socket
#//
#// IS-A forward export; HAS-A backward port
#//----------------------------------------------------------------------

class UVMTlmNbPassthroughTargetSocket(UVMTlmNbPassthroughTargetSocketBase):

    def __init__(self, name, parent):
        super().__init__(name, parent)

    #// Function: connect
    #//
    #// Connect this socket to the specified <uvm_tlm_nb_initiator_socket>
    def connect(self, provider):
        valid_providers=(UVMTlmNbPassthroughTargetSocketBase,
            UVMTlmNbTargetSocketBase)

        super().connect(provider)
        
        if not isinstance(provider, valid_providers):
            # TODO:
#             uvm_error_context(self.get_type_name(),
#                 "type mismatch in connect -- connection cannot be completed", 
#                 self.get_comp())
            pass

#
#//----------------------------------------------------------------------
