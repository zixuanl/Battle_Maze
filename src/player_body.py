#!/usr/bin/python
import sys
import math
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

class player(pygame.sprite.Sprite,Communicate):
    game_over='false'
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
    
        self.action_flag=-2 # MOVE = -1 , Fire = 1 , Bullet = 0
    
    def update(self,dt,game):
        if player.game_over=='true':
            game.show_loser_screen()
            self.kill()
        key=pygame.key.get_pressed()
        
        queue = game.message_queue[game.player_num]['bullet']
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
        
        queue = game.message_queue[game.player_num]['move']
        while queue.empty() != True:
            data = queue.get()
            print 'processing data...', data
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
        
        last_position = self.rect.copy()
        new = self.rect.copy()
        
        if key[pygame.K_RIGHT]:    
            new.x = new.x + 10
            self.direction = 1
            self.action_flag=-1
        
        elif key[pygame.K_LEFT]:
            new.x = new.x - 10
            self.direction=-1
            self.action_flag=-1
            
        elif key[pygame.K_UP]:
            new.y = new.y - 10
            self.direction=2
            self.action_flag=-1
           
        elif key[pygame.K_DOWN]:
            new.y = new.y + 10
            self.direction=-2
            self.action_flag=-1
        elif key[pygame.K_SPACE] and not self.guncooldown:
            self.action_flag = 1
            self.guncooldown = 1
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
            self.rect = last_position
        
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
        
        if self.action_flag==-1:
            data = str(game.player_num) + ' ' + str(new.x) + " " + str(new.y) + " " + str(self.direction)
            game.multicast_to_peers_data(MOVE, data)
        elif self.action_flag==1:
            data = str(game.player_num) + ' ' + str(self.direction)
            game.multicast_to_peers_data(FIRE, data)
        self.action_flag=-2