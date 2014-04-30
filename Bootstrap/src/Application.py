'''
Created on Apr 19, 2014

@author: arvindbalaji
'''
from Framework import *
import random
import sys
import time

PLAYER_LIST="PLAY"
REPLY = "REPL"
ERROR = "ERRO"
GAME_START="GAME" # send to bootstrap to get game details
DETAILS="DETL" # bootstrap replies with this as first message followed by PLAYER_LIST messages
PLAY_START="PSTA"
INFORM_GAME_END_BOOTSTRAP="OVER"
LEAVING = "LEAV"
DROP_NODE = "DROP"
DEAD_NODE = "DEAD"

MAX_PLAYER_NUMBER=6

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
        
        handlers = {
                GAME_START:self.__handle_gamestart,
                INFORM_GAME_END_BOOTSTRAP: self.__handle_game_end_bootstrap,
                LEAVING:self.__handle_player_leaving_gracious,
                DROP_NODE: self.__handle_player_leaving_suddenly
                    }
       
        self.my_peer_name=firstpeer
        for mt in handlers:
            self.add_event_handler(mt, handlers[mt])
        self.t = threading.Thread( target = self.mainloop, args = [] )
        self.t.start()
        
        self.rejoin_thread_dict={}
   
    #--------------------------------------------------------------------------
    def __handle_drop_node(self,peerconn,data,peername):
    #--------------------------------------------------------------------------  

        print "Got Drop message"

        #This is where you need to deal with the lost node
        #This data contains ip:host of the lost node 
        print data


          
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
        if data in self.rejoin_thread_dict:
            temp_list=self.rejoin_thread_dict.pop(data)
            game_id=temp_list[1]
            player_number=temp_list[2]
            self.game_dict[int(game_id)].append(data)
            peerconn.send_data(DETAILS,'%d %s %d %d' % (int(game_id),self.gameid_map_dict[int(game_id)],len(self.game_dict[int(game_id)])-1,int(player_number)))
            for peer_list in self.game_dict[int(game_id)]:
                if peer_list!=data:
                    peerconn.send_data(PLAYER_LIST,'%s %s %d' % (peer_list,peer_list.split(":")[0],int(peer_list.split(":")[1])))
        else:
            # This condition is hit when nodes require initial set up details
            print "in else of game start" , data
            if not "STARTED" in data:
                self.game_dict_lock.acquire()
                #Check if there is already a game with lesser than 4 users. If so add the user to it. If not create new game
                if(self.game_id in self.game_dict):
                    player_number = len(self.game_dict[self.game_id])+1
                    if(len(self.game_dict[self.game_id])<=MAX_PLAYER_NUMBER-1):
                        peerconn.send_data(DETAILS,'%d %s %d %d' % (self.game_id,self.gameid_map_dict[self.game_id],len(self.game_dict[self.game_id]),player_number))
                        for peer_list in self.game_dict[self.game_id]:
                            peerconn.send_data(PLAYER_LIST,'%s %s %d' % (peer_list,peer_list.split(":")[0],int(peer_list.split(":")[1])))
                        self.game_dict[self.game_id].append(data)
                        if(len(self.game_dict[self.game_id])==MAX_PLAYER_NUMBER):
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
                    message,game_id = data.split(" ")
                    if int(game_id)==int(self.game_id) and len(self.game_dict[self.game_id])!=MAX_PLAYER_NUMBER:
                        self.game_id=self.game_id+1
                        print "GAME ID" , self.game_id
                    peerconn.send_data(REPLY,'OK')
                
    #-------------------------------------------------------------------------- 
    def __handle_player_leaving_gracious(self,peerconn,data,peername):
    #--------------------------------------------------------------------------     
       
        players_game_id,peer_name,player_num,play_start= data.split(" ") 
        if play_start=="False":
                self.game_dict_lock.acquire()
                if peer_name in self.game_dict[int(players_game_id)]:
                    print " GAME DICT BEFORE REMOVING"
                    print self.game_dict[int(players_game_id)]
                    if len(self.game_dict[int(players_game_id)])==MAX_PLAYER_NUMBER:
                        self.game_id=self.game_id-1
                    self.game_dict[int(players_game_id)].remove(peer_name)
                    print " GAME DICT AFTER REMOVING"
                    print self.game_dict[int(players_game_id)]
                self.game_dict_lock.release()
        elif play_start=="True":
            
            if peer_name=="128.237.224.170:12341" or peer_name=="128.237.224.170:12342":
                print " In rejoin test case"
                print "DATA ",data
                self.__handle_player_leaving_suddenly(peerconn, data, peername)
                return
            
            print "peer_name"+" popped"
            if peer_name in self.game_dict[int(players_game_id)]:
                        self.game_dict[int(players_game_id)].remove(peer_name)
            print " GAME DICT AFTER REMOVING"
            print self.game_dict[int(players_game_id)]
 
  
    #--------------------------------------------------------------------------
    def __handle_game_end_bootstrap(self,peerconn,data,peername):
    #--------------------------------------------------------------------------  
        gameid,winnername,winnerid=data.split(" ")
        print "GAME END"
        print self.game_dict
        if int(gameid) in self.game_dict:
            del self.game_dict[int(gameid)]
        print self.game_dict
    
    #--------------------------------------------------------------------------
    def __handle_player_leaving_suddenly(self,peerconn,data,peername):
    #--------------------------------------------------------------------------         
    
        print "DATA IN LEAVING",data
        gameid,peer_address,player_number = data.split(" ")
        print gameid,peer_address,player_number
        
        self.rejoin_thread_dict[peer_address]=[threading.Thread(target=self.rejoin_thread_time,args=[peer_address]),gameid,player_number]
        print self.rejoin_thread_dict[peer_address]
        self.game_dict[int(gameid)].remove(peer_address)
        print self.game_dict
        self.rejoin_thread_dict[peer_address][0].start()
        
    #--------------------------------------------------------------------------
    def rejoin_thread_time(self,peername):
    #--------------------------------------------------------------------------  
        
        time.sleep(40)
        print 'timeout: delete it from the game', peername
        print self.rejoin_thread_dict
        if peername in self.rejoin_thread_dict:
            temp_list=self.rejoin_thread_dict.pop(peername)
            players_game_id = temp_list[1]       
    #--------------------------------------------------------------------------
    def main(self, screen):
    #--------------------------------------------------------------------------    
        print "Starting Bootstrap"

if __name__=='__main__':
    if len(sys.argv) < 4:
        print "Syntax: %s server-port max-peers peer-ip:port" % sys.argv[0]
        sys.exit(-1)
    serverport = int(sys.argv[1])
    maxpeers = sys.argv[2]
    peerid = sys.argv[3]
    appl = Game(firstpeer=peerid, maxpeers=maxpeers, serverport=serverport)
