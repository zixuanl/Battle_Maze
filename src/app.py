#!/usr/bin/python
import sys
import threading
from Tkinter import *
from random import *
from sample_app import *

import pygame
import sys
import tmx
from tmx import *


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

class Game(object):
    def __init__( self, firstpeer,maxpeers=5, serverport=12345, master=None ):
        self.btpeer = SamplePeer( maxpeers, serverport )
        host,port = firstpeer.split(':')
        t = threading.Thread( target = self.btpeer.mainloop, args = [] )
        t.start()  
        self.btpeer.startstabilizer( self.btpeer.checklivepeers, 3 )
        if firstpeer!=self.btpeer.bootstrap:
            self.btpeer.contactbootstrap(host, port)
        #  self.btpeer.startstabilizer( self.onRefresh, 3 ) 
    
    def onDestroy(self):
        self.btpeer.shutdown = True     
    
    def main(self, screen):
        clock = pygame.time.Clock()

        background = pygame.image.load('background.png')
        self.tilemap = tmx.load('brick.tmx', screen.get_size())
        self.sprites = tmx.SpriteLayer()
        self.enemies = tmx.SpriteLayer()
        start_cell = self.tilemap.layers['collision'].find('player')[0]
        self.player1 = player((start_cell.px, start_cell.py), self.sprites)
        self.player2 = enemies((320, 240), self.enemies)
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
    appl = Game( firstpeer=peerid, maxpeers=maxpeers, serverport=serverport )
    if appl.btpeer.bootstrap!=peerid:
        pygame.init()
        screen = pygame.display.set_mode((640, 480))
        appl.main(screen)
        appl.onDestroy()
        