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
import game_elements
from game_elements import *

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
I_WIN = "IWIN"
I_LOST="LOST"
INFORM_GAME_END_BOOTSTRAP="OVER"



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
        self.alive=True
        self.player_num = player_num
    def update(self,dt,game):
        
        if self.alive==False:
            self.kill()
        
        key=pygame.key.get_pressed()
        last_position = self.rect.copy()
        
        #print 'enemy number:', self.player_num
        
        queue = game.message_queue[self.player_num]['bullet']
        while queue.empty() != True:
            data = queue.get()
            direction = int(data)
            if direction == 2:
                bullet(self.rect.midtop,2,game.sprites)
            elif direction == -2:
                bullet(self.rect.midbottom,-2,game.sprites)
            elif direction == -1:
                bullet(self.rect.midleft,-1,game.sprites)
            elif direction == 1:
                bullet(self.rect.midright,1,game.sprites)
        
        queue = game.message_queue[self.player_num]['move']
        while queue.empty() != True:
            data = queue.get()
            print 'processing data for enemy...', data
            x, y, direction = data.split(' ')
            print x, y, direction
            self.rect.x = int(x)
            self.rect.y = int(y)
            if int(direction) == 1:
                self.image = self.right_image
                self.direction = 1
            elif int(direction) == -1:
                self.image = self.left_image
                self.direction = -1
            elif int(direction) == 2:
                self.image=self.up_image
                self.direction = 2
            elif int(direction) == -2:
                self.image = self.down_image
                self.direction = -2
        """       
        if key[pygame.K_d]:
            data = str(self.player_num) + ' ' + str(self.rect.x + 10) + " " + str(self.rect.y) + " " + str(1);
            game.multicast_to_peers_data(MOVE, data)
        elif key[pygame.K_a]:
            data = str(self.player_num) + ' ' + str(self.rect.x - 10) + " " + str(self.rect.y) + " " + str(-1)
            game.multicast_to_peers_data(MOVE, data)
        elif key[pygame.K_w]:
            data = str(self.player_num) + ' ' + str(self.rect.x) + " " + str(self.rect.y - 10) + " " + str(2)
            game.multicast_to_peers_data(MOVE, data)
        elif key[pygame.K_s]:
            data = str(self.player_num) + ' ' + str(self.rect.x) + " " + str(self.rect.y + 10) + " " + str(-2)
            game.multicast_to_peers_data(MOVE, data)
        elif key[pygame.K_r] and not self.guncooldown:
            data = str(self.player_num) + ' ' + str(self.direction)
            game.multicast_to_peers_data(FIRE, data)
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
        """