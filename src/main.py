### インポート
import sys
import pygame
from pygame.locals import *

### 画面初期化
pygame.init()
surface = pygame.display.set_mode((960, 320))

### キーリピート設定
pygame.key.set_repeat(100,100)

### フォントリスト取得
list = []
for x in pygame.font.get_fonts():
    list.append(x)

### リスト位置初期化
i = 0

### 無限ループ
while True:

    ### 背景色設定
    surface.fill((0,0,0))

    ### フォント設定
    font = pygame.font.SysFont(list[i], 30)

    ### 表示文字設定
    name = font.render("{}".format(list[i]), True, (255,255,255))
    numb = font.render("1234567890", True, (255,255,255))
    asci = font.render("ABCDEFGHIJKLMNOPQRSTUVWXYZ", True, (255,255,255))
    japn = font.render("あいうえおアイウエオ山田太郎鈴木花子", True, (255,255,255))

    ### 画面表示位置
    surface.blit(name, [20,20])
    surface.blit(numb, [20,70])
    surface.blit(asci, [20,120])
    surface.blit(japn, [20,170])

    ### 画面更新
    pygame.display.update()

    ### イベント取得
    for event in pygame.event.get():

        ### 終了処理
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()

            ### フォント変更
            if event.key == K_UP   and i > 0:
                i -= 1
            if event.key == K_DOWN and i < len(list)-1:
                i += 1