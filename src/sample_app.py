#!/usr/bin/python

from btpeer import *

PEERNAME = "NAME"   # request a peer's canonical id
LISTPEERS = "LIST"
PLAYER_LIST="PLAY"
INSERTPEER = "JOIN"
MOVE = "MOVE"
FIRE = "FIRE"
OBSTACLE = "OBST"
PEERQUIT = "QUIT"
REPLY = "REPL"
ERROR = "ERRO"
GAME_START="GAME"

class SamplePeer(BTPeer):
    def __init__(self, maxpeers, serverport):
        BTPeer.__init__(self, maxpeers, serverport)
        handlers = {LISTPEERS : self.__handle_listpeers,INSERTPEER : self.__handle_insertpeer,PEERNAME: self.__handle_peername,PLAYER_LIST:self.__handle_playerlist,
                    MOVE: self.__handle_move,FIRE: self.__handle_fire,OBSTACLE: self.__handle_obstacle,PEERQUIT: self.__handle_quit,GAME_START: self.__handle_gamestart}
        for mt in handlers:
            self.addhandler(mt, handlers[mt])
    
    def __debug(self, msg):
        if self.debug:
            btdebug(msg)
    
    #this function basically takes returns list of peers as of now to the user 
    def __handle_gamestart(self, peerconn, data):
        peer_list="128.237.243.181:22222"
        peerconn.senddata(PLAYER_LIST,'%s %s %d' % (peer_list,peer_list.split(":")[0],int(peer_list.split(":")[1])))
    
    def __handle_move(self,peerconn,data):
        print ""
    
    def __handle_fire(self,peerconn,data):
        print ""
    
    def __handle_obstacle(self,peerconn,data):
        print ""
        
    def __handle_quit(self,peerconn,data):
        print ""
    
    def __handle_playerlist(self,peerconn,data):
        """ Handles the INSERTPEER (join) message type. The message data
        should be a string of the form, "peerid  host  port", where peer-id
        is the canonical name of the peer that desires to be added to this
        peer's list of peers, host and port are the necessary data to connect
        to the peer.
    
        """
        self.peerlock.acquire()
        try:
            try:
                peerid,host,port = data.split()
        
                if self.maxpeersreached():
                    self.__debug('maxpeers %d reached: connection terminating' 
                          % self.maxpeers)
                    peerconn.senddata(ERROR, 'Join: too many peers')
                    return
        
                # peerid = '%s:%s' % (host,port)
                if peerid not in self.getpeerids() and peerid != self.myid:
                    self.addpeer(peerid, host, port)
                    self.__debug('added peer: %s' % peerid)
                    peerconn.senddata(REPLY, 'Join: peer added: %s' % peerid)
                else:
                    peerconn.senddata(ERROR, 'Join: peer already inserted %s'
                               % peerid)
            except:
                self.__debug('invalid insert %s: %s' % (str(peerconn), data))
                peerconn.senddata(ERROR, 'Join: incorrect arguments')
        finally:
            self.peerlock.release()
        print self.peers

    
    def __handle_insertpeer(self, peerconn, data):
    #--------------------------------------------------------------------------
        """ Handles the INSERTPEER (join) message type. The message data
        should be a string of the form, "peerid  host  port", where peer-id
        is the canonical name of the peer that desires to be added to this
        peer's list of peers, host and port are the necessary data to connect
        to the peer.
    
        """
        self.peerlock.acquire()
        try:
            try:
                peerid,host,port = data.split()
        
                if self.maxpeersreached():
                    self.__debug('maxpeers %d reached: connection terminating' 
                          % self.maxpeers)
                    peerconn.senddata(ERROR, 'Join: too many peers')
                    return
        
                # peerid = '%s:%s' % (host,port)
                if peerid not in self.getpeerids() and peerid != self.myid:
                    self.addpeer(peerid, host, port)
                    self.__debug('added peer: %s' % peerid)
                    peerconn.senddata(REPLY, 'Join: peer added: %s' % peerid)
                else:
                    peerconn.senddata(ERROR, 'Join: peer already inserted %s'
                               % peerid)
            except:
                self.__debug('invalid insert %s: %s' % (str(peerconn), data))
                peerconn.senddata(ERROR, 'Join: incorrect arguments')
        finally:
            self.peerlock.release()

    def __handle_listpeers(self, peerconn, data):
        #--------------------------------------------------------------------------
        """ Handles the LISTPEERS message type. Message data is not used. """
        self.peerlock.acquire()
        try:
            self.__debug('Listing peers %d' % self.numberofpeers())
            peerconn.senddata(REPLY, '%d' % self.numberofpeers())
            for pid in self.getpeerids():
                host,port = self.getpeer(pid)
                peerconn.senddata(REPLY, '%s %s %d' % (pid, host, port))
        finally:
            self.peerlock.release()
            
    #--------------------------------------------------------------------------
    def __handle_peername(self, peerconn, data):
        """ Handles the NAME message type. Message data is not used. """
        peerconn.senddata(REPLY, self.myid)
          
    def contactbootstrap(self,host,port):
        host,port = self.bootstrap.split(":")
        resp = self.connectandsend(host, port,"GAME"," ")
        self.__debug(str(resp))
        if (resp[0] != PLAYER_LIST):
            return
        data=resp[1]
        self.peerlock.acquire()
        try:
            try:
                peerid,host,port = data.split()
                # peerid = '%s:%s' % (host,port)
                if peerid not in self.getpeerids() and peerid != self.myid:
                    self.addpeer(peerid, host, port)
                    self.__debug('added peer: %s' % peerid)
                else:
                    print ('Join: peer already inserted %s' % peerid)
            except:
                self.__debug('invalid insert %s: %s' % (str(12345), data))
        finally:
            self.peerlock.release()
        print self.peers