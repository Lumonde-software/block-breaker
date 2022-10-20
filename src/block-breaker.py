# -*- coding: utf-8 -*-
from ctypes.wintypes import tagRECT
import pygame
from pygame.locals import *
import math
import sys
import pygame.mixer
import cv2
import numpy as np

# 画面サイズ
SCREEN = Rect(0, 0, 800, 800)

TITLE, SELECT, CAMERA, GAME = range(4)

# バドルのクラス
class Paddle(pygame.sprite.Sprite):
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.rect.bottom = SCREEN.bottom - 20        # パドルのy座標

    def update(self):
        self.rect.centerx = pygame.mouse.get_pos()[0]  # マウスのx座標をパドルのx座標に
        self.rect.clamp_ip(SCREEN)                     # ゲーム画面内のみで移動

# ボールのクラス
class Ball(pygame.sprite.Sprite):
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename, paddle, blocks, score, speed, angle_left, angle_right):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.dx = self.dy = 0.0  # ボールの速度
        self.paddle = paddle  # パドルへの参照
        self.blocks = blocks  # ブロックグループへの参照
        self.update = self.start # ゲーム開始状態に更新
        self.score = score
        self.hit = 0  # 連続でブロックを壊した回数
        self.speed = speed # ボールの初期速度
        self.angle_left = angle_left # パドルの反射方向(左端:135度）
        self.angle_right = angle_right # パドルの反射方向(右端:45度）

    # ゲーム開始状態（マウスを左クリック時するとボール射出）
    def start(self):
        # ボールの初期位置(パドルの上)
        self.rect.centerx = self.paddle.rect.centerx
        self.rect.bottom = self.paddle.rect.top

        # 左クリックでボール射出
        if pygame.mouse.get_pressed()[0] == 1:
            self.dx = 0.0
            self.dy = -self.speed
            self.update = self.move

    # ボールの挙動
    def move(self):
        self.rect.centerx += self.dx
        self.rect.centery += self.dy

        # 壁との反射
        if self.rect.left < SCREEN.left:    # 左側
            self.rect.left = SCREEN.left
            self.dx = -self.dx              # 速度を反転
        if self.rect.right > SCREEN.right:  # 右側
            self.rect.right = SCREEN.right
            self.dx = -self.dx
        if self.rect.top < SCREEN.top:      # 上側
            self.rect.top = SCREEN.top
            self.dy = -self.dy

        # パドルとの反射(左端:135度方向, 右端:45度方向, それ以外:線形補間)
        # 2つのspriteが接触しているかどうかの判定
        if self.rect.colliderect(self.paddle.rect) and self.dy > 0:
            self.hit = 0                                # 連続ヒットを0に戻す
            (x1, y1) = (self.paddle.rect.left - self.rect.width, self.angle_left)
            (x2, y2) = (self.paddle.rect.right, self.angle_right)
            x = self.rect.left                          # ボールが当たった位置
            y = (float(y2-y1)/(x2-x1)) * (x - x1) + y1  # 線形補間
            angle = math.radians(y)                     # 反射角度
            self.dx = self.speed * math.cos(angle)
            self.dy = -self.speed * math.sin(angle)
            self.paddle_sound.play()                    # 反射音

        # ボールを落とした場合
        if self.rect.top > SCREEN.bottom:
            self.update = self.start                    # ボールを初期状態に
            self.gameover_sound.play()
            self.hit = 0
            self.score.add_score(-100)                  # スコア減点-100点

        # ボールと衝突したブロックリストを取得（Groupが格納しているSprite中から、指定したSpriteと接触しているものを探索）
        blocks_collided = pygame.sprite.spritecollide(self, self.blocks, True)
        if blocks_collided:  # 衝突ブロックがある場合
            oldrect = self.rect
            for block in blocks_collided:
                # ボールが左からブロックへ衝突した場合
                if oldrect.left < block.rect.left and oldrect.right < block.rect.right:
                    self.rect.right = block.rect.left
                    self.dx = -self.dx
                    
                # ボールが右からブロックへ衝突した場合
                if block.rect.left < oldrect.left and block.rect.right < oldrect.right:
                    self.rect.left = block.rect.right
                    self.dx = -self.dx

                # ボールが上からブロックへ衝突した場合
                if oldrect.top < block.rect.top and oldrect.bottom < block.rect.bottom:
                    self.rect.bottom = block.rect.top
                    self.dy = -self.dy

                # ボールが下からブロックへ衝突した場合
                if block.rect.top < oldrect.top and block.rect.bottom < oldrect.bottom:
                    self.rect.top = block.rect.bottom
                    self.dy = -self.dy
                self.block_sound.play()     # 効果音を鳴らす
                self.hit += 1               # 衝突回数
                self.score.add_score(self.hit * 10)   # 衝突回数に応じてスコア加点

# ブロックのクラス
class Block(pygame.sprite.Sprite):
    def __init__(self, filename, x, y):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        # ブロックの左上座標
        self.rect.left = SCREEN.left + x * self.rect.width
        self.rect.top = SCREEN.top + y * self.rect.height

# スコアのクラス
class Score():
    def __init__(self, x, y):
        self.sysfont = pygame.font.SysFont(None, 20)
        self.score = 0
        (self.x, self.y) = (x, y)
    def draw(self, screen):
        img = self.sysfont.render("SCORE:"+str(self.score), True, (255,255,250))
        screen.blit(img, (self.x, self.y))
    def add_score(self, x):
        self.score += x

class Button():
    def __init__(self, x, y, size, pad, color, txtcolor, text="Button", center=False):
        self.x = x
        self.y = y
        self.pad = pad
        self.color = color
        self.font = pygame.font.SysFont(None, size)
        self.text = self.font.render(text, True, txtcolor)
        if (center):
            self.x = x-(self.text.get_width() + pad//2)//2
            self.y = y+(self.text.get_height() + pad//2)//2
        self.button = Rect((self.x,self.y), (self.text.get_width() + pad, self.text.get_height() + pad))
        self.buttonUp = 1
    
    def pushed(self, event):
        self.button.top = self.y
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.button.collidepoint(event.pos):
                if self.buttonUp == 1:
                    self.button.top += 2
                    self.buttonUp = 0
        if event.type == pygame.MOUSEBUTTONUP:
            if self.button.collidepoint(event.pos):
                if self.buttonUp == 0:
                    self.button.top -= 2
                    self.buttonUp = 1
                    return 1
        return 0

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.button)
        screen.blit(self.text, (self.x + self.pad / 2, self.y + self.pad / 2))

class Title():
    """タイトル画面"""
    def __init__(self, filename, start_btn):
        self.logo = pygame.image.load(filename)
        self.logo_rect = self.logo.get_rect()
        self.logo_img = pygame.transform.rotozoom(self.logo, 0, 0.9*SCREEN.width/self.logo_rect.width)
        self.logo_img_rect = self.logo_img.get_rect()
        # 画像の左上座標
        self.logo_img_rect.left = SCREEN.centerx - self.logo_img_rect.width // 2
        self.logo_img_rect.top = 30
        self.start_btn = start_btn
        self.play_bgm()

    def update(self):
        pass

    def draw(self, screen):
        screen.blit(self.logo_img, (self.logo_img_rect.left, self.logo_img_rect.top))
        self.start_btn.draw(screen)

    def play_bgm(self):
        self.bgm_sound.play()      # BGM

class Select():
    def __init__(self):
        pass

    def update(self):
        pass

class Camera():
    def __init__(self, path, video):
        self.path = path
        self.video = video
        self.cap = cv2.VideoCapture(self.video)
        if not (self.cap.isOpened()):
            print("cannot open video")
            exit(1)
        self.display_size = (800, 600)
        # self.display = Rect(0, 0, self.video.width, self.video.height)
        # self.display.left = 10
        # self.display.top = 10

    def update(self):
        self.ret, self.frame = self.cap.read()
        if ( self.ret == False ):
            print("cannot update video")
            exit(1)
        # そのままだと何故か回転してしまうので予め回転しておく
        self.frame2 = cv2.rotate(self.frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.surface = pygame.pixelcopy.make_surface(cv2.cvtColor(self.frame2, cv2.COLOR_BGR2RGB))

    def draw(self, screen):
        screen.blit(self.surface, (10,10))
        # screen.blit(self.frame, (self.display.left, self.display.top))

class block_breaker:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN.size)
        pygame.display.set_caption("Block Breaker")
        Title.bgm_sound = pygame.mixer.Sound("dq1.wav") # タイトル画面のBGM取得
        Ball.paddle_sound = pygame.mixer.Sound("dq1.wav")    # パドルにボールが衝突した時の効果音取得
        Ball.block_sound = pygame.mixer.Sound("dq1.wav") # ブロックにボールが衝突した時の効果音取得
        Ball.gameover_sound = pygame.mixer.Sound("dq1.wav")    # ゲームオーバー時の効果音取得
        # 描画用のスプライトグループ
        self.game_group = pygame.sprite.RenderUpdates()  
        # 衝突判定用のスプライトグループ
        self.blocks = pygame.sprite.Group()   
        # スプライトグループに追加    
        Paddle.containers = self.game_group
        Ball.containers = self.game_group
        Block.containers = self.game_group, self.blocks
        self.paddle = Paddle("paddle.png")                                  # パドルの作成
        self.score = Score(10, 10)                                          # スコアを画面(10, 10)に表示
        Ball("ball.png", self.paddle, self.blocks, self.score, 5, 135, 45)  # ボールを作成
        # タイトル画面のボタンを作成
        self.start_btn = Button(SCREEN.centerx, SCREEN.height * 0.6, 80, 16, (255, 0, 0), (255, 255, 255), "START", True)
        self.title = Title("logo.png", self.start_btn)                      # タイトル画面
        print(self.title.logo)
        self.select =  Select()                                             # セレクト画面
        # カメラ
        self.camera = Camera('/home/denjo/experiment/cvgl/opencv/data/haarcascades/haarcascade_frontalface_default.xml', 0) 
        self.game_state = TITLE                                             # ゲームの状態をTITLEにする
        self.main_loop()                                                    # メインループを起動
    
    def main_loop(self):    
        clock = pygame.time.Clock()
        while True:
            clock.tick(60)              # フレームレート(60fps)
            self.update()             # ゲーム状態の更新
            self.render()             # ゲームオブジェクトのレンダリング
            pygame.display.update()  # 画面に描画
            self.check_event()        # イベントハンドラ
    
    def update(self):
        """ゲーム状態の更新"""
        if self.game_state == TITLE:
            self.title.update()
        elif self.game_state == SELECT:
            self.select.update()
        elif self.game_state == CAMERA:
            self.camera.update()
        elif self.game_state == GAME:
            self.game_group.update()        # 全てのスプライトグループを更新

    def render(self):
        """ゲームオブジェクトのレンダリング"""
        if self.game_state == TITLE:
            self.screen.fill((0,0,128))
            self.title.draw(self.screen)
        elif self.game_state == SELECT:
            self.screen.fill((0,128,0))
            self.game_state = CAMERA
        elif self.game_state == CAMERA:
            self.camera.draw(self.screen)
        elif self.game_state == GAME:
            self.screen.fill((0,20,0))
            self.game_group.draw(self.screen)   # 全てのスプライトグループを描画 
            self.score.draw(self.screen)        # スコアを描画  
            pygame.display.update()             # 画面更新 
    
    def create_block(self):
        # ブロックの作成(14*10)
        for x in range(1, 15):
            for y in range(1, 11):
                Block("block.png", x, y)

    def check_event(self):
        """イベントハンドラ"""
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
            # 表示されているウィンドウに応じてイベントハンドラを変更
            if self.game_state == TITLE:
                self.title_handler(event)
            elif self.game_state == SELECT:
                self.select_handler(event)
            elif self.game_state == CAMERA:
                self.camera_handler(event)
            elif self.game_state == GAME:
                self.game_handler(event)

    def title_handler(self, event):
        """タイトル画面のイベントハンドラ"""
        if (self.title.start_btn.pushed(event)):
            self.game_state = SELECT
    
    def select_handler(self, event):
        """セレクト画面のイベントハンドラ"""
        pass
    
    def camera_handler(self, event):
        pass
    
    def game_handler(self, event):
        pass

if __name__ == "__main__":
    block_breaker()