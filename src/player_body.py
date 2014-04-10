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
    
    def update2(self,game,message_type,data):
            game.tilemap.set_focus(self.rect.x, self.rect.y)
        
    def update(self, dt, game):
        if player.game_over=='true':
            game.show_loser_screen()
            self.kill()
        key=pygame.key.get_pressed()
        #print 'here'
        last_position = self.rect.copy()
        
        message_type = game.message_type
        data = game.message_data
        #print data
        if message_type == MOVE:
            x, y, direction, player_num = data.split(' ')
            print x, y, direction, player_num
            if (game.player_num == player_num):
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
            
            
        elif key[pygame.K_RIGHT]:
            #self.rect.x+=10
            #self.image=self.right_image
            #self.direction=1
            data = str(self.rect.x + 10) + " " + str(self.rect.y) + " " + str(1) + " " + str(game.player_num)
            game.multicast_to_peers_data(MOVE, data)
        elif key[pygame.K_LEFT]:
            #self.rect.x-=10
            #self.image=self.left_image
            #self.direction=-1
            data = str(self.rect.x - 10) + " " + str(self.rect.y) + " " + str(-1) + " " + str(game.player_num)
            game.multicast_to_peers_data(MOVE, data)
        elif key[pygame.K_UP]:
            #self.rect.y-=10
            #self.image=self.up_image
            #self.direction=2
            data = str(self.rect.x) + " " + str(self.rect.y - 10) + " " + str(2) + " " + str(game.player_num)
            game.multicast_to_peers_data(MOVE, data)
        elif key[pygame.K_DOWN]:
            #self.rect.y+=10
            #self.image=self.down_image
            #self.direction=-2
            data = str(self.rect.x) + " " + str(self.rect.y + 10) + " " + str(-2) + " " + str(game.player_num)
            game.multicast_to_peers_data(MOVE, data)
        
        
        '''if key[pygame.K_SPACE] and not self.guncooldown:
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
        self.blockwallcooldown=max(0,self.blockwallcooldown-dt)'''
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