#//----------------------------------------------------------------------
#//   Copyright 2007-2011 Mentor Graphics Corporation
#//   Copyright 2007-2011 Cadence Design Systems, Inc.
#//   Copyright 2010-2011 Synopsys, Inc.
#//   Copyright 2019 Tuomas Poikela (tpoikela)
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

import cocotb
from cocotb.triggers import Timer, Event

from ..base.sv import sv
from ..base.uvm_event import UVMEvent
from ..base.uvm_queue import UVMQueue
from .uvm_sequence_item import UVMSequenceItem
from ..base.uvm_object_globals import *
from ..macros import uvm_fatal, uvm_warning
from ..base.uvm_pool import UVMPool
from ..dap import uvm_get_to_lock_dap
from ..base.uvm_recorder import UVMRecorder
from uvm.base.sv import wait

SEQ_ERR1_MSG = "neither the item's sequencer nor dedicated sequencer has been supplied to start item in "

#//------------------------------------------------------------------------------
#//
#// CLASS: uvm_sequence_base
#//
#// The uvm_sequence_base class provides the interfaces needed to create streams
#// of sequence items and/or other sequences.
#//
#// A sequence is executed by calling its <start> method, either directly
#// or invocation of any of the `uvm_do_* macros.
#//
#// Executing sequences via <start>:
#//
#// A sequence's <start> method has a ~parent_sequence~ argument that controls
#// whether <pre_do>, <mid_do>, and <post_do> are called *in the parent*
#// sequence. It also has a ~call_pre_post~ argument that controls whether its
#// <pre_body> and <post_body> methods are called.
#// In all cases, its <pre_start> and <post_start> methods are always called.
#//
#// When <start> is called directly, you can provide the appropriate arguments
#// according to your application.
#//
#// The sequence execution flow looks like this
#//
#// User code
#//
#//| sub_seq.randomize(...); // optional
#//| sub_seq.start(seqr, parent_seq, priority, call_pre_post)
#//|
#//
#// The following methods are called, in order
#//
#//|
#//|   sub_seq.pre_start()        (task)
#//|   sub_seq.pre_body()         (task)  if call_pre_post==1
#//|     parent_seq.pre_do(0)     (task)  if parent_sequence!=None
#//|     parent_seq.mid_do(this)  (func)  if parent_sequence!=None
#//|   sub_seq.body               (task)  YOUR STIMULUS CODE
#//|     parent_seq.post_do(this) (func)  if parent_sequence!=None
#//|   sub_seq.post_body()        (task)  if call_pre_post==1
#//|   sub_seq.post_start()       (task)
#//
#//
#// Executing sub-sequences via `uvm_do macros:
#//
#// A sequence can also be indirectly started as a child in the <body> of a
#// parent sequence. The child sequence's <start> method is called indirectly
#// by invoking any of the `uvm_do macros.
#// In these cases, <start> is called with
#// ~call_pre_post~ set to 0, preventing the started sequence's <pre_body> and
#// <post_body> methods from being called. During execution of the
#// child sequence, the parent's <pre_do>, <mid_do>, and <post_do> methods
#// are called.
#//
#// The sub-sequence execution flow looks like
#//
#// User code
#//
#//|
#//| `uvm_do_with_prior(seq_seq, { constraints }, priority)
#//|
#//
#// The following methods are called, in order
#//
#//|
#//|   sub_seq.pre_start()         (task)
#//|   parent_seq.pre_do(0)        (task)
#//|   parent_req.mid_do(sub_seq)  (func)
#//|     sub_seq.body()            (task)
#//|   parent_seq.post_do(sub_seq) (func)
#//|   sub_seq.post_start()        (task)
#//|
#//
#// Remember, it is the *parent* sequence's pre|mid|post_do that are called, not
#// the sequence being executed.
#//
#//
#// Executing sequence items via <start_item>/<finish_item> or `uvm_do macros:
#//
#// Items are started in the <body> of a parent sequence via calls to
#// <start_item>/<finish_item> or invocations of any of the `uvm_do
#// macros. The <pre_do>, <mid_do>, and <post_do> methods of the parent
#// sequence will be called as the item is executed.
#//
#// The sequence-item execution flow looks like
#//
#// User code
#//
#//| parent_seq.start_item(item, priority)
#//| item.randomize(...) [with {constraints}]
#//| parent_seq.finish_item(item)
#//|
#//| or
#//|
#//| `uvm_do_with_prior(item, constraints, priority)
#//|
#//
#// The following methods are called, in order
#//
#//|
#//|   sequencer.wait_for_grant(prior) (task) \ start_item  \
#//|   parent_seq.pre_do(1)            (task) /              \
#//|                                                      `uvm_do* macros
#//|   parent_seq.mid_do(item)         (func) \              /
#//|   sequencer.send_request(item)    (func)  \finish_item /
#//|   sequencer.wait_for_item_done()  (task)  /
#//|   parent_seq.post_do(item)        (func) /
#//
#// Attempting to execute a sequence via <start_item>/<finish_item>
#// will produce a run-time error.
#//------------------------------------------------------------------------------

#class uvm_sequence_base extends uvm_sequence_item
class UVMSequenceBase(UVMSequenceItem):

    #  // Variable: do_not_randomize
    #  //
    #  // If set, prevents the sequence from being randomized before being executed
    #  // by the `uvm_do*() and `uvm_rand_send*() macros,
    #  // or as a default sequence.
    #  //
    #  bit do_not_randomize


    #  static string type_name = "uvm_sequence_base"
    type_name = "uvm_sequence_base"

    #  // Function: new
    #  //
    #  // The constructor for uvm_sequence_base.
    #  //
    def __init__(self, name="uvm_sequence"):
        UVMSequenceItem.__init__(self, name)
        self.m_sequence_state = UVM_CREATED
        self.m_wait_for_grant_semaphore = 0
        self.m_init_phase_daps(1)
        self.m_next_transaction_id = 1
        self.m_priority = -1
        self.m_tr_recorder = None  # uvm_recorder
        #self.m_automatic_phase_objection_dap = None  # uvm_get_to_lock_dap#(bit)
        #self.m_starting_phase_dap = None  # uvm_get_to_lock_dap#(uvm_phase)
        # Each sequencer will assign a sequence id.  When a sequence is talking to multiple
        # sequencers, each sequence_id is managed separately
        self.m_sqr_seq_ids = UVMPool()
        self.children_array = {}  # bit[uvm_sequence_base]
        self.response_queue = UVMQueue()
        self.response_queue_depth = 8
        self.response_queue_error_report_disabled = False
        #  bits to detect if is_relevant()/wait_for_relevant() are implemented
        self.is_rel_default = False
        self.wait_rel_default = False
        self.m_sequence_process = None  # process
        self.m_use_response_handler = False
        #self.m_resp_queue_event = UVMEvent("resp_queue_event")
        self.m_resp_queue_event = Event("resp_queue_event")
        self.m_resp_queue_event.clear()
        self.m_events = {}
        self.m_events[UVM_FINISHED] = Event("UVM_FINISHED")

    #  // Function: is_item
    #  //
    #  // Returns 1 on items and 0 on sequences. As this object is a sequence,
    #  // ~is_item~ will always return 0.
    #  //
    #  virtual function bit is_item()
    #    return 0
    #  endfunction


    #  // Function: get_sequence_state
    #  //
    #  // Returns the sequence state as an enumerated value. Can use to wait on
    #  // the sequence reaching or changing from one or more states.
    #  //
    #  //| wait(get_sequence_state() & (UVM_STOPPED|UVM_FINISHED))
    #
    #  function uvm_sequence_state_enum get_sequence_state()
    #    return m_sequence_state
    #  endfunction

    #  // Task: wait_for_sequence_state
    #  //
    #  // Waits until the sequence reaches one of the given ~state~. If the sequence
    #  // is already in one of the state, this method returns immediately.
    #  //
    #  //| wait_for_sequence_state(UVM_STOPPED|UVM_FINISHED)
    #  task wait_for_sequence_state(int unsigned state_mask)
    @cocotb.coroutine
    def wait_for_sequence_state(self, state_mask):
        state = self.m_sequence_state & state_mask
        if state in self.m_events:
            yield self.m_events[state].wait()
        else:
            raise Exception("Cannot wait for state " + str(state)
                    + " - not implemented")

    #  // Function: get_tr_handle
    #  //
    #  // Returns the integral recording transaction handle for this sequence.
    #  // Can be used to associate sub-sequences and sequence items as
    #  // child transactions when calling <uvm_component::begin_child_tr>.
    #
    def get_tr_handle(self):
        if (self.m_tr_recorder is not None):
            return self.m_tr_recorder.get_handle()
        else:
            return 0
        #  endfunction

    #  //--------------------------
    #  // Group: Sequence Execution
    #  //--------------------------
    #
    #
    #  // Task: start
    #  //
    #  // Executes this sequence, returning when the sequence has completed.
    #  //
    #  // The ~sequencer~ argument specifies the sequencer on which to run this
    #  // sequence. The sequencer must be compatible with the sequence.
    #  //
    #  // If ~parent_sequence~ is ~None~, then this sequence is a root parent,
    #  // otherwise it is a child of ~parent_sequence~. The ~parent_sequence~'s
    #  // pre_do, mid_do, and post_do methods will be called during the execution
    #  // of this sequence.
    #  //
    #  // By default, the ~priority~ of a sequence
    #  // is the priority of its parent sequence.
    #  // If it is a root sequence, its default priority is 100.
    #  // A different priority may be specified by ~this_priority~.
    #  // Higher numbers indicate higher priority.
    #  //
    #  // If ~call_pre_post~ is set to 1 (default), then the <pre_body> and
    #  // <post_body> tasks will be called before and after the sequence
    #  // <body> is called.
    #
    #  virtual task start (uvm_sequencer_base sequencer,
    #                      uvm_sequence_base parent_sequence = None,
    #                      int this_priority = -1,
    #                      bit call_pre_post = 1)
    @cocotb.coroutine
    def start(self, sequencer, parent_sequence=None, this_priority=-1,
            call_pre_post=1):
        old_automatic_phase_objection = False
        self.set_item_context(parent_sequence, sequencer)

        if not(self.m_sequence_state in [UVM_CREATED,UVM_STOPPED,UVM_FINISHED]):
            uvm_fatal("SEQ_NOT_DONE",
                "Sequence " + self.get_full_name() + " already started")
        #end

        if self.m_parent_sequence is not None:
            self.m_parent_sequence.children_array[self] = 1

        if this_priority < -1:
            uvm_fatal("SEQPRI", sv.sformatf("Sequence %s start has illegal priority: %0d",
               self.get_full_name(), this_priority))

        if this_priority < 0:
            if parent_sequence is None:
                this_priority = 100
            else:
                this_priority = parent_sequence.get_priority()

        # Check that the response queue is empty from earlier runs
        self.clear_response_queue()
        self.m_priority = this_priority

        if self.m_sequencer is not None:
            handle = 0
            stream = None  # uvm_tr_stream stream
            if self.m_parent_sequence is None:
                stream = self.m_sequencer.get_tr_stream(self.get_name(), "Transactions")
                handle = self.m_sequencer.begin_tr(self, self.get_name())
                self.m_tr_recorder = UVMRecorder.get_recorder_from_handle(handle)
            else:
                stream = self.m_sequencer.get_tr_stream(self.get_root_sequence_name(), "Transactions")
                val = 0
                if self.m_parent_sequence.m_tr_recorder is not None:
                    val = self.m_parent_sequence.m_tr_recorder.get_handle()
                handle = self.m_sequencer.begin_child_tr(self, val, self.get_root_sequence_name())
                self.m_tr_recorder = UVMRecorder.get_recorder_from_handle(handle)

        # Ensure that the sequence_id is intialized in case this sequence has been stopped previously
        self.set_sequence_id(-1)
        # Remove all sqr_seq_ids
        self.m_sqr_seq_ids.delete()

        # Register the sequence with the sequencer if defined.
        if self.m_sequencer is not None:
            self.m_sequencer.m_register_sequence(self)

        # Change the state to PRE_START, do this before the fork so that
        # the "if (!(m_sequence_state inside {...}" works
        self.m_sequence_state = UVM_PRE_START

        self.m_sequence_process = cocotb.fork(self.start_process(parent_sequence, call_pre_post))
        yield self.m_sequence_process

        if self.m_sequencer is not None:
            self.m_sequencer.end_tr(self)

        # Clean up any sequencer queues after exiting; if we
        # were forcibly stoped, this step has already taken place
        if self.m_sequence_state != UVM_STOPPED:
            if self.m_sequencer is not None:
                self.m_sequencer.m_sequence_exiting(self)

        #0; // allow stopped and finish waiters to resume
        yield Timer(0)

        if (self.m_parent_sequence is not None and
                self in self.m_parent_sequence.children_array):
            del self.m_parent_sequence.children_array[self]

        old_automatic_phase_objection = self.get_automatic_phase_objection()
        self.m_init_phase_daps(1)
        self.set_automatic_phase_objection(old_automatic_phase_objection)
        #endtask

    @cocotb.coroutine
    def start_process(self, parent_sequence, call_pre_post):
        #fork
        #m_sequence_process = process::self()

        # absorb delta to ensure PRE_START was seen
        #0
        yield Timer(0)

        # Raise the objection if enabled
        # (This will lock the uvm_get_to_lock_dap)
        if self.get_automatic_phase_objection():
            self.m_safe_raise_starting_phase("automatic phase objection")

        self.pre_start()

        if call_pre_post == 1:
            self.m_sequence_state = UVM_PRE_BODY
            #0
            yield Timer(0)
            self.pre_body()

        if parent_sequence is not None:
            parent_sequence.pre_do(0)    # task
            parent_sequence.mid_do(self)  # function

        self.m_sequence_state = UVM_BODY
        #0
        yield Timer(0)
        yield self.body()

        self.m_sequence_state = UVM_ENDED
        #0
        yield Timer(0)

        if parent_sequence is not None:
            parent_sequence.post_do(self)

        if call_pre_post == 1:
            self.m_sequence_state = UVM_POST_BODY
            #0
            yield Timer(0)
            self.post_body()

        self.m_sequence_state = UVM_POST_START
        #0
        yield Timer(0)
        self.post_start()

        # Drop the objection if enabled
        if self.get_automatic_phase_objection():
            self.m_safe_drop_starting_phase("automatic phase objection")

        self.m_sequence_state = UVM_FINISHED
        self.m_events[UVM_FINISHED].set()
        #0
        yield Timer(0)
        #join


    #  // Task: pre_start
    #  //
    #  // This task is a user-definable callback that is called before the
    #  // optional execution of <pre_body>.
    #  // This method should not be called directly by the user.
    #
    #  virtual task pre_start()
    def pre_start(self):
        return

    #  // Task: pre_body
    #  //
    #  // This task is a user-definable callback that is called before the
    #  // execution of <body> ~only~ when the sequence is started with <start>.
    #  // If <start> is called with ~call_pre_post~ set to 0, ~pre_body~ is not
    #  // called.
    #  // This method should not be called directly by the user.
    #  virtual task pre_body()
    def pre_body(self):
        return

    #  // Task: pre_do
    #  //
    #  // This task is a user-definable callback task that is called ~on the
    #  // parent sequence~, if any
    #  // sequence has issued a wait_for_grant() call and after the sequencer has
    #  // selected this sequence, and before the item is randomized.
    #  //
    #  // Although pre_do is a task, consuming simulation cycles may result in
    #  // unexpected behavior on the driver.
    #  //
    #  // This method should not be called directly by the user.
    def pre_do(self, is_item):
        return

    #
    #
    #  // Function: mid_do
    #  //
    #  // This function is a user-definable callback function that is called after
    #  // the sequence item has been randomized, and just before the item is sent
    #  // to the driver.  This method should not be called directly by the user.
    #
    def mid_do(self, this_item):
        return

    #  // Task: body
    #  //
    #  // This is the user-defined task where the main sequence code resides.
    #  // This method should not be called directly by the user.
    #
    @cocotb.coroutine
    def body(self):
        uvm_warning("uvm_sequence_base", "Body definition undefined")
        yield Timer(0, "NS")

    #  // Function: post_do
    #  //
    #  // This function is a user-definable callback function that is called after
    #  // the driver has indicated that it has completed the item, using either
    #  // this item_done or put methods. This method should not be called directly
    #  // by the user.
    def post_do(self, this_item):
        return

    #  // Task: post_body
    #  //
    #  // This task is a user-definable callback task that is called after the
    #  // execution of <body> ~only~ when the sequence is started with <start>.
    #  // If <start> is called with ~call_pre_post~ set to 0, ~post_body~ is not
    #  // called.
    #  // This task is a user-definable callback task that is called after the
    #  // execution of the body, unless the sequence is started with call_pre_post=0.
    #  // This method should not be called directly by the user.
    def post_body(self):
        return

    #
    #  // Task: post_start
    #  //
    #  // This task is a user-definable callback that is called after the
    #  // optional execution of <post_body>.
    #  // This method should not be called directly by the user.
    def post_start(self):
        return

    #  // Group: Run-Time Phasing
    #  //
    #
    #  // Automatic Phase Objection DAP
    #  local uvm_get_to_lock_dap#(bit) m_automatic_phase_objection_dap
    #  // Starting Phase DAP
    #  local uvm_get_to_lock_dap#(uvm_phase) m_starting_phase_dap

    #  // Function- m_init_phase_daps
    #  // Either creates or renames DAPS
    def m_init_phase_daps(self, create):
        apo_name = sv.sformatf("%s.automatic_phase_objection", self.get_full_name())
        sp_name = sv.sformatf("%s.starting_phase", self.get_full_name())

        if create:
            self.m_automatic_phase_objection_dap = uvm_get_to_lock_dap.type_id.create(
                apo_name, self.get_sequencer())
            self.m_starting_phase_dap = uvm_get_to_lock_dap.type_id.create(sp_name,
                    self.get_sequencer())
        else:
            self.m_automatic_phase_objection_dap.set_name(apo_name)
            self.m_starting_phase_dap.set_name(sp_name)
    #
    #`ifndef UVM_NO_DEPRECATED
    # `define UVM_DEPRECATED_STARTING_PHASE
    #`endif
    #
    #`ifdef UVM_DEPRECATED_STARTING_PHASE
    #  // DEPRECATED!! Use get/set_starting_phase accessors instead!
    #  uvm_phase starting_phase
    #  // Value set via set_starting_phase
    #  uvm_phase m_set_starting_phase
    #  // Ensures we only warn once per sequence
    #  bit m_warn_deprecated_set
    #`endif
    #

    #  // Function: get_starting_phase
    #  // Returns the 'starting phase'.
    #  //
    #  // If non-~None~, the starting phase specifies the phase in which this
    #  // sequence was started.  The starting phase is set automatically when
    #  // this sequence is started as the default sequence on a sequencer.
    #  // See <uvm_sequencer_base::start_phase_sequence> for more information.
    #  //
    #  // Internally, the <uvm_sequence_base> uses an <uvm_get_to_lock_dap> to
    #  // protect the starting phase value from being modified
    #  // after the reference has been read.  Once the sequence has ended
    #  // its execution (either via natural termination, or being killed),
    #  // then the starting phase value can be modified again.
    #  //
    def get_starting_phase(self):
        return self.m_starting_phase_dap.get()

    #
    #  // Function: set_starting_phase
    #  // Sets the 'starting phase'.
    #  //
    #  // Internally, the <uvm_sequence_base> uses a <uvm_get_to_lock_dap> to
    #  // protect the starting phase value from being modified
    #  // after the reference has been read.  Once the sequence has ended
    #  // its execution (either via natural termination, or being killed),
    #  // then the starting phase value can be modified again.
    #  //
    def set_starting_phase(self, phase):
        self.m_starting_phase_dap.set(phase)

    #  // Function: set_automatic_phase_objection
    #  // Sets the 'automatically object to starting phase' bit.
    #  //
    #  // The most common interaction with the starting phase
    #  // within a sequence is to simply ~raise~ the phase's objection
    #  // prior to executing the sequence, and ~drop~ the objection
    #  // after ending the sequence (either naturally, or
    #  // via a call to <kill>). In order to
    #  // simplify this interaction for the user, the UVM
    #  // provides the ability to perform this functionality
    #  // automatically.
    #  //
    #  // For example:
    #  //| function my_sequence::new(string name="unnamed")
    #  //|   super.new(name)
    #  //|   set_automatic_phase_objection(1)
    #  //| endfunction : new
    #  //
    #  // From a timeline point of view, the automatic phase objection
    #  // looks like:
    #  //| start() is executed
    #  //|   --! Objection is raised !--
    #  //|   pre_start() is executed
    #  //|   pre_body() is optionally executed
    #  //|   body() is executed
    #  //|   post_body() is optionally executed
    #  //|   post_start() is executed
    #  //|   --! Objection is dropped !--
    #  //| start() unblocks
    #  //
    #  // This functionality can also be enabled in sequences
    #  // which were not written with UVM Run-Time Phasing in mind:
    #  //| my_legacy_seq_type seq = new("seq")
    #  //| seq.set_automatic_phase_objection(1)
    #  //| seq.start(my_sequencer)
    #  //
    #  // Internally, the <uvm_sequence_base> uses a <uvm_get_to_lock_dap> to
    #  // protect the ~automatic_phase_objection~ value from being modified
    #  // after the reference has been read.  Once the sequence has ended
    #  // its execution (either via natural termination, or being killed),
    #  // then the ~automatic_phase_objection~ value can be modified again.
    #  //
    #  // NEVER set the automatic phase objection bit to 1 if your sequence
    #  // runs with a forever loop inside of the body, as the objection will
    #  // never get dropped!
    def set_automatic_phase_objection(self, value):
        self.m_automatic_phase_objection_dap.set(value)

    #  // Function: get_automatic_phase_objection
    #  // Returns (and locks) the value of the 'automatically object to
    #  // starting phase' bit.
    #  //
    #  // If 1, then the sequence will automatically raise an objection
    #  // to the starting phase (if the starting phase is not ~None~) immediately
    #  // prior to <pre_start> being called.  The objection will be dropped
    #  // after <post_start> has executed, or <kill> has been called.
    #  //
    def get_automatic_phase_objection(self):
        return self.m_automatic_phase_objection_dap.get()

    #  // m_safe_raise_starting_phase
    #  function void m_safe_raise_starting_phase(string description = "",
    #                                            int count = 1)
    def m_safe_raise_starting_phase(self, description="", count=1):
        starting_phase = self.get_starting_phase()
        if (starting_phase is not None):
            starting_phase.raise_objection(self, description, count)

    #
    #  // m_safe_drop_starting_phase
    #  function void m_safe_drop_starting_phase(string description = "",
    #                                           int count = 1)
    def m_safe_drop_starting_phase(self, description="", count=1):
        starting_phase = self.get_starting_phase()
        if (starting_phase is not None):
            starting_phase.drop_objection(self, description, count)
        #  endfunction : m_safe_drop_starting_phase

    #  //------------------------
    #  // Group: Sequence Control
    #  //------------------------
    #
    #  // Function: set_priority
    #  //
    #  // The priority of a sequence may be changed at any point in time.  When the
    #  // priority of a sequence is changed, the new priority will be used by the
    #  // sequencer the next time that it arbitrates between sequences.
    #  //
    #  // The default priority value for a sequence is 100.  Higher values result
    #  // in higher priorities.
    def set_priority(self, value):
        self.m_priority = value

    #  // Function: get_priority
    #  //
    #  // This function returns the current priority of the sequence.
    #
    def get_priority(self):
        return self.m_priority

    #  // Function: is_relevant
    #  //
    #  // The default is_relevant implementation returns 1, indicating that the
    #  // sequence is always relevant.
    #  //
    #  // Users may choose to override with their own virtual function to indicate
    #  // to the sequencer that the sequence is not currently relevant after a
    #  // request has been made.
    #  //
    #  // When the sequencer arbitrates, it will call is_relevant on each requesting,
    #  // unblocked sequence to see if it is relevant. If a 0 is returned, then the
    #  // sequence will not be chosen.
    #  //
    #  // If all requesting sequences are not relevant, then the sequencer will call
    #  // wait_for_relevant on all sequences and re-arbitrate upon its return.
    #  //
    #  // Any sequence that implements is_relevant must also implement
    #  // wait_for_relevant so that the sequencer has a way to wait for a
    #  // sequence to become relevant.
    #
    def is_relevant(self):
        self.is_rel_default = True
        return 1

    #  // Task: wait_for_relevant
    #  //
    #  // This method is called by the sequencer when all available sequences are
    #  // not relevant.  When wait_for_relevant returns the sequencer attempt to
    #  // re-arbitrate.
    #  //
    #  // Returning from this call does not guarantee a sequence is relevant,
    #  // although that would be the ideal. The method provide some delay to
    #  // prevent an infinite loop.
    #  //
    #  // If a sequence defines is_relevant so that it is not always relevant (by
    #  // default, a sequence is always relevant), then the sequence must also supply
    #  // a wait_for_relevant method.
    #
    #  virtual task wait_for_relevant()
    #    event e
    #    wait_rel_default = 1
    #    if (is_rel_default != wait_rel_default)
    #      uvm_report_fatal("RELMSM",
    #        "is_relevant() was implemented without defining wait_for_relevant()", UVM_NONE)
    #    @e;  // this is intended to never return
    #  endtask

    #  // Task: lock
    #  //
    #  // Requests a lock on the specified sequencer. If sequencer is ~None~, the lock
    #  // will be requested on the current default sequencer.
    #  //
    #  // A lock request will be arbitrated the same as any other request.  A lock is
    #  // granted after all earlier requests are completed and no other locks or
    #  // grabs are blocking this sequence.
    #  //
    #  // The lock call will return when the lock has been granted.
    #
    #  task lock(uvm_sequencer_base sequencer = None)
    #    if (sequencer == None)
    #      sequencer = self.m_sequencer
    #
    #    if (sequencer == None)
    #      uvm_report_fatal("LOCKSEQR", "None self.m_sequencer reference", UVM_NONE)
    #
    #    sequencer.lock(this)
    #  endtask
    #
    #
    #  // Task: grab
    #  //
    #  // Requests a lock on the specified sequencer.  If no argument is supplied,
    #  // the lock will be requested on the current default sequencer.
    #  //
    #  // A grab request is put in front of the arbitration queue. It will be
    #  // arbitrated before any other requests. A grab is granted when no other grabs
    #  // or locks are blocking this sequence.
    #  //
    #  // The grab call will return when the grab has been granted.
    #
    #  task grab(uvm_sequencer_base sequencer = None)
    #    if (sequencer == None) begin
    #      if (self.m_sequencer == None) begin
    #        uvm_report_fatal("GRAB", "None self.m_sequencer reference", UVM_NONE)
    #      end
    #      self.m_sequencer.grab(this)
    #    end
    #    else begin
    #      sequencer.grab(this)
    #    end
    #  endtask
    #
    #
    #  // Function: unlock
    #  //
    #  // Removes any locks or grabs obtained by this sequence on the specified
    #  // sequencer. If sequencer is ~None~, then the unlock will be done on the
    #  // current default sequencer.
    #
    #  function void  unlock(uvm_sequencer_base sequencer = None)
    #    if (sequencer == None) begin
    #      if (self.m_sequencer == None) begin
    #        uvm_report_fatal("UNLOCK", "None self.m_sequencer reference", UVM_NONE)
    #      end
    #      self.m_sequencer.unlock(this)
    #    end else begin
    #      sequencer.unlock(this)
    #    end
    #  endfunction
    #
    #
    #  // Function: ungrab
    #  //
    #  // Removes any locks or grabs obtained by this sequence on the specified
    #  // sequencer. If sequencer is ~None~, then the unlock will be done on the
    #  // current default sequencer.
    #
    #  function void  ungrab(uvm_sequencer_base sequencer = None)
    #    unlock(sequencer)
    #  endfunction
    #
    #
    #  // Function: is_blocked
    #  //
    #  // Returns a bit indicating whether this sequence is currently prevented from
    #  // running due to another lock or grab. A 1 is returned if the sequence is
    #  // currently blocked. A 0 is returned if no lock or grab prevents this
    #  // sequence from executing. Note that even if a sequence is not blocked, it
    #  // is possible for another sequence to issue a lock or grab before this
    #  // sequence can issue a request.
    #
    #  function bit is_blocked()
    #    return self.m_sequencer.is_blocked(this)
    #  endfunction
    #
    #
    #  // Function: has_lock
    #  //
    #  // Returns 1 if this sequence has a lock, 0 otherwise.
    #  //
    #  // Note that even if this sequence has a lock, a child sequence may also have
    #  // a lock, in which case the sequence is still blocked from issuing
    #  // operations on the sequencer.
    #
    #  function bit has_lock()
    #    return self.m_sequencer.has_lock(this)
    #  endfunction
    #
    #
    #  // Function: kill
    #  //
    #  // This function will kill the sequence, and cause all current locks and
    #  // requests in the sequence's default sequencer to be removed. The sequence
    #  // state will change to UVM_STOPPED, and the post_body() and post_start() callback
    #  // methods will not be executed.
    #  //
    #  // If a sequence has issued locks, grabs, or requests on sequencers other than
    #  // the default sequencer, then care must be taken to unregister the sequence
    #  // with the other sequencer(s) using the sequencer unregister_sequence()
    #  // method.
    #
    #  function void kill()
    #    if (m_sequence_process is not None) begin
    #      // If we are not connected to a sequencer, then issue
    #      // kill locally.
    #      if (self.m_sequencer == None) begin
    #        m_kill()
    #        // We need to drop the objection if we raised it...
    #        if (get_automatic_phase_objection()) begin
    #           m_safe_drop_starting_phase("automatic phase objection")
    #        end
    #        return
    #      end
    #      // If we are attached to a sequencer, then the sequencer
    #      // will clear out queues, and then kill this sequence
    #      self.m_sequencer.kill_sequence(this)
    #      // We need to drop the objection if we raised it...
    #      if (get_automatic_phase_objection()) begin
    #         m_safe_drop_starting_phase("automatic phase objection")
    #      end
    #      return
    #    end
    #  endfunction
    #
    #
    #  // Function: do_kill
    #  //
    #  // This function is a user hook that is called whenever a sequence is
    #  // terminated by using either sequence.kill() or sequencer.stop_sequences()
    #  // (which effectively calls sequence.kill()).
    #
    #  virtual function void do_kill()
    #    return
    #  endfunction
    #
    #  function void m_kill()
    #    do_kill()
    #    foreach(children_array[i]) begin
    #       i.kill()
    #    end
    #    if (m_sequence_process is not None) begin
    #      m_sequence_process.kill
    #      m_sequence_process = None
    #    end
    #    m_sequence_state = UVM_STOPPED
    #    if ((self.m_parent_sequence is not None) && (self.m_parent_sequence.children_array.exists(this)))
    #      self.m_parent_sequence.children_array.delete(this)
    #  endfunction
    #
    #
    #  //-------------------------------
    #  // Group: Sequence Item Execution
    #  //-------------------------------
    #

    #  // Function: create_item
    #  //
    #  // Create_item will create and initialize a sequence_item or sequence
    #  // using the factory.  The sequence_item or sequence will be initialized
    #  // to communicate with the specified sequencer.
    #
    #  protected function uvm_sequence_item create_item(uvm_object_wrapper type_var,
    #                                                   uvm_sequencer_base l_sequencer, string name)
    def create_item(self, type_var, l_sequencer, name):
        from ..base.uvm_coreservice import UVMCoreService
        cs = UVMCoreService.get()
        factory = cs.get_factory()
        item = factory.create_object_by_type(type_var, self.get_full_name(), name)
        item.set_item_context(self, l_sequencer)
        return item
        #  endfunction

    #  // Function: start_item
    #  //
    #  // ~start_item~ and <finish_item> together will initiate operation of
    #  // a sequence item.  If the item has not already been
    #  // initialized using create_item, then it will be initialized here to use
    #  // the default sequencer specified by self.m_sequencer.  Randomization
    #  // may be done between start_item and finish_item to ensure late generation
    #  //
    #  virtual task start_item (uvm_sequence_item item,
    #                           int set_priority = -1,
    #                           uvm_sequencer_base sequencer=None)
    @cocotb.coroutine
    def start_item(self, item, set_priority=-1, sequencer=None):
        seq = None

        if item is None:
            uvm_fatal("NoneITM",
               "attempting to start a None item from sequence " + self. get_full_name())
            return

        #if($cast(seq, item)) begin
        #  uvm_report_fatal("SEQNOTITM",
        #     {"attempting to start a sequence using start_item() from sequence '",
        #      get_full_name(), "'. Use seq.start() instead."}, UVM_NONE)
        #  return
        #end
        seq = item

        if sequencer is None:
            sequencer = item.get_sequencer()

        if sequencer is None:
            sequencer = self.get_sequencer()

        if sequencer is None:
            uvm_fatal("SEQ", SEQ_ERR1_MSG + self.get_full_name())
            return

        item.set_item_context(self, sequencer)

        if (set_priority < 0):
            set_priority = self.get_priority()

        yield sequencer.wait_for_grant(self, set_priority)

        # TODO recording
        #if (sequencer.is_auto_item_recording_enabled()) begin
        #  void'(sequencer.begin_child_tr(item,
        #                                 (self.m_tr_recorder == None) ? 0 : self.m_tr_recorder.get_handle(),
        #                                 item.get_root_sequence_name(), "Transactions"))
        #end

        self.pre_do(1)

    #  // Function: finish_item
    #  //
    #  // finish_item, together with start_item together will initiate operation of
    #  // a sequence_item.  Finish_item must be called
    #  // after start_item with no delays or delta-cycles.  Randomization, or other
    #  // functions may be called between the start_item and finish_item calls.
    #  //
    #  virtual task finish_item (uvm_sequence_item item,
    #                            int set_priority = -1)
    @cocotb.coroutine
    def finish_item(self, item, set_priority=-1):
        sequencer = item.get_sequencer()

        if sequencer is None:
            uvm_fatal("STRITM", "sequence_item has None sequencer")

        self.mid_do(item)
        sequencer.send_request(self, item)
        yield sequencer.wait_for_item_done(self, -1)

        # tpoikela: commented out, otherwise item.end_event is not triggered
        # if sequencer.is_auto_item_recording_enabled():
        sequencer.end_tr(item)
        self.post_do(item)

    #  // Task: wait_for_grant
    #  //
    #  // This task issues a request to the current sequencer.  If item_priority is
    #  // not specified, then the current sequence priority will be used by the
    #  // arbiter. If a lock_request is made, then the sequencer will issue a lock
    #  // immediately before granting the sequence.  (Note that the lock may be
    #  // granted without the sequence being granted if is_relevant is not asserted).
    #  //
    #  // When this method returns, the sequencer has granted the sequence, and the
    #  // sequence must call send_request without inserting any simulation delay
    #  // other than delta cycles.  The driver is currently waiting for the next
    #  // item to be sent via the send_request call.
    #
    #  virtual task wait_for_grant(int item_priority = -1, bit lock_request = 0)
    #    if (self.m_sequencer == None) begin
    #      uvm_fatal("WAITGRANT", "None self.m_sequencer reference")
    #    end
    #    self.m_sequencer.wait_for_grant(this, item_priority, lock_request)
    #  endtask


    #  // Function: send_request
    #  //
    #  // The send_request function may only be called after a wait_for_grant call.
    #  // This call will send the request item to the sequencer, which will forward
    #  // it to the driver. If the rerandomize bit is set, the item will be
    #  // randomized before being sent to the driver.
    #
    #  virtual function void send_request(uvm_sequence_item request, bit rerandomize = 0)
    #    if (self.m_sequencer == None) begin
    #        uvm_report_fatal("SENDREQ", "None self.m_sequencer reference", UVM_NONE)
    #      end
    #    self.m_sequencer.send_request(this, request, rerandomize)
    #  endfunction


    #  // Task: wait_for_item_done
    #  //
    #  // A sequence may optionally call wait_for_item_done.  This task will block
    #  // until the driver calls item_done or put.  If no transaction_id parameter
    #  // is specified, then the call will return the next time that the driver calls
    #  // item_done or put.  If a specific transaction_id is specified, then the call
    #  // will return when the driver indicates completion of that specific item.
    #  //
    #  // Note that if a specific transaction_id has been specified, and the driver
    #  // has already issued an item_done or put for that transaction, then the call
    #  // will hang, having missed the earlier notification.
    #
    #
    #  virtual task wait_for_item_done(int transaction_id = -1)
    #    if (self.m_sequencer == None) begin
    #        uvm_report_fatal("WAITITEMDONE", "None self.m_sequencer reference", UVM_NONE)
    #      end
    #    self.m_sequencer.wait_for_item_done(this, transaction_id)
    #  endtask
    #
    #
    #
    #  // Group: Response API
    #  //--------------------
    #
    #  // Function: use_response_handler
    #  //
    #  // When called with enable set to 1, responses will be sent to the response
    #  // handler. Otherwise, responses must be retrieved using get_response.
    #  //
    #  // By default, responses from the driver are retrieved in the sequence by
    #  // calling get_response.
    #  //
    #  // An alternative method is for the sequencer to call the response_handler
    #  // function with each response.
    #
    #  function void use_response_handler(bit enable)
    #    m_use_response_handler = enable
    #  endfunction
    #

    #  // Function: get_use_response_handler
    #  //
    #  // Returns the state of the use_response_handler bit.
    #
    def get_use_response_handler(self):
        return self.m_use_response_handler

    #  // Function: response_handler
    #  //
    #  // When the use_response_handler bit is set to 1, this virtual task is called
    #  // by the sequencer for each response that arrives for this sequence.
    #
    #  virtual function void response_handler(uvm_sequence_item response)
    #    return
    #  endfunction
    #
    #
    #  // Function: set_response_queue_error_report_disabled
    #  //
    #  // By default, if the self.response_queue overflows, an error is reported. The
    #  // self.response_queue will overflow if more responses are sent to this sequence
    #  // from the driver than get_response calls are made. Setting value to 0
    #  // disables these errors, while setting it to 1 enables them.
    #
    def set_response_queue_error_report_disabled(self, value):
        self.response_queue_error_report_disabled = value

    #  // Function: get_response_queue_error_report_disabled
    #  //
    #  // When this bit is 0 (default value), error reports are generated when
    #  // the response queue overflows. When this bit is 1, no such error
    #  // reports are generated.
    #
    def get_response_queue_error_report_disabled(self):
        return self.response_queue_error_report_disabled

    #  // Function: set_response_queue_depth
    #  //
    #  // The default maximum depth of the response queue is 8. These method is used
    #  // to examine or change the maximum depth of the response queue.
    #  //
    #  // Setting the response_queue_depth to -1 indicates an arbitrarily deep
    #  // response queue.  No checking is done.
    #
    def set_response_queue_depth(self, value):
        self.response_queue_depth = value

    #  // Function: get_response_queue_depth
    #  //
    #  // Returns the current depth setting for the response queue.
    #
    def get_response_queue_depth(self):
        return self.response_queue_depth

    #  // Function: clear_response_queue
    #  //
    #  // Empties the response queue for this sequence.
    #
    def clear_response_queue(self):
        self.response_queue.delete()
        self.m_resp_queue_event.set()

    #  virtual function void put_base_response(input uvm_sequence_item response)
    def put_base_response(self, response):
        if ((self.response_queue_depth == -1) or
                (self.response_queue.size() < self.response_queue_depth)):
            self.response_queue.push_back(response)
            self.m_resp_queue_event.set()
            return
        if self.response_queue_error_report_disabled == 0:
            uvm_report_error(self.get_full_name(), "Response queue overflow, response was dropped", UVM_NONE)

    #  // Function- put_response
    #  //
    #  // Internal method.
    #  virtual function void put_response (uvm_sequence_item response_item)
    def put_response(self, response_item):
        self.put_base_response(response_item)

    #  // Function- get_base_response
    #  virtual task get_base_response(output uvm_sequence_item response, input int transaction_id = -1)
    @cocotb.coroutine
    def get_base_response(self, response, transaction_id=-1):
        queue_size = 0
        i = 0

        if self.response_queue.size() == 0:
            yield wait(lambda : self.response_queue.size() == 0,
                 self.m_resp_queue_event)

        if transaction_id == -1:
            resp_item = self.response_queue.pop_front()
            response.append(resp_item)
            return

        while True:
            queue_size = self.response_queue.size()
            for i in range(queue_size):
                if (self.response_queue[i].get_transaction_id() == transaction_id):
                    response.append(self.response_queue[i])
                    self.response_queue.delete(i)
                    self.m_resp_queue_event.set()
                    return
            #wait (self.response_queue.size() != queue_size)
            yield wait(lambda : self.response_queue.size() != queue_size,
                       self.m_resp_queue_event)
        #  endtask


    #  //------------------------
    #  // Group- Sequence Library DEPRECATED
    #  //------------------------
    #
    #`ifndef UVM_NO_DEPRECATED
    #
    #  // Variable- seq_kind
    #  //
    #  // Used as an identifier in constraints for a specific sequence type.
    #
    #  rand int unsigned seq_kind
    #
    #  // For user random selection. This excludes the exhaustive and
    #  // random sequences.
    #  constraint pick_sequence {
    #       (num_sequences() <= 2) || (seq_kind >= 2)
    #       (seq_kind <  num_sequences()) || (seq_kind == 0); }
    #
    #
    #  // Function- num_sequences
    #  //
    #  // Returns the number of sequences in the sequencer's sequence library.
    #
    #  function int num_sequences()
    #    if (self.m_sequencer == None)
    #      return 0
    #    return (self.m_sequencer.num_sequences())
    #  endfunction
    #
    #
    #
    #  // Function- get_seq_kind
    #  //
    #  // This function returns an int representing the sequence kind that has
    #  // been registerd with the sequencer.  The return value may be used with
    #  // the <get_sequence> or <do_sequence_kind> methods.
    #
    #  function int get_seq_kind(string type_name)
    #    `uvm_warning("UVM_DEPRECATED",$sformatf("%m deprecated."))
    #    if(self.m_sequencer is not None)
    #      return self.m_sequencer.get_seq_kind(type_name)
    #    else
    #      uvm_report_warning("NoneSQ", $sformatf("%0s sequencer is None.",
    #                                           get_type_name()), UVM_NONE)
    #  endfunction
    #
    #
    #  // Function- get_sequence
    #  //
    #  // This function returns a reference to a sequence specified by ~req_kind~,
    #  // which can be obtained using the <get_seq_kind> method.
    #
    #  function uvm_sequence_base get_sequence(int unsigned req_kind)
    #    uvm_sequence_base m_seq
    #    string m_seq_type
    #    uvm_coreservice_t cs = uvm_coreservice_t::get()
    #    uvm_factory factory=cs.get_factory()
    #    `uvm_warning("UVM_DEPRECATED",$sformatf("%m deprecated."))
    #    if (req_kind < 0 || req_kind >= self.m_sequencer.sequences.size()) begin
    #      uvm_report_error("SEQRNG",
    #        $sformatf("Kind arg '%0d' out of range. Need 0-%0d",
    #        req_kind, self.m_sequencer.sequences.size()-1), UVM_NONE)
    #    end
    #    m_seq_type = self.m_sequencer.sequences[req_kind]
    #    if (!$cast(m_seq, factory.create_object_by_name(m_seq_type, get_full_name(), m_seq_type))) begin
    #      uvm_report_fatal("FCTSEQ",
    #        $sformatf("Factory cannot produce a sequence of type %0s.",
    #        m_seq_type), UVM_NONE)
    #    end
    #    m_seq.set_use_sequence_info(1)
    #    return m_seq
    #  endfunction
    #
    #
    #  // Task- do_sequence_kind
    #  //
    #  // This task will start a sequence of kind specified by ~req_kind~,
    #  // which can be obtained using the <get_seq_kind> method.
    #
    #  task do_sequence_kind(int unsigned req_kind)
    #    string m_seq_type
    #    uvm_sequence_base m_seq
    #    uvm_coreservice_t cs = uvm_coreservice_t::get()
    #    uvm_factory factory=cs.get_factory()
    #    `uvm_warning("UVM_DEPRECATED",$sformatf("%m deprecated."))
    #    m_seq_type = self.m_sequencer.sequences[req_kind]
    #    if (!$cast(m_seq, factory.create_object_by_name(m_seq_type, get_full_name(), m_seq_type))) begin
    #      uvm_report_fatal("FCTSEQ",
    #        $sformatf("Factory cannot produce a sequence of type %0s.", m_seq_type), UVM_NONE)
    #    end
    #
    #    m_seq.set_item_context(this, self.m_sequencer)
    #
    #    if(!m_seq.randomize()) begin
    #      uvm_report_warning("RNDFLD", "Randomization failed in do_sequence_kind()")
    #    end
    #    m_seq.start(self.m_sequencer,this,get_priority(),0)
    #  endtask
    #
    #
    #  // Function- get_sequence_by_name
    #  //
    #  // Internal method.
    #
    #  function uvm_sequence_base get_sequence_by_name(string seq_name)
    #    uvm_sequence_base m_seq
    #    uvm_coreservice_t cs = uvm_coreservice_t::get()
    #    uvm_factory factory=cs.get_factory()
    #    `uvm_warning("UVM_DEPRECATED",$sformatf("%m deprecated."))
    #    if (!$cast(m_seq, factory.create_object_by_name(seq_name, get_full_name(), seq_name))) begin
    #      uvm_report_fatal("FCTSEQ",
    #        $sformatf("Factory cannot produce a sequence of type %0s.", seq_name), UVM_NONE)
    #    end
    #    m_seq.set_use_sequence_info(1)
    #    return m_seq
    #  endfunction
    #
    #
    #  // Task- create_and_start_sequence_by_name
    #  //
    #  // Internal method.
    #
    #  task create_and_start_sequence_by_name(string seq_name)
    #    uvm_sequence_base m_seq
    #    `uvm_warning("UVM_DEPRECATED",$sformatf("%m deprecated."))
    #    m_seq = get_sequence_by_name(seq_name)
    #    m_seq.start(self.m_sequencer, this, this.get_priority(), 0)
    #  endtask
    #
    #
    #`endif // UVM_NO_DEPRECATED
    #

    #  //----------------------
    #  // Misc Internal methods
    #  //----------------------
    #
    #  // m_get_sqr_sequence_id
    #  // ---------------------
    #  function int m_get_sqr_sequence_id(int sequencer_id, bit update_sequence_id)
    def m_get_sqr_sequence_id(self, sequencer_id, update_sequence_id):
        if self.m_sqr_seq_ids.exists(sequencer_id):
            if update_sequence_id == 1:
                self.set_sequence_id(self.m_sqr_seq_ids[sequencer_id])
            return self.m_sqr_seq_ids[sequencer_id]

        if update_sequence_id == 1:
            self.set_sequence_id(-1)
        return -1
        #  endfunction

    #  // m_set_sqr_sequence_id
    #  // ---------------------
    #  function void m_set_sqr_sequence_id(int sequencer_id, int sequence_id)
    def m_set_sqr_sequence_id(self, sequencer_id, sequence_id):
        self.m_sqr_seq_ids[sequencer_id] = sequence_id
        self.set_sequence_id(sequence_id)
#endclass
