#!/usr/bin/python
import sys
import threading
from Tkinter import *
from random import *
from sample_app import *
from btpeer import *
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

class wall(pygame.sprite.Sprite):
    def __init__(self,location,*groups):
        super(wall,self).__init__(*groups)
        self.image=pygame.image.load("brick.png")
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
        self.image = pygame.image.load("bullet.png")
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
        self.image = pygame.image.load("bullet.png")
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
            print "He is so dead"

class enemies(pygame.sprite.Sprite):
    def __init__(self, location, *groups):
        super(enemies,self).__init__(*groups)
        self.image=pygame.image.load("up_tank.png")
        self.up_image = pygame.image.load("up_tank.png")
        self.left_image = pygame.image.load("left_tank.png")
        self.right_image = pygame.image.load("right_tank.png")
        self.down_image = pygame.image.load("down_tank.png")
        self.direction = 2
        self.rect=pygame.rect.Rect(location,self.image.get_size())
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
        game.tilemap.set_focus(new.x, new.y)
        
              
class player(pygame.sprite.Sprite):
    def __init__(self, location, *groups):
        super(player,self).__init__(*groups)
        self.image=pygame.image.load("up_tank.png")
        self.up_image = pygame.image.load("up_tank.png")
        self.left_image = pygame.image.load("left_tank.png")
        self.right_image = pygame.image.load("right_tank.png")
        self.down_image = pygame.image.load("down_tank.png")
        self.direction = 2
        self.rect=pygame.rect.Rect(location,self.image.get_size())
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
        for cell in game.tilemap.layers['collision'].collide(new,'blocker'):
            if last_position.right <= cell.left and new.right > cell.left:
                new.right = cell.left
            if last_position.left >= cell.right and new.left < cell.right:
                new.left = cell.right
            if last_position.bottom <= cell.top and new.bottom > cell.top:
                new.bottom = cell.top
            if last_position.top >= cell.bottom and new.top < cell.bottom:
                new.top = cell.bottom
        game.tilemap.set_focus(new.x, new.y)

class Game(object,BTPeer):
    def __init__( self, firstpeer,maxpeers=5, serverport=12345, master=None ):
        
        BTPeer.__init__(self, maxpeers, serverport)
        handlers = {LISTPEERS : self.__handle_listpeers,INSERTPEER : self.__handle_insertpeer,PEERNAME: self.__handle_peername,PLAYER_LIST:self.__handle_playerlist,
                    MOVE: self.__handle_move,FIRE: self.__handle_fire,OBSTACLE: self.__handle_obstacle,PEERQUIT: self.__handle_quit,GAME_START: self.__handle_gamestart,
                    PEER_INFO_DETAILS: self.__peer_info_details}
        for mt in handlers:
            self.addhandler(mt, handlers[mt])
        
        self.map=" "
        self.number_peers=0
        self.player_num=-1
        self.my_peer_name=firstpeer
        self.enemy={}
        
        host,port = firstpeer.split(':')
        t = threading.Thread( target = self.mainloop, args = [] )
        t.start()  
        self.startstabilizer( self.checklivepeers, 3 )
        if firstpeer!=self.bootstrap:
            self.contactbootstrap(firstpeer)
            if(self.number_peers>0):
                self.contactpeers(firstpeer)
     
    def onDestroy(self):
        self.shutdown = True     
    
    def __debug(self, msg):
        if self.debug:
            btdebug(msg)
 
    """There are different handlers based on the type of the event that occurs. The below functions are all handlers"""   
    
    """Function that chooses the Map and other details and sends it back to the user"""
    """DETAILS contain - game-id,MAP,Number of peers and X,Y position"""
    """GAME contains list of peers"""
    def __handle_gamestart(self, peerconn,data,peername):

        print data
        if(self.game_id in self.game_dict):
            print "GAME ID PRESENT"
            player_number = len(self.game_dict[self.game_id])+1
            if(len(self.game_dict[self.game_id])<=3):
                peerconn.senddata(DETAILS,'%d %s %d %d' % (self.game_id,self.gameid_map_dict[self.game_id],len(self.game_dict[self.game_id]),player_number))
                for peer_list in self.game_dict[self.game_id]:
                    peerconn.senddata(PLAYER_LIST,'%s %s %d' % (peer_list,peer_list.split(":")[0],int(peer_list.split(":")[1])))
                self.game_dict[self.game_id].append(data)
                if(len(self.game_dict[self.game_id])==4):
                    self.game_id=self.game_id+1
            print "Game dictionary is :"
            print self.game_dict[self.game_id]
        
        else:
            print "GAME ID NOT PRESENT"
            map_id=random.randint(1, 4)
            print self.available_maps_dict[map_id]    
            self.game_dict[self.game_id]=[]
            player_number = len(self.game_dict[self.game_id])+1
            peerconn.senddata(DETAILS,'%d %s %d %d' % (self.game_id,self.available_maps_dict[map_id],len(self.game_dict[self.game_id]), player_number))
            self.game_dict[self.game_id].append(data)
            self.gameid_map_dict[self.game_id]=self.available_maps_dict[map_id]

            print "Game_id_map is :"
            print self.gameid_map_dict
            print "Game dictionary is :"
            print self.game_dict[self.game_id]

    def contactbootstrap(self,peername):
        host,port = self.bootstrap.split(":")
        resp = self.connectandsend(host, port,"GAME",peername)
        print len(resp),resp
        self.__debug(str(resp))
        if (resp[0][0] != DETAILS):
            return
        self.game_id,self.map,self.number_peers,self.player_num=resp[0][1].split()
        print self.player_num
        x=1
        for x in range(1,1+int(self.number_peers)):
            if (resp[x][0] != PLAYER_LIST):
                return 
            data=resp[x][1]
            self.peerlock.acquire()
            try:
                try:
                    peerid,host,port = data.split()
                    if peerid not in self.getpeerids() and peerid != self.myid:
                        self.addpeer(peerid, host, port)
                        self.__debug('added peer: %s' % peerid)
                    else:
                        print ('Join: peer already inserted %s' % peerid)
                except:
                    self.__debug('invalid insert %s: %s' % (str(12345), data))
            finally:
                self.peerlock.release()
    
    def contactpeers(self,peername):
        data = self.game_id+" "+peername+" "+self.player_num
        for key in self.peers:
            host,port=self.peers[key][0],self.peers[key][1]
            resp = self.connectandsend(host, port,PEER_INFO_DETAILS,data)
            if (resp[0][0] !=PEER_INFO_DETAILS):
                return
            gameid,peername,player_number= resp[0][1].split()
            self.playernum_hostip_dict[player_number]=peername
            print "LOCAL PLAYER DICTIONARY"
            print self.playernum_hostip_dict
            
    def __peer_info_details(self,peerconn,data,peername):
        gameid,peername,player_number= data.split()
        if(gameid!=self.game_id):
            print "wrong game. Something wrong with bootstrapping"
            peerconn.senddata(ERROR, 'Game ID different %s' % self.game_id)
            return
        if(player_number in self.playernum_hostip_dict):
            peerconn.senddata(ERROR, 'Player number already present %s' % self.game_id)
            return
        self.playernum_hostip_dict[player_number]=peername
        peerconn.senddata(PEER_INFO_DETAILS,'%s %s %s' % (self.game_id,self.my_peer_name,self.player_num))
        print "LOCAL PLAYER DICTIONARY"
        print self.playernum_hostip_dict
    
    def __handle_move(self,peerconn,data,peername):
        print ""
    
    def __handle_fire(self,peerconn,data,peername):
        print ""
    
    def __handle_obstacle(self,peerconn,data,peername):
        print ""
        
    def __handle_quit(self,peerconn,data,peername):
        print ""
    
    def __handle_playerlist(self,peerconn,data,peername):
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
        print "BYE"
        print self.peers
    
    def __handle_insertpeer(self, peerconn, data,peername):
        print " "
    
    def __handle_listpeers(self, peerconn, data,peername):
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
    def __handle_peername(self,peerconn,data,peername):
        """ Handles the NAME message type. Message data is not used. """
        peerconn.senddata(REPLY, self.myid)
    
    def main(self, screen):
        clock = pygame.time.Clock()

        background = pygame.image.load('background.png')
        self.tilemap = tmx.load(self.map, screen.get_size())
        self.sprites = tmx.SpriteLayer()
        self.enemies = tmx.SpriteLayer()
        start_cell = self.tilemap.layers['collision'].find('player')[int(self.player_num)-1]
        self.player1 = player((start_cell.px, start_cell.py), self.sprites)
        for entry in self.playernum_hostip_dict:
            start_cell = self.tilemap.layers['collision'].find('player')[int(entry)-1]
            self.enemy[entry]=enemies((start_cell.px,start_cell.py),self.enemies)
        self.blockwall = tmx.SpriteLayer()
        self.tilemap.layers.append(self.sprites)
        self.tilemap.layers.append(self.blockwall)
        self.tilemap.layers.append(self.enemies)

        while 1:
            dt=clock.tick(20)
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
    #add code here to make all process wait before starting the game
    if appl.bootstrap!=peerid:
        pygame.init()
        screen = pygame.display.set_mode((800, 800))
        print screen.get_size()
        appl.main(screen)
        appl.onDestroy()
        