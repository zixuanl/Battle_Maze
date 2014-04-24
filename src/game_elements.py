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

class flags(pygame.sprite.Sprite):
    def __init__(self,location,flag_num,*groups):
        super(flags,self).__init__(*groups)
        self.image = pygame.image.load("game_items/flag.png")
        self.rect = pygame.rect.Rect(location,self.image.get_size())
        self.flag_num = flag_num
     
    def update(self,dt,game):
        queue = game.message_queue[self.flag_num]['flag']
        while queue.empty() != True:
            data = queue.get()
            self.kill()
            
        if pygame.sprite.spritecollide(self, game.players_sp,False):
            #game.flags_collected = game.flags_collected+1
            print 'flags collected!'
            data = game.player_num + ' ' + str(self.flag_num)
            game.multicast_to_peers_data(FLAG, data)
            self.kill()
    
class fire(pygame.sprite.Sprite):
    def __init__(self,location,direction,*groups):
        super(fire,self).__init__(*groups)
        self.image = pygame.image.load("game_items/bullet.png")
        self.rect=pygame.rect.Rect(location,self.image.get_size())
        self.direction=direction
        self.lifespan=1

    def update(self, dt, game):
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
        self.lifespan -= dt
        if self.lifespan < 0:
            self.kill()
            return
        if self.direction==2:
            self.rect.y +=-1*400 * dt
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
