#!/usr/bin/python
import socket
import struct
import threading
import time
import traceback


def btdebug( msg ):
    """ Prints a messsage to the screen with the name of the current thread """
    print "[%s] %s" % ( str(threading.currentThread().getName()), msg )


#==============================================================================
class Communicate:
    """ 
    Implements the core functionality that might be used by a peer in a
    P2P network.
    """

    #--------------------------------------------------------------------------
    def __init__( self, maxpeers=5, serverport=0, myid=None, serverhost = None ):
    #--------------------------------------------------------------------------
        self.debug = 0
        self.peers_list_lock = threading.RLock()  # ensure proper access to peers list (maybe better to use threading.RLock (reentrant))
        self.playernum_hostip_dict_lock= threading.RLock()
        self.leader_list_lock=threading.RLock()
        self.game_dict_lock = threading.RLock()
        
        if serverport!=0:
            self.game_dict={}
            self.available_maps_dict = {1:'maps/level2.tmx',2:'maps/level2.tmx',3:'maps/level2.tmx',4:'maps/level2.tmx'}
            self.gameid_map_dict ={}
            self.game_id=1
            self.playernum_hostip_dict ={}
            self.leader_list=[]
            
            self.peers = {}  # peerid ==> (host, port) mapping
            self.handlers = {}
            self.leader_num = 0
            self.play_start=False
            self.bootstrap = "128.237.210.73:12345"
            self.shutdown = False  # used to stop the main loop
            
            self.maxpeers = int(maxpeers)
            self.serverport = int(serverport)
            
            if serverhost: 
                self.serverhost = serverhost
            else: 
                self.__get_self_ip()
    
            if myid: 
                self.myid = myid
            else: 
                self.myid = '%s:%d' % (self.serverhost, self.serverport)
        else:
            self.player_tank_map ={
                                   '1':{'up':'tanks/1_up.png','down':'tanks/1_down.png','left':'tanks/1_left.png','right':'tanks/1_right.png'},
                                   '2':{'up':'tanks/2_up.png','down':'tanks/2_down.png','left':'tanks/2_left.png','right':'tanks/2_right.png'},
                                   '3':{'up':'tanks/3_up.png','down':'tanks/3_down.png','left':'tanks/3_left.png','right':'tanks/3_right.png'},
                                   '4':{'up':'tanks/4_up.png','down':'tanks/4_down.png','left':'tanks/4_left.png','right':'tanks/4_right.png'}
                                   }
        
                
    #--------------------------------------------------------------------------
    def __get_self_ip( self ):
    #--------------------------------------------------------------------------
        """ Attempt to connect to an Internet host in order to determine the
        local machine's IP address.
        """
        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        s.connect( ( "www.google.com", 80 ) )
        self.serverhost = s.getsockname()[0]
        s.close()

    #--------------------------------------------------------------------------
    def __debug( self, msg ):
    #--------------------------------------------------------------------------
        if self.debug:
            btdebug( msg )

    #--------------------------------------------------------------------------
    def __connection_handler( self, clientsock ):
    #--------------------------------------------------------------------------
        """
        Dispatches messages from the socket connection
        """
        host, port = clientsock.getpeername()
        peerconn = Handler_thread( None, host, port, clientsock, debug=False )
    
        try:
            msgtype, msgdata = peerconn.receive_data()
            if msgtype: 
                msgtype = msgtype.upper()
            if msgtype not in self.handlers:
                self.__debug( 'Not handled: %s: %s' % (msgtype, msgdata) )
            else:
                self.__debug( 'Handling peer msg: %s: %s' % (msgtype, msgdata) )
                self.handlers[ msgtype ]( peerconn, msgdata,clientsock.getpeername() )
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
    
        self.__debug( 'Disconnecting ' + str(clientsock.getpeername()) )
        peerconn.close()

    #--------------------------------------------------------------------------
    def __runstabilizer( self, stabilizer, delay ):
    #--------------------------------------------------------------------------
        while not self.shutdown:
            stabilizer()
            time.sleep( delay )

    #--------------------------------------------------------------------------
    def setmyid( self, myid ):
    #--------------------------------------------------------------------------
        self.myid = myid

    #--------------------------------------------------------------------------
    def startstabilizer( self, stabilizer, delay ):
    #--------------------------------------------------------------------------
        """ Registers and starts a stabilizer function with this peer. 
        The function will be activated every <delay> seconds. 
        """
        t = threading.Thread( target = self.__runstabilizer,args = [ stabilizer, delay ] )
        t.start()
        
    #--------------------------------------------------------------------------
    def add_event_handler( self, msgtype, handler ):
    #--------------------------------------------------------------------------
        """ Registers the handler for the given message type with this peer """
        assert len(msgtype) == 4
        self.handlers[ msgtype ] = handler

    #--------------------------------------------------------------------------
    def add_to_peer_dict( self, peerid, host, port ):
    #--------------------------------------------------------------------------
        """ 
        Adds a peer name and host:port mapping to the known list of peers.
        """
        if peerid not in self.peers and (self.maxpeers == 0 or len(self.peers) < self.maxpeers):
            self.peers[ peerid ] = (host, int(port))
            return True
        else:
            return False

    #--------------------------------------------------------------------------
    def getpeer( self, peerid ):
    #--------------------------------------------------------------------------
        """ Returns the (host, port) tuple for the given peer name """
        assert peerid in self.peers    # maybe make this just a return NULL?
        return self.peers[ peerid ]

    #--------------------------------------------------------------------------
    def removepeer( self, peerid ):
    #--------------------------------------------------------------------------
        """ Removes peer information from the known list of peers. """
        if peerid in self.peers:
            del self.peers[ peerid ]

    def removepeerat( self, loc ):
        self.removepeer(self.loc) 

    #--------------------------------------------------------------------------
    def get_peers_list( self ):
    #--------------------------------------------------------------------------
        """ Return a list of all known peer id's. """
        return self.peers.keys()

    #--------------------------------------------------------------------------
    def numberofpeers( self ):
    #--------------------------------------------------------------------------
        """ Return the number of known peer's. """
        return len(self.peers)

    #--------------------------------------------------------------------------
    def setup_server_socket( self, port, backlog=4 ):
    #--------------------------------------------------------------------------
        """ 
        Constructs and prepares a server socket listening on the given 
        port.
        """
        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        s.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        s.bind((socket.gethostname(),port))
        s.listen(backlog)
        return s
    
    #--------------------------------------------------------------------------
    def contact_peer_with_msg( self, host, port, msgtype, msgdata,pid=None, waitreply=True ):
    #--------------------------------------------------------------------------
        """
        Connects and sends a message to the specified host:port. The host's
        reply, if expected, will be returned as a list of tuples.
        """
        msgreply = []
        try:
            peerconn = Handler_thread( pid, host, port, debug=self.debug )
            #print msgdata
            peerconn.send_data( msgtype, msgdata )
            self.__debug( 'Sent %s: %s' % (pid, msgtype) )
            
            if waitreply:
                onereply = peerconn.receive_data()
                while (onereply != (None,None)):
                    msgreply.append( onereply )
                    self.__debug( 'Got reply %s: %s' % ( pid, str(msgreply)))
                    onereply = peerconn.receive_data()
            peerconn.close()
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
        return msgreply

    #--------------------------------------------------------------------------
    def checklivepeers( self ):
    #--------------------------------------------------------------------------
        """ 
        Attempts to ping all currently known peers in order to ensure that
        they are still active. Removes any from the peer list that do
        not reply. This function can be used as a simple stabilizer.
    
        """
        todelete = []
        for pid in self.peers:
            isconnected = False
            try:
                self.__debug( 'Check live %s' % pid )
                host,port = self.peers[pid]
                peerconn = Handler_thread( pid, host, port, debug=self.debug )
                peerconn.send_data( 'PING', '' )
                isconnected = True
            except:
                todelete.append( pid )
            if isconnected:
                peerconn.close()
        self.peers_list_lock.acquire()
        try:
            for pid in todelete: 
                if pid in self.peers: 
                    del self.peers[pid]
        finally:
            self.peers_list_lock.release()

    #--------------------------------------------------------------------------
    def mainloop( self ):
    #--------------------------------------------------------------------------
        s = self.setup_server_socket( self.serverport )
        self.__debug( 'Server started: %s (%s:%d)'
                  % ( self.myid, self.serverhost, self.serverport ) )
        while not self.shutdown:
            try:
                self.__debug( 'Listening for connections...' )
                s.settimeout(10)
                clientsock, clientaddr = s.accept()
                
                t = threading.Thread( target = self.__connection_handler,args = [ clientsock ] )
                t.start()
            except KeyboardInterrupt:
                self.shutdown = True
                continue
            except:
                if self.debug:
                    traceback.print_exc()
                    continue
        self.__debug( 'Main loop exiting' )
        s.close()
# end Communicate class

class Handler_thread:

    #--------------------------------------------------------------------------
    def __init__( self, peerid, host, port, sock=None, debug=False ):
    #--------------------------------------------------------------------------
        # any exceptions thrown upwards
    
        self.id = peerid
        self.debug = debug
    
        if not sock:
            self.s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
            self.s.connect( ( host, int(port) ) )
        else:
            self.s = sock
    
        self.sd = self.s.makefile( 'rw', 0 )
    
    
        #--------------------------------------------------------------------------
    def __pack_message_for_sending( self,msgtype, msgdata):
        #--------------------------------------------------------------------------
        msglen = len(msgdata)
        msg = struct.pack( "!4sL%ds" % msglen, msgtype, msglen, msgdata)
        return msg


    #--------------------------------------------------------------------------
    def __debug( self, msg ):
    #--------------------------------------------------------------------------
        if self.debug:
            btdebug( msg )


    #--------------------------------------------------------------------------
    def send_data( self, msgtype, msgdata ):
    #--------------------------------------------------------------------------
        """
        send_data( message type, message data ) -> boolean status
    
        Send a message through a peer connection. Returns True on success
        or False if there was an error.
        """
    
        try:
            msg = self.__pack_message_for_sending( msgtype, msgdata )
            self.sd.write( msg )
            self.sd.flush()
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
            return False
        return True
            
    #--------------------------------------------------------------------------
    def receive_data( self ):
    #--------------------------------------------------------------------------
        """
        receive_data() -> (msgtype, msgdata)
    
        Receive a message from a peer connection. Returns (None, None)
        if there was any error.
        """
    
        try:
            msgtype = self.sd.read( 4 )
            if not msgtype: 
                return (None, None)
            
            lenstr = self.sd.read( 4 )
            msglen = int(struct.unpack( "!L", lenstr )[0])
            msg = ""
    
            while len(msg) != msglen:
                data = self.sd.read( min(2048, msglen - len(msg)) )
                if not len(data):
                    break
                msg += data
    
            if len(msg) != msglen:
                return (None, None)
    
        except KeyboardInterrupt:
            raise
        except:
            traceback.print_exc()
            return (None, None)
    
        return (msgtype,msg)

    # end receive_data method

    #--------------------------------------------------------------------------
    def close( self ):
    #--------------------------------------------------------------------------
        self.s.close()
        self.s = None
        self.sd = None

    #--------------------------------------------------------------------------
    def __str__( self ):
    #--------------------------------------------------------------------------
        return "|%s|" % id