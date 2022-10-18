import cv2
import const
import tkinter as tk

const.HEIGHT = 1000
const.WIDTH = 3000

const.START_IMG_PATH = '../data/start.jpg'
const.GAME_NAME = 'Image Recognition Block Breaker'

start_img = cv2.imread(const.START_IMG_PATH, 1)
print(start_img.shape)
resized_start_img = cv2.resize(start_img, (const.WIDTH, const.WIDTH*start_img.shape[0]//start_img.shape[1]))

cv2.namedWindow(const.GAME_NAME, cv2.WINDOW_NORMAL)
cv2.imshow(const.GAME_NAME, resized_start_img)

while True:
    k = cv2.waitKey(0) 
    if k == 27:
        cv2.destroyAllWindows()
        break