#!/usr/bin/python
import sys
import threading
from Tkinter import *
from random import *
from framework import *
import pygame
import sys
import tmx
import random
from tmx import *
import player_body
from player_body import *
import game_elements
from game_elements import *
import enemy_body
from enemy_body import *
import txtlib
import Queue
import thread

PEERNAME = "NAME"   # request a peer's canonical id
LISTPEERS = "LIST"
PLAYER_LIST="PLAY"
INSERTPEER = "JOIN"
MOVE = "MOVE"
FIRE = "FIRE"
FLAG = "FLAG"
UPDATE = "UPDT"
OBSTACLE = "OBST"
PEERQUIT = "QUIT"
REPLY = "REPL"
ERROR = "ERRO"
GAME_START="GAME" # send to bootstrap to get game details
DETAILS="DETL" # bootstrap replies with this as first message followed by PLAYER_LIST messages
PEER_INFO_DETAILS="INFO" # Request for information from peer after getting the list from bootstrap
PLAY_START="PSTA"
I_WIN = "IWIN"
I_LOST="LOST"
INFORM_GAME_END_BOOTSTRAP="OVER"
LEADER = "LEAD"
LEAVING = "LEAV"
DROP_NODE = "DROP"
DEAD_NODE = "DEAD"
HEART_BEAT = "HBMS"

MAX_PLAYER_NUMBER = 4
# Test if a player can leave and Rejoin 
REJOIN ="REJN"
PEER_INFO_DETAILS_AFTERSTART="PIDA"

UPDATE_FREQUENCY = 0.03
CHECK_COUNT_FREQUENCY = 1
WAIT_NEW_LEADER = 5

class Game(object,Communicate):
    
    """
    This constructor does most of the bootstrapping. All nodes first contact the bootstrap node and get information
    like game-id, number of peers , list of peers and their player_num from it. Once thats done, they contact any peers
    from the list that they get and exchange information about each other. The first person is considered the head and 
    he starts the game
    """
    #--------------------------------------------------------------------------
    def __init__( self, firstpeer,maxpeers=5, serverport=12345, master=None ):
    #--------------------------------------------------------------------------
        
        Communicate.__init__(self, maxpeers, serverport)
        """
        This is a dictionary containing message type to function pointer mappings. On receiving a message,check if a 
        handler is present and pass the data to the handler
        """
        handlers = {
                    PEERNAME: self.__handle_peername,
                    MOVE: self.__handle_move,
                    FIRE: self.__handle_fire,
                    FLAG: self.__handle_flag,
                    UPDATE: self.__handle_update,
                    PEER_INFO_DETAILS: self.__peer_info_details,
                    PLAY_START: self.__play_start,
                    I_WIN:self.__handle_game_end_peers,
                    LEAVING:self.__handle_player_leaving_gracious,
                    DROP_NODE:self.__handle_node_drop
                    }
        for mt in handlers:
            self.add_event_handler(mt, handlers[mt])
        
        
        self.map=" " # signifies the current map to be used
        self.number_peers=0 # This is the number of peers returned by the bootstrap node
        self.player_num=-1 # The player_num returned by the bootstrap node
        self.my_peer_name=firstpeer # Your own host:port 
        self.enemy={} # list of all other players objects that are created later
        
        self.flag_list={}
        self.flags_collected = {}
        self.message_queue = {}
        self.update_count = 0
        
        self.game_over = False
        self.win = False

        self.stall_update=False
        self.last_joined = ""
        self.dead_node = {}
        pygame.init()
        
        host,port = firstpeer.split(':')
        self.t = threading.Thread( target = self.mainloop, args = [] )
        self.t.setDaemon(True)
        self.t.start()
###############################################################
        self.get_bootstrap()
###############################################################   
        #PLEASE uncomment and assign your IP to the following for testing to make it work on your machine

        self.bootstrap='128.237.214.194:12345'       
        
        self.contactbootstrap(GAME_START,firstpeer) #contact bootstrap to get required information
            
        print self.player_num
        self.message_queue[self.player_num] = {}
        self.message_queue[self.player_num]['move'] = Queue.Queue(0)
        self.message_queue[self.player_num]['bullet'] = Queue.Queue(0)
        self.message_queue[self.player_num]['flag'] = Queue.Queue(0)
        self.flags_collected[self.player_num] = 0
        self.playernum_hostip_dict[self.player_num]=self.my_peer_name
            
        self.connect_pool={}
        self.update_pool={}
        self.create_update_pool=False
        
        pygame.init()
        self.screen = pygame.display.set_mode((1034, 624))
        # The first node to join the game is given the option to start the game. All others wait for him to start
        if int(self.number_peers) > 0:
            #self.contactpeers(firstpeer)
            self.multicast_to_peers(PEER_INFO_DETAILS,self.my_peer_name)
            self.showstartscreen_rest()    
        elif int(self.number_peers)==0: #first node to join the game
            self.showstartscreen_first()
            #once he starts, convey information to all peers so that they can start too
            #self.convey_play_start(firstpeer)
            print "LEADER_LIST , LEADER_NUM"
            print self.leader_list , self.leader_num
                
     
    #--------------------------------------------------------------------------
    def __onDestroy(self):
    #--------------------------------------------------------------------------
        self.shutdown = True     
    
    #--------------------------------------------------------------------------
    def __debug(self, msg):
    #--------------------------------------------------------------------------
        if self.debug:
            print_debug(msg)
 
 #--------------------------------------------------------------------------
    def update_datastructures(self,leaving_player_num):
 #--------------------------------------------------------------------------
        
        print "BEFORE_DS_HOSTIP"
        print self.playernum_hostip_dict
        temp=[]
        for key in self.playernum_hostip_dict:
            temp.append(key)
        temp.sort()
        print temp
        for x in range (0,len(temp)):
            if int(leaving_player_num) < int(temp[x]):
                old_key=temp[x]
                new_key= str(int(temp[x])-1)
                self.playernum_hostip_dict[new_key]=self.playernum_hostip_dict.pop(old_key)
            if x==len(self.playernum_hostip_dict):
                break
        print "UPDATE_DS_HOSTIP"
        print self.playernum_hostip_dict
        
        i=-1
        print "Before_DS_LEADER_LIST"
        print self.leader_list
        for element in range (0,len(self.leader_list)):
           print int(self.leader_list[element])
           
           if int(leaving_player_num) < int(self.leader_list[element]):
               self.leader_list[element]= str(int(self.leader_list[element])-1)
    
        print "UPDATE_DS_LEADER_LIST"
        print self.leader_list
        
    """--------------------------------------------ALL HANDLER FUNCTIONS---------------------------------"""
    
    
    #--------------------------------------------------------------------------    
    def __play_start(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        """ 
        This message to start play is sent by the first node to every other node in the game. On receiving the message,they make
        their play_start variable to True which makes them exit the above "showstartscreen_rest" function and start the game
        """
        peerconn.send_data(REPLY,'STARTED GAME')
        self.play_start=True
    
    #--------------------------------------------------------------------------    
    def __peer_info_details(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        """
        Get information about a peer, save it and send back your own information
        """
        gameid,peername,player_number= data.split()
        if(gameid!=self.game_id):
            print "wrong game. Something wrong with bootstrapping"
            peerconn.send_data(ERROR, 'Game ID different %s' % self.game_id)
            return
        self.playernum_hostip_dict_lock.acquire()
        if(player_number in self.playernum_hostip_dict):
            peerconn.send_data(ERROR, 'Player number already present %s' % self.game_id)
            return
        self.playernum_hostip_dict[player_number]=peername
        self.playernum_hostip_dict_lock.release()
        
        print 'get player:', player_number
        self.message_queue[player_number] = {}
        self.message_queue[player_number]['move'] = Queue.Queue(0)
        self.message_queue[player_number]['bullet'] = Queue.Queue(0)
        self.message_queue[player_number]['flag'] = Queue.Queue(0)
        self.flags_collected[player_number] = 0
            
        self.leader_list.append(player_number)
        
        if self.play_start==True:
            print "PLAY_START_TRUE"
            print self.enemy
            if not player_number in self.enemy.keys():
                print "HI"
                self.last_joined=player_number
                self.stall_update=True
            peerconn.send_data(PEER_INFO_DETAILS_AFTERSTART,'%s %s %s' % (self.game_id,self.my_peer_name,self.player_num))
        else:
            print "PLAY_START_FALSE"
            peerconn.send_data(PEER_INFO_DETAILS,'%s %s %s' % (self.game_id,self.my_peer_name,self.player_num))
    
    #--------------------------------------------------------------------------  
    def __handle_node_drop(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        print self.connect_pool
        del self.connect_pool[data]
        if self.player_num!=self.leader_num:
            remove = None
            for key in self.playernum_hostip_dict:
                if self.playernum_hostip_dict[key] == data:
                    remove = key
            if remove:
                self.playernum_hostip_dict.pop(remove)
                self.leader_list.remove(remove)
                self.sort_and_assign_leader()
                if self.enemy[remove]:
                    print self.enemy[remove].alive
                    self.enemy[remove].alive=False
                    self.enemy.pop(remove)
        else:
            del self.update_pool[data]

            print "Current dictionary is : ",self.playernum_hostip_dict
  
    #--------------------------------------------------------------------------   
    def __handle_move(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        player_num = data.split(' ')[0]
        data = data.split(' ', 1)[1]
        #print 'received move message from', player_num
        self.message_queue[player_num]['move'].put(data)
        #self.add_message_to_queue(data,self.message_queue[player_num]['move'])
        
    
    #--------------------------------------------------------------------------    
    def __handle_fire(self,peerconn,data,peername):
    #--------------------------------------------------------------------------        
        player_num = data.split(' ')[0]
        data = data.split(' ', 1)[1]
        #print 'received fire message from', player_num
        self.message_queue[player_num]['bullet'].put(data)
        #self.add_message_to_queue(data,self.message_queue[player_num]['bullet'])
    
    #--------------------------------------------------------------------------    
    def __handle_flag(self,peerconn,data,peername):
    #--------------------------------------------------------------------------        
        player_num = data.split(' ')[0]
        data = data.split(' ', 1)[1]
        #print 'received flag message from', player_num, 'for flag', data
        self.flags_collected[player_num] += 1
        self.message_queue[data]['flag'].put(data)
        #self.add_message_to_queue(data,self.message_queue[player_num]['flag'])
    
    #--------------------------------------------------------------------------    
    def __handle_update(self,peerconn,data,peername):
    #--------------------------------------------------------------------------        
        #print "update"
        self.update_count += 1
        self.update_all()
    
    def update_all(self):
        #dt = self.clock.tick(20)
        #print dt
        self.tilemap.update(90 / 1000.,self)
        self.tilemap.draw(self.game_surface)
        #used to update the player list tab on the left with the right message contents
        self.show_on_screen_messages()
        self.screen2.blit(self.game_surface,(210,0))
        self.screen2.blit(self.player_surface.area, (5, 5))
        self.screen2.blit(self.message_surface.area,(5,310))

        '''self.screen.blit(self.game_surface,(210,0))
        self.screen.blit(self.player_surface.area, (5, 5))
        self.screen.blit(self.message_surface.area,(5,310))'''
        pygame.display.flip()
    
    def check_count(self):
        while 1:
            if (self.game_over == True or self.win == True):
                break
            
            time.sleep(CHECK_COUNT_FREQUENCY)
            #print 'Checking update count', self.update_count
            if (self.update_count <= 0):
                print 'Leader dead!'
                key = self.leader_num
                
                data = str(self.game_id) + ' ' + str(self.playernum_hostip_dict[key]) + ' ' + str(key)
                self.contactbootstrap("DROP", None, data)
                
                del self.playernum_hostip_dict[key]
                self.leader_list.remove(key)
                self.sort_and_assign_leader()
                self.enemy[key].alive = False
                self.enemy.pop(key)
                
                time.sleep(WAIT_NEW_LEADER)
                    
            self.update_count = 0
    
    def add_message_to_queue(self,message,queue):
        message_seq = int(message.split(' ')[0])
        for i in range(0, len(queue) + 1):
            if (i == len(queue)):
                queue.append(message)
            seq = int(queue[i].split(' ')[0])
            if (seq > message_seq):
                queue.insert(i, message)
            
    #-------------------------------------------------------------------------- 
    def __handle_player_leaving_gracious(self,peerconn,data,peername):
    #--------------------------------------------------------------------------     
        """
        There are 2 scenarios where a player can exit graciously.
        1. From the waiting screen initially 
        2. When playing in the middle of the game
        When a player exits from the waiting screen , then we inform all the peers and remove the player from their 
        player_num , hostip dictionary. Then we inform the bootstrap node and remove the player from the game dict for that
        game id. This is implemented before the self.play_start variable is set to true.
        
        When a player exits in the middle of the game , we inform all the peers and we also inform the bootstrap node.
        The players object has to be removed from the screen accordingly. The player needs to be removed from the game_dict
        too. Flags collected by the player have to be replayed back. This is implemented after the self.play_start=true   
        """  
        players_game_id,peer_name,player_num= data.split(" ") 
        if self.play_start==False:
            if self.my_peer_name!=self.bootstrap:
                if players_game_id == self.game_id:
                    try:
                        self.playernum_hostip_dict.pop(player_num)
                        self.leader_list.remove(player_num)
                        if int(player_num) < int(self.player_num):
                            self.player_num=str(int(self.player_num)-1)
                        self.update_datastructures(player_num)
                        self.sort_and_assign_leader()
                    except KeyError:
                        print "Key not found"
        elif self.play_start==True:
            if self.my_peer_name!=self.bootstrap:
                if players_game_id == self.game_id:
                    try:
                        del self.connect_pool[self.playernum_hostip_dict[player_num]]
                        if self.player_num==self.leader_num:
                            del self.update_pool[self.playernum_hostip_dict[player_num]]
                        self.playernum_hostip_dict.pop(player_num)
                        self.leader_list.remove(player_num)
                        self.sort_and_assign_leader()
                    except KeyError:
                        print "Key not found"
                    if self.enemy[player_num]:
                        print self.enemy[player_num].alive
                        self.enemy[player_num].alive=False
                        self.enemy.pop(player_num)
    
    #--------------------------------------------------------------------------  
    def __handle_game_end_peers(self,peerconn,data,peername):
    #-------------------------------------------------------------------------- 
        print " In game_end"
        print self.playernum_hostip_dict
        gameid,winnername,winnerid=data.split(" ")
        if(gameid==self.game_id):
            self.playernum_hostip_dict_lock.acquire()
            if(self.playernum_hostip_dict[winnerid]==winnername):
                peerconn.send_data(I_LOST,'%s' %self.my_peer_name)
                
            self.playernum_hostip_dict_lock.release()
        self.game_over = True
  
    #--------------------------------------------------------------------------
    def __handle_peername(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        """ Handles the NAME message type. Message data is not used. """
        peerconn.send_data(REPLY, self.myid)
 
    """--------------------------------------------END HANDLER FUNCTIONS---------------------------------"""
 
 
    """--------------------------------------------NODE CONTACT FUNCTIONS---------------------------------"""
     
    #--------------------------------------------------------------------------
    def contactbootstrap(self,messagetype,peername, data = None):
    #--------------------------------------------------------------------------
        """
         This function is called by all nodes when they want to start a game and it gets back all details for the game
        """
        host,port = self.bootstrap.split(":")
        if messagetype==GAME_START:
            try:
                resp = self.contact_peer_with_msg(host, port,messagetype,peername)
                self.__debug(str(resp))
                print "RESPONSE",resp
                if (resp[0][0] != DETAILS):
                    return
                #Get back game id, no:of peers,player_num and players list
                self.game_id,self.map,self.number_peers,self.player_num=resp[0][1].split()
                self.leader_list.append(self.player_num)
                x=1
                for x in range(1,1+int(self.number_peers)):
                    if (resp[x][0] != PLAYER_LIST):
                        return 
                    data=resp[x][1]
                    self.peers_list_lock.acquire()
                    try:
                        try:
                            peerid,host,port = data.split()
                            if peerid not in self.get_peers_list() and peerid != self.myid:
                                self.add_to_peer_dict(peerid, host, port)
                                self.__debug('added peer: %s' % peerid)
                            else:
                                print ('Join: peer already inserted %s' % peerid)
                        except:
                            self.__debug('invalid insert %s: %s' % (str(12345), data))
                    finally:
                        self.peers_list_lock.release()
            except Exception,e: 
                print e
                traceback.print_exc()
                self.print_error_screen()
                pygame.quit()
                self.__onDestroy()
                sys.exit() 
        
        elif messagetype==LEAVING:
            print "In contact bootstrap"
            data=self.game_id+" "+self.my_peer_name+" "+self.player_num+" "+str(self.play_start) 
            resp = self.contact_peer_with_msg(host, port,messagetype,data)
        
        elif messagetype==INFORM_GAME_END_BOOTSTRAP:
            data = self.game_id+" "+self.my_peer_name+" "+self.player_num
            self.contact_peer_with_msg(host,port,INFORM_GAME_END_BOOTSTRAP,data)  
        elif messagetype==DROP_NODE:
            self.contact_peer_with_msg(host,port,messagetype,data)
        elif messagetype==DEAD_NODE:
            self.contact_peer_with_msg(host,port,messagetype,data)


            
        
    #--------------------------------------------------------------------------
    def multicast_to_peers(self,messagetype,peername):
    #--------------------------------------------------------------------------
        """
        This function is a common handler thats used to multicast messages to different players in the game. The messages
        can be of different types and are differentiated with a switch case
        """
        if messagetype==PEER_INFO_DETAILS:
            data = self.game_id+" "+peername+" "+self.player_num
            message_type=""
            self.peers_list_lock.acquire()
            for key in self.peers:
                host,port=self.peers[key][0],self.peers[key][1]
                resp = self.contact_peer_with_msg(host, port,messagetype,data)
                print "Response received "+resp[0][0]
                if (resp[0][0] !=PEER_INFO_DETAILS and resp[0][0]!=PEER_INFO_DETAILS_AFTERSTART):
                    return
                
                received_messagetype=resp[0][0]
                gameid,peername,player_number= resp[0][1].split()
                self.playernum_hostip_dict[player_number]=peername
                self.leader_list.append(player_number)
                self.message_queue[player_number] = {}
                self.message_queue[player_number]['move'] = Queue.Queue(0)
                self.message_queue[player_number]['bullet'] = Queue.Queue(0)
                self.message_queue[player_number]['flag'] = Queue.Queue(0)
                self.flags_collected[player_number] = 0
                print "LOCAL PLAYER DICTIONARY"
                print self.playernum_hostip_dict
                print received_messagetype
            if received_messagetype==PEER_INFO_DETAILS_AFTERSTART:
                print "AFTER START CONSIDITION"
                self.play_start=True
            self.peers_list_lock.release()
            
        elif messagetype==I_WIN:
            data = self.game_id+" "+self.my_peer_name+" "+self.player_num
            acknowledgements = 0
            if len(self.playernum_hostip_dict)!=0:
                self.playernum_hostip_dict_lock.acquire()
                for key in self.playernum_hostip_dict:
                    if key!=self.player_num:
                        value = self.playernum_hostip_dict[key].split(":")
                        host,port = value[0],value[1]
                        resp = self.contact_peer_with_msg(host, port,messagetype,data)
                        if resp[0][0]!=I_LOST:
                            return
                        acknowledgements = acknowledgements +1
                self.playernum_hostip_dict_lock.release()
            self.contactbootstrap(INFORM_GAME_END_BOOTSTRAP,self.my_peer_name) 
            
        elif messagetype==PLAY_START:
            data = "START GAME"
            i=0
            self.playernum_hostip_dict_lock.acquire()
            for key in self.playernum_hostip_dict:
                if key!=self.player_num:
                    host,port=self.playernum_hostip_dict[key].split(":")
                    resp = self.contact_peer_with_msg(host, port,messagetype,data)
                    if(resp[0][0]==REPLY):
                        i=i+1
            self.playernum_hostip_dict_lock.release()
            host,port = self.bootstrap.split(":")
            data="STARTED " + str(self.game_id)
            resp = self.contact_peer_with_msg(host, port,GAME_START,data)
        
        elif messagetype==LEADER:
            data = self.player_num
            for key in self.playernum_hostip_dict:
                host,port=self.playernum_hostip_dict[key].split(":")
                resp = self.contact_peer_with_msg(host, port,messagetype,data)
        
        elif messagetype==LEAVING:
            print "Leaving message sent"
            data=self.game_id+" "+self.my_peer_name+" "+self.player_num
            self.playernum_hostip_dict_lock.acquire()
            self.playernum_hostip_dict.pop(self.player_num)
            for key in self.playernum_hostip_dict:
                host,port=self.playernum_hostip_dict[key].split(":")
                resp = self.contact_peer_with_msg(host, port, messagetype, data,None, False)
            #contact bootstrap and inform that you are leaving here
            self.contactbootstrap(LEAVING,self.my_peer_name)
            self.playernum_hostip_dict_lock.release()
    
    #-------------------------------------------------------------------------- 
    def multicast_to_peers_data(self, message_type, data):
    #-------------------------------------------------------------------------- 
        if message_type==UPDATE:
            self.playernum_hostip_dict_lock.acquire()
            try:
                for key in self.playernum_hostip_dict:
                    value = self.playernum_hostip_dict[key].split(":")
                    host,port = value[0],value[1]
                    # print "Contacting peer", (host, port)
                    self.contact_peer_with_msg_update(host, port, message_type, data)  
            except:
                traceback.print_exc()
                print ""
            self.playernum_hostip_dict_lock.release()
        
        elif message_type==DROP_NODE:
            for key in self.playernum_hostip_dict:
                    value = self.playernum_hostip_dict[key].split(":")
                    host,port = value[0],value[1]
                    self.contact_peer_with_msg(host, port, "DROP", data)    
        else:
            try:
                for key in self.playernum_hostip_dict:
                    value = self.playernum_hostip_dict[key].split(":")
                    host,port = value[0],value[1]
                    self.contact_peer_with_msg_static(host, port, message_type, data) 
            except:
                print ""
    """--------------------------------------------END NODE CONTACT FUNCTIONS---------------------------------"""

    def  create_update_pool_leader(self):
        try:
            for key in self.playernum_hostip_dict:
                value = self.playernum_hostip_dict[key].split(":")
                host,port = value[0],value[1]
                self.update_pool[self.playernum_hostip_dict[key]] = Handler_thread( None, host, port, debug=self.debug )
                print "create update connection to ",
                print host,
                print ":",
                print port
                
                self.check = threading.Thread( target = self.check_mainloop, args = [] )
                self.check.setDaemon(True)
                self.check.start()
                
            self.create_update_pool=False
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
            


    #-------------------------------------------------------------------------- 
    def sort_and_assign_leader(self):
    #-------------------------------------------------------------------------- 
        self.leader_list_lock.acquire()
        if len(self.leader_list)>0:
                self.leader_list.sort()
                self.leader_num=self.leader_list[0]
                self.create_update_pool=True
        self.leader_list_lock.release()
        
    
    def allow_player_joined(self):
        try: 
            player_number = self.last_joined
            print self.playernum_hostip_dict
        
            host,port = self.playernum_hostip_dict[player_number].split(":")
            self.connect_pool[self.playernum_hostip_dict[player_number]]=Handler_thread(None,host,port,debug=self.debug)
            print "Reconnected connection pool",self.connect_pool
        
            if self.player_num == self.leader_num:
                self.update_pool[self.playernum_hostip_dict[player_number]]=Handler_thread(None,host,port,debug=self.debug)
            
            start_cell = self.tilemap.layers['player'].find('player')[int(player_number)-1]
            flag_cell = self.tilemap.layers['flags'].find('flag')[int(player_number)-1]
        
            self.enemy[player_number]=enemies((start_cell.px,start_cell.py),player_number,self.enemies)
            self.tilemap.layers.append(self.enemies)
        
            self.stall_update=False
        except:
                traceback.print_exc()
          
    """--------------------------------------------ALL SCREEN DISPLAY FUNCTIONS---------------------------------"""
    
    #--------------------------------------------------------------------------
    def showstartscreen_first(self):
    #--------------------------------------------------------------------------
        """
         Shows the start screen for the first node. The screen shows battle maze with list of hosts available and a message
         saying "press space to accept and start"
        """
        background=pygame.image.load("title/battlemaze_leader.png").convert()
        background = pygame.transform.scale(background, (1034,590))
        host_surface = txtlib.Text((1034, 34), 'freesans',30)
        host_surface.background_color=(0,0,0)
        host_surface.default_color=(178,34,34)
        hosts="                 Hosts Joined :   "
        while 1:
            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.multicast_to_peers(PLAY_START,self.my_peer_name)
                        self.play_start=True
                        self.sort_and_assign_leader()
                        return
                    if event.key == pygame.K_ESCAPE:
                        self.multicast_to_peers(LEAVING,self.my_peer_name)
                        pygame.quit()
                        self.__onDestroy()
                        sys.exit()
            for key in self.playernum_hostip_dict:
                if key!=self.player_num:
                    hosts =hosts+str(self.playernum_hostip_dict[key])+" | "
            host_surface.text=hosts
            host_surface.update()
            self.screen.blit(background, (0, 0))
            self.screen.blit(host_surface.area, (0, 590))
            pygame.display.flip()
            hosts="                 Hosts Joined :   "
    #--------------------------------------------------------------------------    
    def showstartscreen_rest(self):
    #--------------------------------------------------------------------------
        """
        This is the start screen for all other nodes. The start screen shows a list of all hosts in the game and a message
        saying "awaiting approval". Once the first node in the game presses space, this function exits.
        """
        background=pygame.image.load("title/battlemaze_peers.png").convert()
        background = pygame.transform.scale(background, (1034,590))
        host_surface = txtlib.Text((1034, 34), 'freesans',30)
        host_surface.background_color=(0,0,0)
        host_surface.default_color=(178,34,34)
        hosts="                 Hosts Joined :   "
        
        flag=0
        while self.play_start!=True:
            if self.leader_num==self.player_num:
                flag=1
                break
            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.multicast_to_peers(LEAVING,self.my_peer_name)
                        pygame.quit()
                        self.__onDestroy()
                        sys.exit()
            for key in self.playernum_hostip_dict:
               if key!=self.player_num:
                    hosts =hosts+str(self.playernum_hostip_dict[key])+" | "
            host_surface.text=hosts
            host_surface.update()
            self.screen.blit(background,(0,0))
            self.screen.blit(host_surface.area, (0, 590))
            pygame.display.flip()
            hosts="                 Hosts Joined :   "
        if flag==1:
            self.showstartscreen_first()
        else:
            self.sort_and_assign_leader()
     
    #--------------------------------------------------------------------------
    def show_winner_screen(self):
    #--------------------------------------------------------------------------
        """
        This is the winner display screen , once the game gets over
        """
        background=pygame.image.load("title/you_win.png").convert()
        background = pygame.transform.scale(background, (1034,624))
        font = pygame.font.Font('freesansbold.ttf', 20)
        message="Press Space to exit"
        while 1:
            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        self.__onDestroy()
                        sys.exit()
                        return
            text = font.render(message, True,(178,34,34),(46,139,87))
            textpos = text.get_rect()
            textpos.midbottom=background.get_rect().midbottom
            background.blit(text, textpos)
            self.screen.blit(background, (0, 0))
            pygame.display.flip()
    
    #--------------------------------------------------------------------------
    def show_loser_screen(self):
    #--------------------------------------------------------------------------
        """
        This screen gets displayed for every loser in the game
        """
        background=pygame.image.load("title/game_over.png").convert()
        background = pygame.transform.scale(background, (1034,624))
        font = pygame.font.Font('freesansbold.ttf', 20)
        message="Press Space to exit"
        while 1:
            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        self.__onDestroy()
                        sys.exit()
                        return
            text = font.render(message, True,(178,34,34),(46,139,87))
            textpos = text.get_rect()
            textpos.midbottom=background.get_rect().midbottom
            background.blit(text, textpos)
            self.screen.blit(background, (0, 0))
            pygame.display.flip()
      

    #--------------------------------------------------------------------------
    def show_on_screen_messages(self):
    #--------------------------------------------------------------------------
        data1="             PLAYER LIST\n\n"
        for key in self.playernum_hostip_dict:
            data1 = data1+ str(key)+"    "+str(self.playernum_hostip_dict[key])+"\n\n"
        
        self.player_surface.text=data1
        self.player_surface.update()
        
        data2="             MESSAGES\n\n"
        self.message_surface.text=data2
        self.message_surface.update()
    
        """--------------------------------------------End SCREEN DISPLAY FUNCTIONS---------------------------------"""
      
     #--------------------------------------------------------------------------
    def print_error_screen(self):
    #--------------------------------------------------------------------------
        screen = pygame.display.set_mode((1034, 624))
        background=pygame.image.load("title/server_busy.png").convert()
        background = pygame.transform.scale(background, (1034,624))
        while 1:
            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        self.__onDestroy()
                        sys.exit()
                        return
            screen.blit(background, (0, 0))
            pygame.display.flip()
    #--------------------------------------------------------------------------
    def main(self, screen):
    #--------------------------------------------------------------------------    
    
        self.screen2 = screen
        """
        The main function that actually starts the game
        """
        self.player_surface = txtlib.Text((200, 300), 'freesans',21)
        self.message_surface= txtlib.Text((200, 308), 'freesans',21)
        self.game_surface = pygame.Surface((824,624))
        
        self.tilemap = tmx.load(self.map, self.game_surface.get_size())
        self.sprites = tmx.SpriteLayer()
        self.enemies = tmx.SpriteLayer()
        self.players_sp = tmx.SpriteLayer()
        self.blockwall = tmx.SpriteLayer()
        self.flag_layer = tmx.SpriteLayer()
        
        background = pygame.image.load('title/background.jpg').convert()
        background = pygame.transform.scale(background, (210,624))
        screen.blit(background,(0,0))
        pygame.display.flip()
        
        start_cell = self.tilemap.layers['player'].find('player')[int(self.player_num)-1]
        flag_cell = self.tilemap.layers['flags'].find('flag')[int(self.player_num)-1]
        self.player1 = player((start_cell.px, start_cell.py),self.player_num,self.players_sp)
        self.flag_list[self.player_num]=flags((flag_cell.px,flag_cell.py),self.player_num,self.flag_layer)
        for entry in self.playernum_hostip_dict:
            if (entry != self.player_num):
                start_cell = self.tilemap.layers['player'].find('player')[int(entry)-1]
                flag_cell = self.tilemap.layers['flags'].find('flag')[int(entry)-1]
                self.enemy[entry]=enemies((start_cell.px,start_cell.py),entry,self.enemies)
                self.flag_list[entry]=flags((flag_cell.px,flag_cell.py),entry,self.flag_layer)
        
        self.tilemap.layers.append(self.sprites)
        self.tilemap.layers.append(self.blockwall)
        self.tilemap.layers.append(self.enemies)
        self.tilemap.layers.append(self.players_sp)
        self.tilemap.layers.append(self.flag_layer)

        # create the connect_pool

        try:
            for key in self.playernum_hostip_dict:
                value = self.playernum_hostip_dict[key].split(":")
                host,port = value[0],value[1]
                self.connect_pool[self.playernum_hostip_dict[key]] = Handler_thread( None, host, port, debug=self.debug )
                print "create connection to ",
                print host,
                print ":",
                print port
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
        """  
        if  self.player_num == self.leader_num:
            self.check = threading.Thread( target = self.check_mainloop, args = [] )
            self.check.setDaemon(True)
            self.check.start()
        """      
        clock = pygame.time.Clock()
        self.update_all()
        
        thread.start_new_thread(self.check_count, ())
        
        while 1:
            time.sleep(UPDATE_FREQUENCY)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.multicast_to_peers(LEAVING,self.my_peer_name)
                    pygame.quit()
                    self.__onDestroy()
                    sys.exit()
                    return
            # if all the flags have been collected , convey that you win the game
            if self.stall_update==False:
                if (self.flags_collected[self.player_num] == len(self.playernum_hostip_dict)):
                    self.win = True
                    self.multicast_to_peers(I_WIN, self.my_peer_name)
                    self.show_winner_screen()
                if self.game_over == True:
                    print 'Game over'
                    self.show_loser_screen()
                if (self.player_num == self.leader_list[0]):
                    if self.create_update_pool==True:
                        self.create_update_pool_leader()
                    self.multicast_to_peers_data(UPDATE, '')
            else:
                self.allow_player_joined()

if __name__=='__main__':
    if len(sys.argv) < 4:
        print "Syntax: %s server-port max-peers peer-ip:port" % sys.argv[0]
        sys.exit(-1)
    serverport = int(sys.argv[1])
    maxpeers = sys.argv[2]
    peerid = sys.argv[3]
    appl = Game(firstpeer=peerid, maxpeers=maxpeers, serverport=serverport)
    appl.main(appl.screen)
