from ctypes.wintypes import tagRECT
import pygame
from pygame.locals import *
import math
import sys
import pygame.mixer
import cv2 as cv
import numpy as np
import block_breaker as bb

a = 1

SCREEN = Rect(0,0,bb.BLOCK_SIZE-a*2,bb.BLOCK_SIZE-a*2)

pygame.init()
screen = pygame.display.set_mode(SCREEN.size)
screen.fill((255,255,0))
rect = Rect(1,1,SCREEN.width-2, SCREEN.height-2)
pygame.draw.rect(screen, (255,0,0), rect)
pygame.image.save(screen, "png/rectangle.png")