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

PEERNAME = "NAME"   # request a peer's canonical id
LISTPEERS = "LIST"
PLAYER_LIST="PLAY"
INSERTPEER = "JOIN"
MOVE = "MOVE"
FIRE = "FIRE"
FLAG = "FLAG"
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
                    LISTPEERS : self.__handle_listpeers,INSERTPEER : self.__handle_insertpeer,
                    PEERNAME: self.__handle_peername,
                    MOVE: self.__handle_move,
                    FIRE: self.__handle_fire,
                    FLAG: self.__handle_flag,
                    OBSTACLE: self.__handle_obstacle,
                    PEERQUIT: self.__handle_quit,GAME_START: self.__handle_gamestart,
                    PEER_INFO_DETAILS: self.__peer_info_details,PLAY_START: self.__play_start,I_WIN:self.__handle_game_end_peers,
                    INFORM_GAME_END_BOOTSTRAP: self.__handle_game_end_bootstrap,LEAVING:self.__handle_player_leaving_gracious
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
        
        host,port = firstpeer.split(':')
        self.t = threading.Thread( target = self.mainloop, args = [] )
        self.t.start()  
    #    self.startstabilizer( self.checklivepeers, 3 )
        # A bootstrap node should only help in bootstrapping. So all this is not needed for it
        if firstpeer!=self.bootstrap:
            self.contactbootstrap(GAME_START,firstpeer) #contact bootstrap to get required information
            
            print self.player_num
            self.message_queue[self.player_num] = {}
            self.message_queue[self.player_num]['move'] = Queue.Queue(0)
            self.message_queue[self.player_num]['bullet'] = Queue.Queue(0)
            self.flags_collected[self.player_num] = 0
            self.playernum_hostip_dict[self.player_num]=self.my_peer_name
            
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
    def __handle_gamestart(self, peerconn,data,peername):
    #--------------------------------------------------------------------------
        """
        Function that chooses the Map and other details and sends it back to the user
        DETAILS contain - game-id,MAP,Number of peers and X,Y position
        GAME contains list of peers
        This function is used only by the bootstrapping node and is called from "contactbootstrap" function
        This function is used to contact bootstrap for getting initial details and to inform bootstrap once all 
        nodes have started play so that it does not allow any more players
        """
        # This condition is hit when nodes require initial set up details
        if data!="STARTED":
            self.game_dict_lock.acquire()
            #Check if there is already a game with lesser than 4 users. If so add the user to it. If not create new game
            if(self.game_id in self.game_dict):
                player_number = len(self.game_dict[self.game_id])+1
                if(len(self.game_dict[self.game_id])<=3):
                    peerconn.send_data(DETAILS,'%d %s %d %d' % (self.game_id,self.gameid_map_dict[self.game_id],len(self.game_dict[self.game_id]),player_number))
                    for peer_list in self.game_dict[self.game_id]:
                        peerconn.send_data(PLAYER_LIST,'%s %s %d' % (peer_list,peer_list.split(":")[0],int(peer_list.split(":")[1])))
                    self.game_dict[self.game_id].append(data)
                    if(len(self.game_dict[self.game_id])==4):
                        self.game_id=self.game_id+1
                print "Game dictionary is :"
                print self.game_dict[self.game_id]
            
            #create new game for the given game-id and add user to it
            else:
                map_id=random.randint(1, 4)
                print self.available_maps_dict[map_id]    
                self.game_dict[self.game_id]=[]
                player_number = len(self.game_dict[self.game_id])+1
                peerconn.send_data(DETAILS,'%d %s %d %d' % (self.game_id,self.available_maps_dict[map_id],len(self.game_dict[self.game_id]), player_number))
                self.game_dict[self.game_id].append(data)
                self.gameid_map_dict[self.game_id]=self.available_maps_dict[map_id]
                print "Game dictionary is :"
                print self.game_dict[self.game_id]
            self.game_dict_lock.release()
        #this condition is hit when a game is started with < 4 players
        else:
                self.game_id=self.game_id+1
                peerconn.send_data(REPLY,'OK')
    
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
        self.flags_collected[player_number] = 0
            
        
        self.leader_list.append(player_number)
        peerconn.send_data(PEER_INFO_DETAILS,'%s %s %s' % (self.game_id,self.my_peer_name,self.player_num))
    
    #--------------------------------------------------------------------------    
    def __handle_move(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        player_num = data.split(' ')[0]
        data = data.split(' ', 1)[1]
        print 'received move message from', player_num
        self.message_queue[player_num]['move'].put(data)
        
    
    #--------------------------------------------------------------------------    
    def __handle_fire(self,peerconn,data,peername):
    #--------------------------------------------------------------------------        
        player_num = data.split(' ')[0]
        data = data.split(' ', 1)[1]
        print 'received fire message from', player_num
        self.message_queue[player_num]['bullet'].put(data)
    
    #--------------------------------------------------------------------------    
    def __handle_flag(self,peerconn,data,peername):
    #--------------------------------------------------------------------------        
        player_num = data.split(' ')[0]
        data = data.split(' ', 1)[1]
        print 'received flag message from', player_num
        self.flags_collected[player_num] += 1
        #self.message_queue[player_num]['bullet'].put(data)
        
    #--------------------------------------------------------------------------    
    def __handle_obstacle(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        print ""
        
    #--------------------------------------------------------------------------    
    def __handle_quit(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        print ""
      
    #--------------------------------------------------------------------------    
    def __handle_insertpeer(self, peerconn, data,peername):
    #--------------------------------------------------------------------------    
        print " "
    
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
            elif self.my_peer_name==self.bootstrap:
                    self.game_dict_lock.acquire()
                    if peer_name in self.game_dict[int(players_game_id)]:
                        print " GAME DICT BEFORE REMOVING"
                        print self.game_dict[int(players_game_id)]
                        if len(self.game_dict[int(players_game_id)])==4:
                            self.game_id=self.game_id-1
                        self.game_dict[int(players_game_id)].remove(peer_name)
                        print " GAME DICT AFTER REMOVING"
                        print self.game_dict[int(players_game_id)]
                    self.game_dict_lock.release()
        elif self.play_start==True:
            if self.my_peer_name!=self.bootstrap:
                if players_game_id == self.game_id:
                    try:
                        self.playernum_hostip_dict.pop(player_num)
                        self.leader_list.remove(player_num)
                        self.sort_and_assign_leader()
                        print " PLAY HAS STARTED"
                        print self.playernum_hostip_dict
                    except KeyError:
                        print "Key not found"
                    
                    if self.enemy[player_num]:
                        print self.enemy[player_num].alive
                        self.enemy[player_num].alive=False
            else:
                    if peer_name in self.game_dict[int(players_game_id)]:
                        self.game_dict[int(players_game_id)].pop(peer_name)
    
    
    def __handle_game_end_peers(self,peerconn,data,peername):
        print " In game_end"
        print self.playernum_hostip_dict
        gameid,winnername,winnerid=data.split(" ")
        if(gameid==self.game_id):
            self.playernum_hostip_dict_lock.acquire()
            if(self.playernum_hostip_dict[winnerid]==winnername):
                peerconn.send_data(I_LOST,'%s' %self.my_peer_name)
                player.game_over='true'
            self.playernum_hostip_dict_lock.release()
                
    def __handle_game_end_bootstrap(self,peerconn,data,peername):
        gameid,winnername,winnerid=data.splot(" ")
        print "GAME END"
        print self.game_dict
        if gameid in self.game_dict:
            del self.game_dict[gameid]
        print self.game_dict
    #--------------------------------------------------------------------------    
    def __handle_listpeers(self, peerconn, data,peername):
        #--------------------------------------------------------------------------
        """ Handles the LISTPEERS message type. Message data is not used. """
        self.peers_list_lock.acquire()
        try:
            self.__debug('Listing peers %d' % self.numberofpeers())
            peerconn.send_data(REPLY, '%d' % self.numberofpeers())
            for pid in self.get_peers_list():
                host,port = self.getpeer(pid)
                peerconn.send_data(REPLY, '%s %s %d' % (pid, host, port))
        finally:
            self.peers_list_lock.release()
            
    #--------------------------------------------------------------------------
    def __handle_peername(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        """ Handles the NAME message type. Message data is not used. """
        peerconn.send_data(REPLY, self.myid)
 
    """--------------------------------------------END HANDLER FUNCTIONS---------------------------------"""
 
 
 
 
 
 
    """--------------------------------------------NODE CONTACT FUNCTIONS---------------------------------"""
     
    #--------------------------------------------------------------------------
    def contactbootstrap(self,messagetype,peername):
    #--------------------------------------------------------------------------
        """
         This function is called by all nodes when they want to start a game and it gets back all details for the game
        """
        host,port = self.bootstrap.split(":")
        if messagetype==GAME_START:
            resp = self.contact_peer_with_msg(host, port,messagetype,peername)
            self.__debug(str(resp))
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
        elif messagetype==LEAVING:
            print "In contact bootstrap"
            data=self.game_id+" "+self.my_peer_name+" "+self.player_num 
            resp = self.contact_peer_with_msg(host, port,messagetype,data)
            
        
    #--------------------------------------------------------------------------
    def multicast_to_peers(self,messagetype,peername):
    #--------------------------------------------------------------------------
        """
        This function is a common handler thats used to multicast messages to different players in the game. The messages
        can be of different types and are differentiated with a switch case
        """
        if messagetype==PEER_INFO_DETAILS:
            data = self.game_id+" "+peername+" "+self.player_num
            self.peers_list_lock.acquire()
            for key in self.peers:
                host,port=self.peers[key][0],self.peers[key][1]
                resp = self.contact_peer_with_msg(host, port,messagetype,data)
                if (resp[0][0] !=PEER_INFO_DETAILS):
                    return
                gameid,peername,player_number= resp[0][1].split()
                self.playernum_hostip_dict[player_number]=peername
                self.leader_list.append(player_number)
                self.message_queue[player_number] = {}
                self.message_queue[player_number]['move'] = Queue.Queue(0)
                self.message_queue[player_number]['bullet'] = Queue.Queue(0)
                self.flags_collected[player_number] = 0
                print "LOCAL PLAYER DICTIONARY"
                print self.playernum_hostip_dict
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
            host,port=self.bootstrap.split(":")
            self.contact_peer_with_msg(host,port,INFORM_GAME_END_BOOTSTRAP,data)     
            Game.show_winner_screen(self)       
            pygame.quit()
            sys.exit()
            
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
            data="STARTED"
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
    
    def multicast_to_peers_data(self, message_type, data):
        for key in self.playernum_hostip_dict:
            value = self.playernum_hostip_dict[key].split(":")
            host,port = value[0],value[1]
            print "Contacting peer", (host, port)
            self.contact_peer_with_msg(host, port, message_type, data) 

    """--------------------------------------------END NODE CONTACT FUNCTIONS---------------------------------"""

    def sort_and_assign_leader(self):
        self.leader_list_lock.acquire()
        if len(self.leader_list)>0:
                self.leader_list.sort()
                self.leader_num=self.leader_list[0]
        self.leader_list_lock.release()
          
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
                    if event.key == pygame.K_SPACE:
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
                    if event.key == pygame.K_SPACE:
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
    def main(self, screen):
    #--------------------------------------------------------------------------    
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
        self.flag_list[self.player_num]=flags((flag_cell.px,flag_cell.py),self.flag_layer)
        for entry in self.playernum_hostip_dict:
            if (entry != self.player_num):
                start_cell = self.tilemap.layers['player'].find('player')[int(entry)-1]
                flag_cell = self.tilemap.layers['flags'].find('flag')[int(entry)-1]
                self.enemy[entry]=enemies((start_cell.px,start_cell.py),entry,self.enemies)
                self.flag_list[entry]=flags((flag_cell.px,flag_cell.py),self.flag_layer)
        
        self.tilemap.layers.append(self.sprites)
        self.tilemap.layers.append(self.blockwall)
        self.tilemap.layers.append(self.enemies)
        self.tilemap.layers.append(self.players_sp)
        self.tilemap.layers.append(self.flag_layer)
        
        clock = pygame.time.Clock()
        while 1:
            dt=clock.tick(30)
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
            if (self.flags_collected[self.player_num] == len(self.playernum_hostip_dict)):
                self.multicast_to_peers(I_WIN, self.my_peer_name)
            
            self.tilemap.update(dt / 1000.,self)
            self.tilemap.draw(self.game_surface)
            #used to update the player list tab on the left with the right message contents
            self.show_on_screen_messages()
            
            screen.blit(self.game_surface,(210,0))
            screen.blit(self.player_surface.area, (5, 5))
            screen.blit(self.message_surface.area,(5,310))
            
            pygame.display.flip()        

if __name__=='__main__':
    if len(sys.argv) < 4:
        print "Syntax: %s server-port max-peers peer-ip:port" % sys.argv[0]
        sys.exit(-1)
    serverport = int(sys.argv[1])
    maxpeers = sys.argv[2]
    peerid = sys.argv[3]
    appl = Game(firstpeer=peerid, maxpeers=maxpeers, serverport=serverport)
    # the game is started for all nodes except the bootstrap node
    if appl.bootstrap!=peerid:
        appl.main(appl.screen)
