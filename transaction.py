from enum import Enum
import hashlib


class Tx:
    """A blockchain transaction.
    """

    def __init__(self, curr_tick, miner_id, tx_id, pointers):
        """
        Arguments:
            curr_tick {int} -- Current simulation tick.
            miner_id {int} -- Id of originating miner.
            tx_id {int} -- Transaction id (may be duplicate for reissued transaction).
        """

        self.origin = miner_id
        self.id = tx_id
        self.birthday = curr_tick
        self.pointers = pointers  # Backpointer(s) are an inherent part of the tx, each miner takes it or leaves it as a whole.
        self.history = []  # Event history.
        self.confidence_history = []  # Used for Iota. Reuses Event object but replaces state with int confidence [0-100]
        self.addEvent(curr_tick, miner_id, State.CREATED)
        self.stats = {}  # Filled in after simulation for data.
        str_to_hash = ''.join(self.pointers)+str(self.id)+str(self.birthday)+str(self.origin)  # Don't include mutable properties like history.
        self.hash = hashlib.md5(str_to_hash).hexdigest()

    def addEvent(self, time_stamp, miner_id, state):
        """Add event to transaction history.

        Arguments:
            time_stamp {int} -- Tick that event happened on.
            miner_id {int} -- Id of miner with new state for this transaction.
            state {State} -- New state that the miner entered into for this transaction.
        """

        self.history.append(Event(time_stamp, miner_id, state))

    def __str__(self):
        """        
        Returns:
            str -- String representation of transaction.
        """

        return "%d %d %d %s" % (self.id, self.origin, self.birthday, self.pointers)


class Event:
    """Event marking a change in state of a miner for a given transaction.
    """

    def __init__(self, time_stamp, miner_id, state):
        """Event in transaction history.

        Arguments:
            time_stamp {int} -- Tick that event happened on.
            miner_id {int} -- Id of miner with new state for this transaction.
            state {State} -- New state that the miner entered into for this transaction.
        """

        self.time_stamp = time_stamp
        self.miner_id = miner_id
        self.state = state


class State(Enum):
    """Enumeration of transaction states.
    """

    CREATED = 0
    PRE_CONSENSUS = 1
    CONSENSUS = 2
    DISCONSENSED = 3
