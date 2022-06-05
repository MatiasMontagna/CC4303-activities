class CongestionControl:
    def __init__(self, mss):
        if  not isinstance(mss,int):
            raise Exception("ERROR in CongestionControl, init(): mss must be an integer")

        self.possible_states = ["slow_start", "congestion_avoidance"]
        self.state = self.possible_states[0]
        self.first_timeout = True
        self.mss = mss
        self.cwnd = mss
        self.ssthresh = None

    def event_ack_received(self):
        '''Handles reception of ACKs according to current state'''
        if self.state == self.possible_states[0]:
            self.cwnd += self.mss
            if self.ssthresh == None:
                return

            elif self.cwnd >= self.ssthresh: 
                self.state = self.possible_states[1]
                self.first_timeout = True

        elif self.state == self.possible_states[1]:
            self.cwnd += self.mss/self.cwnd

    def event_timeout(self):
        '''Handles timeouts according to current state'''
        if self.state == self.possible_states[0] and self.first_timeout:
            self.ssthresh = self.cwnd/2
            self.cwnd = self.mss
            self.first_timeout = False

        elif self.state == self.possible_states[1]:
            self.state = self.possible_states[0]
            self.ssthresh = None

    def get_cwnd(self):
        return int(self.cwnd)
            
