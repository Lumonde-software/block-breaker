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
SIZE_OF_MOSAIC = 64

BLOCK_SIZE = 8

FACE_AREA_SIZE = SIZE_OF_MOSAIC*BLOCK_SIZE

CAMERA_AREA = Rect(0, 0, CAMERA_WIDTH+CAMERA_MARGIN*2, CAMERA_HEIGHT+CAMERA_MARGIN*2)
CAMERA_FRAME = Rect(CAMERA_MARGIN, CAMERA_MARGIN, CAMERA_WIDTH, CAMERA_HEIGHT)
LEFT_AREA = Rect(0, 0, CAMERA_AREA.width, CAMERA_AREA.height+320)
RIGHT_AREA = Rect(LEFT_AREA.width, 0, 320, LEFT_AREA.height)
SCREEN = Rect(0, 0, LEFT_AREA.width+RIGHT_AREA.width, LEFT_AREA.height)
FACE_AREA = Rect((LEFT_AREA.width-FACE_AREA_SIZE)//2, (LEFT_AREA.width-FACE_AREA_SIZE)//2, FACE_AREA_SIZE, FACE_AREA_SIZE)


TITLE, SELECT, CAMERA, RECOGNIZE, GAME, POSED, CLEAR, OVER = range(8)
GAMEOVER = pygame.USEREVENT
GAMECLEAR = pygame.USEREVENT+1

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
        self.rect.clamp_ip(LEFT_AREA)                  # ゲーム画面内のみで移動

# ボールのクラス
class Ball(pygame.sprite.Sprite):
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename, paddle, blocks, balls, score, speed, angle_left, angle_right):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.dx = self.dy = 0.0  # ボールの速度
        self.paddle = paddle  # パドルへの参照
        self.blocks = blocks  # ブロックグループへの参照
        self.balls = balls  
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
            # self.update = self.start                    # ボールを初期状態に
            self.remove(self.balls)
            self.hit = 0
            self.score.add_score(-100)                  # スコア減点-100点
            if not len(self.balls) > 0:
                gameover = pygame.event.Event(GAMEOVER)
                pygame.event.post(gameover)
                

        # ボールと衝突したブロックリストを取得（Groupが格納しているSprite中から、指定したSpriteと接触しているものを探索）
        blocks_collided = pygame.sprite.spritecollide(self, self.blocks, True)
        if not len(self.blocks) > 0:
            gameclear = pygame.event.Event(GAMECLEAR)
            pygame.event.post(gameclear)
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
    def __init__(self, color, x, y):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.color = (int(color[0]), int(color[1]), int(color[2])) 
        self.width = BLOCK_SIZE
        self.height = BLOCK_SIZE
        self.image = self.create_block_img()
        self.rect = self.image.get_rect()
        # ブロックの左上座標
        self.rect.left = x
        self.rect.top = y
    
    def create_block_img(self):
        img = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
        img.fill((self.color[2], self.color[1], self.color[0]), Rect(1, 1, BLOCK_SIZE-2, BLOCK_SIZE-2))
        return img

# スコアのクラス
class Score():
    def __init__(self, x, y):
        self.sysfont = pygame.font.SysFont("notosanscjksc", 20)
        self.score = 0
        (self.x, self.y) = (x, y)
    def draw(self, screen):
        img = self.sysfont.render("SCORE:"+str(self.score), True, (255,255,250))
        screen.blit(img, (self.x, self.y))
    def add_score(self, x):
        self.score += x

class Button():
    def __init__(self, x, y, size, pad, color, txtcolor, text, center=False):
        self.x = x
        self.y = y
        self.pad = pad
        self.color = color
        self.font = pygame.font.SysFont("notosanscjksc", size)
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
    
    def invFlag(self):
        self.hide = not self.hide

class Title():
    def __init__(self, logofile, musicfile):
        self.logo = pygame.image.load(logofile)
        self.musicfile = musicfile
        pygame.mixer.music.load(self.musicfile)
        self.logo_rect = self.logo.get_rect()
        self.logo_img = pygame.transform.rotozoom(self.logo, 0, 0.9*SCREEN.width/self.logo_rect.width)
        self.logo_img_rect = self.logo_img.get_rect()
        # 画像の左上座標
        self.logo_img_rect.left = SCREEN.centerx - self.logo_img_rect.width // 2
        self.logo_img_rect.top = 30
        self.start_btn = Button(SCREEN.centerx, SCREEN.height * 0.6, 80, 16, (255, 0, 0), (255, 255, 255), "ゲーム開始", True)
        self.start_btn.hide = False
        self.play_bgm()

    def update(self):
        pass

    def draw(self, screen):
        screen.fill((128,0,0))
        screen.blit(self.logo_img, (self.logo_img_rect.left, self.logo_img_rect.top))
        self.start_btn.draw(screen)

    def play_bgm(self):
        pygame.mixer.music.play(-1)      # BGM
    
    def stop_bgm(self):
        pygame.mixer.music.stop()

class Select():
    def __init__(self):
        pass

    def update(self):
        pass

class Camera():
    def __init__(self, path, video):
        self.path = path
        self.video = video
        self.detect_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height, 60, 16, (255, 0, 0), (255, 255, 255), "顔検出", True)
        self.playgame_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height, 60, 16, (255, 0, 0), (255, 255, 255), "ゲーム開始", True)
        self.reshoot_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height+120, 60, 16, (255, 0, 0), (255, 255, 255), "再検出", True)
        self.cascade = cv.CascadeClassifier(self.path)     # カスケード
        self.cap = cv.VideoCapture(self.video)             # ビデオキャプチャ
        if not (self.cap.isOpened()):
            print("cannot open video")
            exit(1)
        self.cap.set(cv.CAP_PROP_FPS, CAMERA_FPS)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.display_left = CAMERA_MARGIN
        self.display_top = CAMERA_MARGIN
        self.faces = []
        self.recognized = False
        self.face_num = 0
        self.image_x = 0
        self.image_y = 0

    def update(self):
        self.ret, self.frame = self.cap.read()
        if self.ret == False:
            print("cannot update video")
            exit(1)
        self.frame = cv.imread("png/detect.png")
        self.recognition()
        self.surface = self.cvtToSurface(self.frame)

    def draw(self, screen):
        screen.fill((0,128,0))
        screen.blit(self.surface, (self.display_left, self.display_top))
        self.detect_btn.draw(screen)
        self.playgame_btn.draw(screen)
        self.reshoot_btn.draw(screen)
        pygame.draw.rect(screen, (0,0,0), RIGHT_AREA)
    
    def cvtToSurface(self,  frame):
        # そのままだと何故か回転してしまうので予め回転しておく
        rotated_frame = cv.rotate(frame, cv.ROTATE_90_COUNTERCLOCKWISE)
        recolored_frame = cv.cvtColor(rotated_frame, cv.COLOR_BGR2RGB)
        return pygame.pixelcopy.make_surface(recolored_frame)
    
    def recognition(self):
        gray_frame = cv.cvtColor(self.frame, cv.COLOR_BGR2GRAY)
        self.faces = self.cascade.detectMultiScale(gray_frame)
        if len(self.faces)>0:
            self.copy_frame = np.copy(self.frame)
            self.copy2_frame = np.copy(self.frame) #!!! FIXME
            self.copy2_surface = self.cvtToSurface(self.copy2_frame)
            for x, y, w, h in self.faces:
                cv.rectangle(self.frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            # cv.imwrite('png/detect.png', self.frame)
            self.recognized = True
        else:
            self.recognized = False

    def mosaic(self, img, size):
        return cv.resize(img, dsize=size, interpolation=cv.INTER_NEAREST)
    
    def create_block(self):
        x, y, width, height = self.faces[self.face_num]
        self.xx = x #!!! FIXME
        self.yy = y
        self.w = width
        self.h = height
        # rate = 0.2
        # y0 = int(y - height*rate)
        # y1 = int(y + height*(1+rate))
        # x0 = int(x - width*rate)
        # x1 = int(x + width*(1+rate))
        # roi = self.copy_frame[y0:y1, x0:x1]
        roi = self.copy_frame[y:y+height, x:x+width] # あってる
        """ gaussianBlur
        blurred_img = cv.GaussianBlur(roi, (9,9), 10.0)
        roi = cv.addWeighted(roi, 2.0, blurred_img, -1.0, 0, roi)
        """
        """ kernel
        kernel = np.array([
            [0, -1, 0],
            [0, 3, 0],
            [0, -1, 0]
        ])
        roi = cv.filter2D(roi, -1, kernel)
        """
        if width < height:
            print("error!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            self.mosaic_frame = self.mosaic(roi, (int(width*SIZE_OF_MOSAIC/height), SIZE_OF_MOSAIC))
            # self.copy_surface = self.cvtToSurface(cv.resize(self.copy_frame, dsize=None, fx=BLOCK_SIZE, fy=BLOCK_SIZE, interpolation=cv.INTER_NEAREST))
            # self.cvtToSurface(self.mosaic_frame)
            # num_w = len(self.mosaic_frame[0])
            # for i in range(SIZE_OF_MOSAIC):
            #     for j in range(num_w):
            #         Block(self.mosaic_frame[i][num_w-j-1], FACE_AREA.centerx - (num_w//2 - j) * BLOCK_SIZE, FACE_AREA.y + i * BLOCK_SIZE)
        else:
            self.mosaic_frame = self.mosaic(roi, (SIZE_OF_MOSAIC, int(height*SIZE_OF_MOSAIC/width)))
            scale = BLOCK_SIZE*SIZE_OF_MOSAIC/width
            # scale = BLOCK_SIZE*SIZE_OF_MOSAIC/width/(1+rate*2)
            resized = cv.resize(self.frame, dsize=None, fx=scale, fy=scale, interpolation=cv.INTER_NEAREST)
            self.copy_surface = self.cvtToSurface(resized)
            self.image_x = -((CAMERA_WIDTH-x)*scale - FACE_AREA.x)
            self.image_y = -(y*scale - FACE_AREA.y)

            # self.display_surface = self.cvtToSurface(resized[int(image_y):int(CAMERA_HEIGHT*scale), int(image_x):int(CAMERA_WIDTH*scale)])
            # self.image_x = FACE_AREA.left - x0*scale
            # self.image_y = FACE_AREA.top - y0*scale
            # self.cvtToSurface(self.mosaic_frame)
            num_h = len(self.mosaic_frame)
            for i in range(num_h):
                for j in range(SIZE_OF_MOSAIC):
                    Block(self.mosaic_frame[i][SIZE_OF_MOSAIC-j-1], FACE_AREA.x + j * BLOCK_SIZE, FACE_AREA.centery - (num_h//2 - i) * BLOCK_SIZE)
        self.face_num += 1


class block_breaker:
    def __init__(self):
        """初期化"""
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN.size)
        pygame.display.set_caption("Block Breaker")
        """TITLE"""
        self.title = Title("png/logo.png", "sound/bgm.wav")                      # タイトル画面
        """SELECT"""
        self.select =  Select()                                             # セレクト画面
        """CAMERA"""
        self.path = '../../opencv/data/haarcascades/haarcascade_frontalface_default.xml'
        self.camera = Camera(self.path, 0)     # カメラ
        """RCOGNIZE"""
        """GAME"""
        Ball.paddle_sound = pygame.mixer.Sound("sound/paddle.wav")    # パドルにボールが衝突した時の効果音取得
        Ball.block_sound = pygame.mixer.Sound("sound/block.wav") # ブロックにボールが衝突した時の効果音取得
        self.gameover_sound = pygame.mixer.Sound("sound/over.wav")    # ゲームオーバー時の効果音取得
        self.gameclear_sound = pygame.mixer.Sound("sound/clear.wav")    # ゲームクリア時の効果音取得
        # 描画用のスプライトグループ
        self.game_group = pygame.sprite.RenderUpdates()
        # 衝突判定用のスプライトグループ
        self.blocks = pygame.sprite.Group()
        # ボール保持用のスプライトグループ   
        self.balls = pygame.sprite.Group()
        # スプライトグループに追加    
        Paddle.containers = self.game_group
        Ball.containers = self.game_group, self.balls
        Block.containers = self.game_group, self.blocks
        self.paddle = Paddle("png/paddle.png")                                  # パドルの作成
        self.score = Score(RIGHT_AREA.left+10, 10)                                          # スコアを画面(10, 10)に表示
        Ball("png/rectangle.png", self.paddle, self.blocks, self.balls, self.score, 5, 135, 45)  # ボールを作成
        """POSED"""
        self.alpha_screen =pygame.Surface(SCREEN.size,flags=pygame.SRCALPHA) 
        self.font = pygame.font.SysFont("notosanscjksc", 90)
        """OVER"""
        """CLEAR"""
        self.finish_btn = Button(SCREEN.centerx, SCREEN.height * 0.7, 70, 16, (255, 0, 0), (255, 255, 255), "ゲーム終了", True)
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
        elif self.game_state == POSED or self.game_state == OVER or self.game_state == CLEAR:
            pass

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
            # self.screen.blit(self.camera.copy_surface, (0,0))
            self.screen.blit(self.camera.copy_surface, (self.image_x, self.image_y)) #!!! FIXME
            self.game_group.draw(self.screen)   # 全てのスプライトグループを描画 
            pygame.draw.rect(self.screen, (0,0,0), RIGHT_AREA)
            # a = pygame.Surface(CAMERA_FRAME.size) # !!! FIXME
            # a.blit(self.camera.copy2_surface,(0,0))
            # b = pygame.Surface((self.camera.w,self.camera.h))
            # a.blit(b,(self.camera.xx,self.camera.yy))
            # self.screen.blit(a,(0,0))
            self.score.draw(self.screen)        # スコアを描画
        elif self.game_state == POSED:
            pass
        elif self.game_state == OVER or self.game_state == CLEAR:
            self.finish_btn.draw(self.screen)

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
            elif self.game_state == POSED:
                self.posed_handler(event)
            elif self.game_state == OVER or self.game_state == CLEAR:
                self.finish_handler(event)

    def title_handler(self, event):
        """タイトル画面のイベントハンドラ"""
        if (self.title.start_btn.pushed(event)):
            self.camera.detect_btn.invFlag()
            self.game_state = SELECT
    
    def select_handler(self, event):
        """セレクト画面のイベントハンドラ"""
        pass
    
    def camera_handler(self, event):
        """カメラ画面のイベントハンドラ"""
        if self.camera.detect_btn.pushed(event):
            if self.camera.recognized:
                self.camera.detect_btn.invFlag()
                self.camera.playgame_btn.invFlag()
                self.camera.reshoot_btn.invFlag()
                self.game_state = RECOGNIZE
    
    def recognize_handler(self, event):
        """RECOGNIZEモードのイベントハンドラ"""
        if self.camera.playgame_btn.pushed(event):
            self.camera.playgame_btn.invFlag()
            self.camera.reshoot_btn.invFlag()
            self.camera.create_block()
            self.image_x = self.camera.image_x
            self.image_y = self.camera.image_y
            self.game_state = GAME
        elif self.camera.reshoot_btn.pushed(event):
            self.camera.playgame_btn.invFlag()
            self.camera.reshoot_btn.invFlag()
            self.camera.detect_btn.invFlag()
            self.game_state = CAMERA
    
    def game_handler(self, event):
        """ゲーム画面のイベントハンドラ"""
        if event.type == KEYDOWN and event.key == K_p:
            self.blit_alpah_screen("POSED")
            self.game_state = POSED
        elif event.type == GAMEOVER:
            self.title.stop_bgm()
            self.gameover_sound.play()
            self.finish_btn.invFlag()
            self.blit_alpah_screen("GAME OVER")
            self.game_state = OVER
        elif event.type == GAMECLEAR or (event.type == KEYDOWN and event.key == K_s):
            self.title.stop_bgm()
            self.gameclear_sound.play()
            self.finish_btn.invFlag()
            self.blit_alpah_screen("GAME CLEAR!")
            self.game_state = CLEAR
    
    def posed_handler(self, event):
        if event.type == KEYDOWN and event.key == K_p:
            self.game_state = GAME
    
    def finish_handler(self, event):
        if self.finish_btn.pushed(event):
            exit(1)

    def blit_alpah_screen(self, txt):
        self.alpha_screen.fill((0,0,0,128))
        text = self.font.render(txt, True, (255,255,255))
        rect = text.get_rect()
        self.alpha_screen.blit(text, (SCREEN.centerx-rect.width/2, SCREEN.centery-rect.height))
        self.screen.blit(self.alpha_screen,(0,0))

if __name__ == "__main__":
    block_breaker()