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
GAME_START="GAME" # send to bootstrap to get game details
DETAILS="DETL" # bootstrap replies with this as first message followed by PLAYER_LIST messages
PEER_INFO_DETAILS="INFO" # Request for information from peer after getting the list from bootstrap
PLAY_START="PSTA"

class wall(pygame.sprite.Sprite):
    def __init__(self,location,*groups):
        super(wall,self).__init__(*groups)
        self.image=pygame.image.load("game_items/brick.png")
        self.rect=pygame.rect.Rect(location,self.image.get_size())
        self.lifespan=50
    def update(self, dt, game):
        self.lifespan -= dt
        if self.lifespan < 0:
            self.kill()
            return
         
class fire(pygame.sprite.Sprite):
    def __init__(self,location,direction,*groups):
        super(fire,self).__init__(*groups)
        self.image = pygame.image.load("game_items/bullet.png")
        self.rect=pygame.rect.Rect(location,self.image.get_size())
        self.direction=direction
        self.lifespan=1

    def update(self, dt, game):
        print self.lifespan
        self.lifespan -= dt
        if self.lifespan < 0:
            wall((self.rect.x,self.rect.y),game.blockwall)
            self.kill()
            return
        else:
            if self.direction==2:
                self.rect.y +=-1*400 * dt
                print self.rect.y
            elif self.direction==-2:
                self.rect.y +=400 * dt
            elif self.direction==1:
                self.rect.x += self.direction * 400 * dt
            elif self.direction==-1:
                self.rect.x += self.direction * 400 * dt

class bullet(pygame.sprite.Sprite):
    def __init__(self,location,direction,*groups):
        super(bullet,self).__init__(*groups)
        self.image = pygame.image.load("game_items/bullet.png")
        self.rect=pygame.rect.Rect(location,self.image.get_size())
        self.direction=direction
        self.lifespan=1
    
    def update(self, dt, game):
        print self.lifespan
        self.lifespan -= dt
        if self.lifespan < 0:
            self.kill()
            return
        if self.direction==2:
            self.rect.y +=-1*400 * dt
            print self.rect.y
        elif self.direction==-2:
            self.rect.y +=400 * dt
        elif self.direction==1:
            self.rect.x += self.direction * 400 * dt
        elif self.direction==-1:
            self.rect.x += self.direction * 400 * dt
        new = self.rect
        if game.tilemap.layers['collision'].collide(new,'blocker'):
            self.kill()
        if pygame.sprite.spritecollide(self, game.blockwall,False):
            self.kill()
        if pygame.sprite.spritecollide(self, game.enemies,True):
            self.kill()
            print "Enemy Dead"
        if pygame.sprite.spritecollide(self, game.players_sp,True):
            self.kill()
            print "Player Dead"

class enemies(pygame.sprite.Sprite,Communicate):
    def __init__(self, location,player_num, *groups):
        Communicate.__init__(self)
        super(enemies,self).__init__(*groups)
        self.image=pygame.image.load(self.player_tank_map[player_num]['up'])
        self.up_image = pygame.image.load(self.player_tank_map[player_num]['up'])
        self.left_image = pygame.image.load(self.player_tank_map[player_num]['left'])
        self.right_image = pygame.image.load(self.player_tank_map[player_num]['right'])
        self.down_image = pygame.image.load(self.player_tank_map[player_num]['down'])
        self.direction = 2
        self.rect=pygame.rect.Rect(location,(self.image.get_width()-4,self.image.get_height()-4))
        self.guncooldown=0
        self.blockwallcooldown=0
        self.firecount=5
        
    def update(self,dt,game):
        key=pygame.key.get_pressed()
        last_position = self.rect.copy()
        
        if key[pygame.K_d]:
            self.rect.x+=10
            self.image=self.right_image
            self.direction=1
        elif key[pygame.K_a]:
            self.rect.x-=10
            self.image=self.left_image
            self.direction=-1
        elif key[pygame.K_w]:
            self.rect.y-=10
            self.image=self.up_image
            self.direction=2
        elif key[pygame.K_s]:
            self.rect.y+=10
            self.image=self.down_image
            self.direction=-2
        elif key[pygame.K_r] and not self.guncooldown:
            if self.direction==2:
                bullet(self.rect.midtop,2,game.sprites)
            elif self.direction==-2:
                bullet(self.rect.midbottom,-2,game.sprites)
            elif self.direction==-1:
                bullet(self.rect.midleft,-1,game.sprites)
            elif self.direction==1:
                bullet(self.rect.midright,1,game.sprites)
            self.guncooldown=1
        self.guncooldown = max(0, self.guncooldown - dt)
        
        if key[pygame.K_t] and self.firecount>0 and not self.blockwallcooldown:
            if self.direction==2:
                fire(self.rect.midtop,2,game.sprites)
            elif self.direction==-2:
                fire(self.rect.midbottom,-2,game.sprites)
            elif self.direction==-1:
                fire(self.rect.midleft,-1,game.sprites)
            elif self.direction==1:
                fire(self.rect.midright,1,game.sprites)
            self.blockwallcooldown=1
            self.firecount-=1
        self.blockwallcooldown=max(0,self.blockwallcooldown-dt)
        if pygame.sprite.spritecollide(self, game.blockwall,False):
            self.rect=last_position
        new = self.rect
        for cell in game.tilemap.layers['collision'].collide(new,'blocker'):
            if last_position.right <= cell.left and new.right > cell.left:
                new.right = cell.left
            if last_position.left >= cell.right and new.left < cell.right:
                new.left = cell.right
            if last_position.bottom <= cell.top and new.bottom > cell.top:
                new.bottom = cell.top
            if last_position.top >= cell.bottom and new.top < cell.bottom:
                new.top = cell.bottom
        #  game.tilemap.set_focus(new.x, new.y)
        
              
class player(pygame.sprite.Sprite,Communicate):
    def __init__(self, location,player_num,*groups):
        Communicate.__init__(self)
        super(player,self).__init__(*groups)
        self.image=pygame.image.load(self.player_tank_map[player_num]['up'])
        self.up_image = pygame.image.load(self.player_tank_map[player_num]['up'])
        self.left_image = pygame.image.load(self.player_tank_map[player_num]['left'])
        self.right_image = pygame.image.load(self.player_tank_map[player_num]['right'])
        self.down_image = pygame.image.load(self.player_tank_map[player_num]['down'])
        self.direction = 2
        self.rect=pygame.rect.Rect(location,(self.image.get_width()-4,self.image.get_height()-4))
        self.guncooldown=0
        self.blockwallcooldown=0
        self.firecount=5
        
    def update(self,dt,game):
        key=pygame.key.get_pressed()
        last_position = self.rect.copy()
        if key[pygame.K_RIGHT]:
            self.rect.x+=10
            self.image=self.right_image
            self.direction=1
        elif key[pygame.K_LEFT]:
            self.rect.x-=10
            self.image=self.left_image
            self.direction=-1
        elif key[pygame.K_UP]:
            self.rect.y-=10
            self.image=self.up_image
            self.direction=2
        elif key[pygame.K_DOWN]:
            self.rect.y+=10
            self.image=self.down_image
            self.direction=-2
        elif key[pygame.K_SPACE] and not self.guncooldown:
            if self.direction==2:
                bullet(self.rect.midtop,2,game.sprites)
            elif self.direction==-2:
                bullet(self.rect.midbottom,-2,game.sprites)
            elif self.direction==-1:
                bullet(self.rect.midleft,-1,game.sprites)
            elif self.direction==1:
                bullet(self.rect.midright,1,game.sprites)
            self.guncooldown=1
        self.guncooldown = max(0, self.guncooldown - dt)
        
        if key[pygame.K_LSHIFT] and self.firecount>0 and not self.blockwallcooldown:
            if self.direction==2:
                fire(self.rect.midtop,2,game.sprites)
            elif self.direction==-2:
                fire(self.rect.midbottom,-2,game.sprites)
            elif self.direction==-1:
                fire(self.rect.midleft,-1,game.sprites)
            elif self.direction==1:
                fire(self.rect.midright,1,game.sprites)
            self.blockwallcooldown=1
            self.firecount-=1
        self.blockwallcooldown=max(0,self.blockwallcooldown-dt)
        if pygame.sprite.spritecollide(self, game.blockwall,False):
            self.rect=last_position
        new = self.rect
        for cell in game.tilemap.layers['collision'].collide(new,"blocker"):
            if last_position.right <= cell.left and new.right > cell.left:
                new.right = cell.left
            if last_position.left >= cell.right and new.left < cell.right:
                new.left = cell.right
            if last_position.bottom <= cell.top and new.bottom > cell.top:
                new.bottom = cell.top
            if last_position.top >= cell.bottom and new.top < cell.bottom:
                new.top = cell.bottom
        game.tilemap.set_focus(new.x, new.y)

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
                    PEERNAME: self.__handle_peername,MOVE: self.__handle_move,
                    FIRE: self.__handle_fire,OBSTACLE: self.__handle_obstacle,
                    PEERQUIT: self.__handle_quit,GAME_START: self.__handle_gamestart,
                    PEER_INFO_DETAILS: self.__peer_info_details,PLAY_START: self.__play_start
                    }
        for mt in handlers:
            self.add_event_handler(mt, handlers[mt])
        
        
        self.map=" " # signifies the current map to be used
        self.number_peers=0 # This is the number of peers returned by the bootstrap node
        self.player_num=-1 # The player_num returned by the bootstrap node
        self.my_peer_name=firstpeer # Your own host:port 
        self.enemy={} # list of all other player objects that are instanciated later
        
        host,port = firstpeer.split(':')
        t = threading.Thread( target = self.mainloop, args = [] )
        t.start()  
        self.startstabilizer( self.checklivepeers, 3 )
        # A bootstrap node should only help in bootstrapping. So all this is not needed for it
        if firstpeer!=self.bootstrap:
            self.contactbootstrap(firstpeer) #contact bootstrap to get required information
            pygame.init()
            self.screen = pygame.display.set_mode((1024, 624))
            # The first node to join the game is given the option to start the game. All others wait for him to start
            if int(self.number_peers) > 0:
                self.contactpeers(firstpeer)
                self.showstartscreen_rest()    
            elif int(self.number_peers)==0: #first node to join the game
                self.showstartscreen_first()
                #once he starts, convey information to all peers so that they can start too
                self.convey_play_start(firstpeer)
                self.play_start=True
                
     
    #--------------------------------------------------------------------------
    def onDestroy(self):
    #--------------------------------------------------------------------------
        self.shutdown = True     
    
    #--------------------------------------------------------------------------
    def __debug(self, msg):
    #--------------------------------------------------------------------------
        if self.debug:
            btdebug(msg)
 
    
    
    
    """
    There are different handlers based on the type of the event that occurs. The below functions are all handlers
    """   
    
    
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
            #Check if there is already a game with lesser than 4 users. If so add the user to it. If not create new game
            if(self.game_id in self.game_dict):
                print "GAME ID PRESENT"
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
                print "GAME ID NOT PRESENT"
                map_id=random.randint(1, 4)
                print self.available_maps_dict[map_id]    
                self.game_dict[self.game_id]=[]
                player_number = len(self.game_dict[self.game_id])+1
                peerconn.send_data(DETAILS,'%d %s %d %d' % (self.game_id,self.available_maps_dict[map_id],len(self.game_dict[self.game_id]), player_number))
                self.game_dict[self.game_id].append(data)
                self.gameid_map_dict[self.game_id]=self.available_maps_dict[map_id]
    
                print "Game_id_map is :"
                print self.gameid_map_dict
                print "Game dictionary is :"
                print self.game_dict[self.game_id]
        else:
                print "INFORM GAME START"
                self.game_id=self.game_id+1
                peerconn.send_data(REPLY,'OK')
        
    #--------------------------------------------------------------------------
    def contactbootstrap(self,peername):
    #--------------------------------------------------------------------------
        """
         This function is called by all nodes when they want to start a game and it gets back all details for the game
        """
        host,port = self.bootstrap.split(":")
        resp = self.contact_peer_with_msg(host, port,GAME_START,peername)
        print len(resp),resp
        self.__debug(str(resp))
        if (resp[0][0] != DETAILS):
            return
        #Get back game id, no:of peers,player_num and player list
        self.game_id,self.map,self.number_peers,self.player_num=resp[0][1].split()
        x=1
        for x in range(1,1+int(self.number_peers)):
            if (resp[x][0] != PLAYER_LIST):
                return 
            data=resp[x][1]
            self.peerlock.acquire()
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
                self.peerlock.release()
    
    #--------------------------------------------------------------------------
    def contactpeers(self,peername):
    #--------------------------------------------------------------------------
        """
        contact the peers to update each others information. Exchange game-id,peername and player_num
        """  

        data = self.game_id+" "+peername+" "+self.player_num
        for key in self.peers:
            host,port=self.peers[key][0],self.peers[key][1]
            resp = self.contact_peer_with_msg(host, port,PEER_INFO_DETAILS,data)
            if (resp[0][0] !=PEER_INFO_DETAILS):
                return
            gameid,peername,player_number= resp[0][1].split()
            self.playernum_hostip_dict[player_number]=peername
            print "LOCAL PLAYER DICTIONARY"
            print self.playernum_hostip_dict
    
    
    #--------------------------------------------------------------------------
    def convey_play_start(self,peername):
    #--------------------------------------------------------------------------
        """
         This function is called by the first node to join the game and informs other nodes as part of the game to start 
         the game. The nodes receiving this will set their play_start variable to true
        """
        
        data = "START GAME"
        i=0
        for key in self.playernum_hostip_dict:
            host,port=self.playernum_hostip_dict[key].split(":")
            resp = self.contact_peer_with_msg(host, port,PLAY_START,data)
            if(resp[0][0]==REPLY):
                i=i+1
        # print "ACKS NEEDED = " + str(len(self.playernum_hostip_dict)) +" ACKS RECEIVED = "+str(i)
        host,port = self.bootstrap.split(":")
        data="STARTED"
        resp = self.contact_peer_with_msg(host, port,GAME_START,data)
    
    #--------------------------------------------------------------------------
    def showstartscreen_first(self):
    #--------------------------------------------------------------------------
        """
         Shows the start screen for the first node. The screen shows battle maze with list of hosts available and a message
         saying "press space to accept and start"
        """
        background=pygame.image.load("title/battlemaze_leader.png").convert()
        background = pygame.transform.scale(background, (1024,624))
        font = pygame.font.Font('freesansbold.ttf', 20)
        hosts="Hosts Joined : "
        while 1:
            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        return
            for key in self.playernum_hostip_dict:
                hosts =hosts+str(self.playernum_hostip_dict[key])+" "
            text = font.render(hosts, True,(178,34,34),(46,139,87))
            textpos = text.get_rect()
            textpos.bottomleft = background.get_rect().bottomleft
            textpos.bottomleft=background.get_rect().bottomleft
            background.blit(text, textpos)
            self.screen.blit(background, (0, 0))
            pygame.display.flip()
            hosts="Hosts Joined : "
    
    #--------------------------------------------------------------------------    
    def showstartscreen_rest(self):
    #--------------------------------------------------------------------------
        """
        This is the start screen for all other nodes. The start screen shows a list of all hosts in the game and a message
        saying "awaiting approval". Once the first node in the game presses space, this function exits.
        """
        background=pygame.image.load("title/battlemaze_peers.png").convert()
        background = pygame.transform.scale(background, (1024,624))
        font = pygame.font.Font('freesansbold.ttf', 20)
        hosts="Hosts Joined : "
        while self.play_start!=True:
            for key in self.playernum_hostip_dict:
                hosts =hosts+str(self.playernum_hostip_dict[key])+" "
            text = font.render(hosts, True,(178,34,34),(46,139,87))
            textpos = text.get_rect()
            textpos.bottomleft = background.get_rect().bottomleft
            textpos.bottomleft=background.get_rect().bottomleft
            background.blit(text, textpos)
            self.screen.blit(background, (0, 0))
            pygame.display.flip()
            hosts="Hosts Joined : "
          
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
        if(player_number in self.playernum_hostip_dict):
            peerconn.send_data(ERROR, 'Player number already present %s' % self.game_id)
            return
        self.playernum_hostip_dict[player_number]=peername
        peerconn.send_data(PEER_INFO_DETAILS,'%s %s %s' % (self.game_id,self.my_peer_name,self.player_num))
    
    #--------------------------------------------------------------------------    
    def __handle_move(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        print ""
    
    #--------------------------------------------------------------------------    
    def __handle_fire(self,peerconn,data,peername):
    #--------------------------------------------------------------------------        
        print ""
    
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
    def __handle_listpeers(self, peerconn, data,peername):
        #--------------------------------------------------------------------------
        """ Handles the LISTPEERS message type. Message data is not used. """
        self.peerlock.acquire()
        try:
            self.__debug('Listing peers %d' % self.numberofpeers())
            peerconn.send_data(REPLY, '%d' % self.numberofpeers())
            for pid in self.get_peers_list():
                host,port = self.getpeer(pid)
                peerconn.send_data(REPLY, '%s %s %d' % (pid, host, port))
        finally:
            self.peerlock.release()
            
    #--------------------------------------------------------------------------
    def __handle_peername(self,peerconn,data,peername):
    #--------------------------------------------------------------------------    
        """ Handles the NAME message type. Message data is not used. """
        peerconn.send_data(REPLY, self.myid)
    
    #--------------------------------------------------------------------------
    def main(self, screen):
    #--------------------------------------------------------------------------    
        """
        The main function that actually starts the game
        """
        clock = pygame.time.Clock()

        background = pygame.image.load('title/background.png')
        self.tilemap = tmx.load(self.map, screen.get_size())
        print "LOAD FINISHED"
        self.sprites = tmx.SpriteLayer()
        self.enemies = tmx.SpriteLayer()
        self.players_sp = tmx.SpriteLayer()
        self.blockwall = tmx.SpriteLayer()
        
        start_cell = self.tilemap.layers['player'].find('player')[int(self.player_num)-1]
        self.player1 = player((start_cell.px, start_cell.py),self.player_num,self.players_sp)
        for entry in self.playernum_hostip_dict:
            start_cell = self.tilemap.layers['player'].find('player')[int(entry)-1]
            self.enemy[entry]=enemies((start_cell.px,start_cell.py),entry,self.enemies)
        
        self.tilemap.layers.append(self.sprites)
        self.tilemap.layers.append(self.blockwall)
        self.tilemap.layers.append(self.enemies)
        self.tilemap.layers.append(self.players_sp)
        

        while 1:
            dt=clock.tick(40)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                    return
            self.tilemap.update(dt / 1000.,self)
            screen.blit(background, (0, 0))
            self.tilemap.draw(screen)
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
        appl.onDestroy()