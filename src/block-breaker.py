# -*- coding: utf-8 -*-
from ctypes.wintypes import tagRECT
# from block-breaker.sample.sample import LEFT
import pygame
from pygame.locals import *
import math
import sys
import pygame.mixer
import cv2
import numpy as np

# 画面サイズ
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_MARGIN = 40

CAMERA_AREA = Rect(0, 0, CAMERA_WIDTH+CAMERA_MARGIN*2, CAMERA_HEIGHT+CAMERA_MARGIN*2)
CAMERA_FRAME = Rect(CAMERA_MARGIN, CAMERA_MARGIN, CAMERA_WIDTH, CAMERA_HEIGHT)
LEFT_AREA = Rect(0, 0, CAMERA_AREA.width, CAMERA_AREA.height+320)
RIGHT_AREA = Rect(LEFT_AREA.width, 0, 320, LEFT_AREA.height)
SCREEN = Rect(0, 0, LEFT_AREA.width+RIGHT_AREA.width, LEFT_AREA.height)

TITLE, SELECT, CAMERA, RECOGNIZE, GAME = range(5)

# バドルのクラス
class Paddle(pygame.sprite.Sprite):
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.rect.bottom = LEFT_AREA.bottom - 20        # パドルのy座標

    def update(self):
        self.rect.centerx = pygame.mouse.get_pos()[0]  # マウスのx座標をパドルのx座標に
        self.rect.clamp_ip(LEFT_AREA)                     # ゲーム画面内のみで移動

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
        if self.rect.left < LEFT_AREA.left:    # 左側
            self.rect.left = LEFT_AREA.left
            self.dx = -self.dx              # 速度を反転
        if self.rect.right > LEFT_AREA.right:  # 右側
            self.rect.right = LEFT_AREA.right
            self.dx = -self.dx
        if self.rect.top < LEFT_AREA.top:      # 上側
            self.rect.top = LEFT_AREA.top
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
        if self.rect.top > LEFT_AREA.bottom:
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
        self.rect.left = LEFT_AREA.left + x * self.rect.width
        self.rect.top = LEFT_AREA.top + y * self.rect.height

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
        self.hide = True
    
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
        if self.hide == False:
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
        screen.fill((128,0,0))
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
    def __init__(self, path, video, detect_btn, playgame_btn, reshoot_btn):
        self.path = path
        self.video = video
        self.detect_btn = detect_btn
        self.playgame_btn = playgame_btn
        self.reshoot_btn = reshoot_btn
        self.cascade = cv2.CascadeClassifier(self.path)     # カスケード
        self.cap = cv2.VideoCapture(self.video)             # ビデオキャプチャ
        if not (self.cap.isOpened()):
            print("cannot open video")
            exit(1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.display_left = CAMERA_MARGIN
        self.display_top = CAMERA_MARGIN
        self.faces = []
        self.recognized = False

    def update(self):
        self.ret, self.frame = self.cap.read()
        if self.ret == False:
            print("cannot update video")
            exit(1)
        self.recognition()
        self.surface = self.cvtToSurface()

    def draw(self, screen):
        screen.fill((0,128,0))
        screen.blit(self.surface, (self.display_left, self.display_top))
        self.detect_btn.draw(screen)
        self.playgame_btn.draw(screen)
        self.reshoot_btn.draw(screen)
    
    def cvtToSurface(self):
        # そのままだと何故か回転してしまうので予め回転しておく
        rotated_frame = cv2.rotate(self.frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        recolored_frame = cv2.cvtColor(rotated_frame, cv2.COLOR_BGR2RGB)
        return pygame.pixelcopy.make_surface(recolored_frame)
    
    def recognition(self):
        gray_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        self.faces = self.cascade.detectMultiScale(gray_frame)
        if len(self.faces)!=0:
            for x, y, w, h in self.faces:
                cv2.rectangle(self.frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.imwrite('detect.png', self.frame)
            self.recognized = True
        else:
            self.recognized = False
    
    def create_block(self):
        pass

class block_breaker:
    def __init__(self):
        """初期化"""
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN.size)
        pygame.display.set_caption("Block Breaker")
        """TITLE"""
        Title.bgm_sound = pygame.mixer.Sound("dq1.wav") # タイトル画面のBGM取得
        # タイトル画面のボタンを作成
        self.start_btn = Button(SCREEN.centerx, SCREEN.height * 0.6, 80, 16, (255, 0, 0), (255, 255, 255), "START", True)
        self.start_btn.hide = False     # ボタンのhideフラグをFalseにする
        self.title = Title("logo.png", self.start_btn)                      # タイトル画面
        """SELECT"""
        self.select =  Select()                                             # セレクト画面
        """CAMERA"""
        self.detect_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height+100, 80, 16, (255, 0, 0), (255, 255, 255), "DETECT", True)
        self.path = '/home/denjo/experiment/cvgl/opencv/data/haarcascades/haarcascade_frontalface_default.xml'
        """RCOGNIZE"""
        self.playgame_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height+60, 80, 16, (255, 0, 0), (255, 255, 255), "PLAY GAME", True)
        self.reshoot_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height+140, 80, 16, (255, 0, 0), (255, 255, 255), "RESHOOT", True)
        """CAMERA SET UP"""
        self.camera = Camera(self.path, 0, self.detect_btn, self.playgame_btn, self.reshoot_btn)     # カメラ
        """GAME"""
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
        """ループ開始"""
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
        elif self.game_state == RECOGNIZE:
            pass
        elif self.game_state == GAME:
            self.game_group.update()        # 全てのスプライトグループを更新

    def render(self):
        """ゲームオブジェクトのレンダリング"""
        if self.game_state == TITLE:
            self.title.draw(self.screen)
        elif self.game_state == SELECT:
            self.game_state = CAMERA
        elif self.game_state == CAMERA or self.game_state == RECOGNIZE:
            self.camera.draw(self.screen)
        elif self.game_state == GAME:
            self.screen.fill((200,200,200))
            self.game_group.draw(self.screen)   # 全てのスプライトグループを描画 
            self.score.draw(self.screen)        # スコアを描画  
    
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
            elif self.game_state == RECOGNIZE:
                self.recognize_handler(event)
            elif self.game_state == GAME:
                self.game_handler(event)

    def title_handler(self, event):
        """タイトル画面のイベントハンドラ"""
        if (self.title.start_btn.pushed(event)):
            self.camera.detect_btn.hide = False
            self.game_state = SELECT
    
    def select_handler(self, event):
        """セレクト画面のイベントハンドラ"""
        pass
    
    def camera_handler(self, event):
        """カメラ画面のイベントハンドラ"""
        if self.camera.detect_btn.pushed(event):
            if self.camera.recognized:
                self.camera.detect_btn.hide = True
                self.camera.playgame_btn.hide = False
                self.camera.reshoot_btn.hide = False
                self.game_state = RECOGNIZE
    
    def recognize_handler(self, event):
        """RECOGNIZEモードのイベントハンドラ"""
        if self.camera.playgame_btn.pushed(event):
            self.camera.playgame_btn.hide = True
            self.camera.reshoot_btn.hide = True
            self.camera.create_block()
            self.create_block()
            self.game_state = GAME
        elif self.camera.reshoot_btn.pushed(event):
            self.camera.playgame_btn.hide = True
            self.camera.reshoot_btn.hide = True
            self.camera.detect_btn.hide = False
            self.game_state = CAMERA
    
    def game_handler(self, event):
        pass

if __name__ == "__main__":
    block_breaker()