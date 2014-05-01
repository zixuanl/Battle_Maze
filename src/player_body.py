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
        self.start_rect = self.rect.copy()
        self.guncooldown=0
        self.blockwallcooldown=0
        self.firecount=5
        self.alive = True
        self.killed = False
    
        self.action_flag=-1 # MOVE = 0 , Fire = 1, Bullet = 2
    
    def update(self,dt,game):
        #print 'updating...'
        
        if self.alive == False:
            print 'Player', game.player_num, 'is dead'
            print 'Flags in his hand', game.flags_collected[game.player_num]
            for flag_num in game.flags_collected[game.player_num]:
                flag_cell = game.tilemap.layers['flags'].find('flag')[int(flag_num)-1]
                game.flag_list[flag_num] = flags((flag_cell.px,flag_cell.py),flag_num,game.flag_layer)
            game.tilemap.layers.append(game.flag_layer)
            del game.flags_collected[game.player_num]
            self.kill()
            game.tilemap.layers.append(game.players_sp)
            return
            
        if self.killed == True:
            self.killed = False
            print 'Player', game.player_num, 'is killed: ', self.killer, 'is the killer'
            self.rect = self.start_rect.copy()
            game.flags_collected[self.killer].extend(game.flags_collected[game.player_num])
            game.flags_collected[game.player_num] = []
            #print 'Flags count: ', game.flags_collected[game.player_num], game.flags_collected[self.killer]
            
        key=pygame.key.get_pressed()
        
        queue = game.message_queue[game.player_num]['bullet']
        while queue.empty() != True:
            data = queue.get()
            direction = int(data)
            if direction == 2:
                bullet(self.rect.midtop,2,game.player_num,game.sprites)
            elif direction == -2:
                bullet(self.rect.midbottom,-2,game.player_num,game.sprites)
            elif direction == -1:
                bullet(self.rect.midleft,-1,game.player_num,game.sprites)
            elif direction == 1:
                bullet(self.rect.midright,1,game.player_num,game.sprites)
        
        queue = game.message_queue[game.player_num]['move']
        while queue.empty() != True:
            data = queue.get()
            #print 'processing data...', data
            x, y, direction = data.split(' ')
            #print x, y, direction
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
        new_rect = self.rect.copy()
        
        if key[pygame.K_RIGHT]:    
            new_rect.x = new_rect.x + 10
            self.direction = 1
            self.action_flag = 0
        elif key[pygame.K_LEFT]:
            new_rect.x = new_rect.x - 10
            self.direction = -1
            self.action_flag = 0
        elif key[pygame.K_UP]:
            new_rect.y = new_rect.y - 10
            self.direction = 2
            self.action_flag = 0
        elif key[pygame.K_DOWN]:
            new_rect.y = new_rect.y + 10
            self.direction = -2
            self.action_flag = 0
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
        
        for cell in game.tilemap.layers['collision'].collide(new_rect,"blocker"):
            if last_position.right <= cell.left and new_rect.right > cell.left:
                new_rect.right = cell.left
            if last_position.left >= cell.right and new_rect.left < cell.right:
                new_rect.left = cell.right
            if last_position.bottom <= cell.top and new_rect.bottom > cell.top:
                new_rect.bottom = cell.top
            if last_position.top >= cell.bottom and new_rect.top < cell.bottom:
                new_rect.top = cell.bottom
        game.tilemap.set_focus(new_rect.x, new_rect.y)
        
        if self.action_flag == 0:
            data = str(game.player_num) + ' ' + str(new_rect.x) + " " + str(new_rect.y) + " " + str(self.direction)
            game.multicast_to_peers_data(MOVE, data)
        elif self.action_flag == 1:
            data = str(game.player_num) + ' ' + str(self.direction)
            game.multicast_to_peers_data(FIRE, data)
        self.action_flag = -1
