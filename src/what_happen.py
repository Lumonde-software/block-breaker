# -*- coding: utf-8 -*-
from ctypes.wintypes import tagRECT
import pygame
from pygame.locals import *
import math
import sys
import pygame.mixer
import cv2 as cv
import numpy as np




CAMERA_FPS = 30

# サイズ
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_MARGIN = 40
FACE_MARGIN = 88
RIGHT_AREA_MARGIN = 30

SIZE_OF_MOSAIC = 32
FACE_AREA_SIZE = 512
BLOCK_SIZE = int(FACE_AREA_SIZE/SIZE_OF_MOSAIC)

CAMERA_AREA = Rect(0, 0, CAMERA_WIDTH+CAMERA_MARGIN*2, CAMERA_HEIGHT+CAMERA_MARGIN*2)
CAMERA_FRAME = Rect(CAMERA_MARGIN, CAMERA_MARGIN, CAMERA_WIDTH, CAMERA_HEIGHT)
LEFT_AREA = Rect(0, 0, CAMERA_AREA.width, CAMERA_AREA.height+450)
RIGHT_AREA = Rect(LEFT_AREA.width, 0, 500, LEFT_AREA.height)
SCREEN = Rect(0, 0, LEFT_AREA.width+RIGHT_AREA.width, LEFT_AREA.height)
FACE_AREA = Rect((LEFT_AREA.width-FACE_AREA_SIZE)//2, (LEFT_AREA.width-FACE_AREA_SIZE)//2, FACE_AREA_SIZE, FACE_AREA_SIZE)

TITLE, CAMERA, RECOGNIZE, GAME, POSED, CLEAR, OVER, AUTO, NEXT = range(9)
GAMEOVER = pygame.USEREVENT
GAMECLEAR = pygame.USEREVENT+1


pygame.init()
aa = pygame.image.load("png/faces.jpg")
aaa = aa.get_rect() 
screen = pygame.display.set_mode((aaa.height, aaa.width))
a = cv.imread("png/faces.jpg")
c = cv.rotate(a, cv.ROTATE_90_COUNTERCLOCKWISE)
cv.imwrite("png/rotate.png", c)
d = cv.cvtColor(c, cv.COLOR_BGR2RGB)
d = pygame.pixelcopy.make_surface(d)
pygame.image.save(d, "png/rotate_inv.png")


cv.imshow("",a)
cv.waitKey(0) #待機時間、ミリ秒指定、0の場合はボタンが押されるまで待機
cv.destroyAllWindows()

while True:
    screen.blit(c,(0,0))
    pygame.display.update()

    for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()