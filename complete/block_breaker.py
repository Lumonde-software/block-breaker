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

# バドルのクラス
class Paddle(pygame.sprite.Sprite):
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.rect.bottom = LEFT_AREA.bottom - 20        # パドルのy座標
        self.flag = False

    def update(self):
        self.rect.centerx = pygame.mouse.get_pos()[0]  # マウスのx座標をパドルのx座標に
        self.rect.clamp_ip(LEFT_AREA)                  # ゲーム画面内のみで移動
    
    def auto_update(self, balls):
        max_y = -1
        max_ball_x = SCREEN.centerx - self.rect.width//2
        for ball in balls:
            if max_y < ball.rect.y and ball.rect.y-2 <= self.rect.bottom:
                max_y = ball.rect.y
                max_ball_x = ball.rect.centerx
        if self.flag:
            self.rect.centerx = max_ball_x - 20
        else:
            self.rect.centerx = max_ball_x + 20
        self.rect.clamp_ip(LEFT_AREA)

    def auto_draw(self, screen):
        screen.blit(self.image, self.rect.topleft)

# ボールのクラス
class Ball(pygame.sprite.Sprite):
    hit_sum = 0
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename, paddle, blocks, balls, score, speed, angle_left, angle_right, increase=False, left=0, top=0, dx=0, dy=0):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.dx = self.dy = 0.0  # ボールの速度
        self.paddle = paddle  # パドルへの参照
        self.blocks = blocks  # ブロックグループへの参照
        self.balls = balls  
        self.score = score
        self.hit = 0  # 連続でブロックを壊した回数
        self.speed = speed # ボールの初期速度
        self.angle_left = angle_left # パドルの反射方向(左端:135度）
        self.angle_right = angle_right # パドルの反射方向(右端:45度)
        if increase:
            self.update = self.move # 増殖により生まれた場合は最初から動く
            self.rect.left = left
            self.rect.top = top
            angle = math.atan2(dy, dx) + 20
            speed = math.sqrt(dx**2+dy**2)
            self.dx = speed*math.cos(angle)
            self.dy = speed*math.sin(angle)
            if -1 < self.dy <= 0:
                self.dy = -1
            elif 0 < self.dy < 1:
                self.dy = 1
        else:
            self.update = self.start # ゲーム開始状態に更新

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
            if -1 < self.dy <= 0:
                self.dy = -1
            elif 0 < self.dy < 1:
                self.dy = 1
            self.paddle.flag = not self.paddle.flag
            self.paddle_sound.play()                    # 反射音

        # ボールを落とした場合
        if self.rect.top > LEFT_AREA.bottom:
            self.remove(self.balls)
            self.dx = 0
            self.dy = 0
            self.hit = 0
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
                elif block.rect.left < oldrect.left and block.rect.right < oldrect.right:
                    self.rect.left = block.rect.right
                    self.dx = -self.dx

                # ボールが上からブロックへ衝突した場合
                elif oldrect.top < block.rect.top and oldrect.bottom < block.rect.bottom:
                    self.rect.bottom = block.rect.top
                    self.dy = -self.dy

                # ボールが下からブロックへ衝突した場合
                elif block.rect.top < oldrect.top and block.rect.bottom < oldrect.bottom:
                    self.rect.top = block.rect.bottom
                    self.dy = -self.dy

                self.block_sound.play()     # 効果音を鳴らす
                Ball.hit_sum += 1
                self.hit += 1               # 衝突回数
                self.score.add_score(self.hit * 10)   # 衝突回数に応じてスコア加点
        
        if Ball.hit_sum >= 10:
            Ball("png/rectangle.png", self.paddle, self.blocks, self.balls, self.score, 5, 135, 45, True, self.rect.left, self.rect.top, self.dx, self.dy)
            self.increase_sound.play()
            Ball.hit_sum = 0

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
        self.sysfont = pygame.font.SysFont("notosanscjksc", 30)
        self.score = 0
        (self.x, self.y) = (x, y)
    def draw(self, screen):
        img = self.sysfont.render("スコア: "+str(self.score), True, (255,255,255))
        screen.blit(img, (self.x, self.y))
    def add_score(self, x):
        self.score += x

class Stage():
    def __init__(self, x, y, detect_num):
        self.sysfont = pygame.font.SysFont("notosanscjksc", 40)
        self.detect_num = detect_num
        self.stage_num = 1
        self.text = self.sysfont.render("ステージ "+str(self.stage_num)+" / "+str(self.detect_num), True, (255,255,255))
        self.rect = self.text.get_rect()
        self.text = pygame.transform.rotozoom(self.text, 0, (RIGHT_AREA.width-RIGHT_AREA_MARGIN*2)/self.rect.width)
        (self.x, self.y) = (x, y)
    def draw(self, screen):
        screen.blit(self.text, (self.x, self.y))
    def next_stage(self):
        self.stage_num += 1
        self.text = self.sysfont.render("ステージ "+str(self.stage_num)+" / "+str(self.detect_num), True, (255,255,255))
        self.rect = self.text.get_rect()
        self.text = pygame.transform.rotozoom(self.text, 0, (RIGHT_AREA.width-RIGHT_AREA_MARGIN*2)/self.rect.width)

class Gauge():
    def __init__(self, x, y):
        self.sysfont = pygame.font.SysFont("notosanscjksc", 30)
        self.text = self.sysfont.render("ボール増殖ゲージ", True, (255,255,255))
        self.rect = self.text.get_rect()
        (self.x, self.y) = (x, y)
    def draw(self, screen, hit_sum):
        screen.blit(self.text, (self.x, self.y))
        pygame.draw.rect(screen, (255,255,255), Rect(self.x, self.y+self.rect.height+10, 440, self.rect.height), 1)
        if hit_sum > 10:
            hit_sum = 10
        pygame.draw.rect(screen, (255,255,255), Rect(self.x+2, self.y+self.rect.height+10+2, int((hit_sum/10)*436), self.rect.height-4))


class Key():
    def __init__(self):
        self.sysfont = pygame.font.SysFont("notosanscjksc", 40)
        self.text_p = self.sysfont.render("ポーズ", True, (255,255,255))
        self.text_a = self.sysfont.render("自動/手動 切り替え", True, (255,255,255))
        self.text_s = self.sysfont.render("ステージスキップ", True, (255,255,255))
        self.text_left= self.sysfont.render("二倍速　切り替え", True, (255,255,255))
        self.p_img = pygame.transform.rotozoom(pygame.image.load("png/P.jpg"), 0, 2)
        self.s_img = pygame.transform.rotozoom(pygame.image.load("png/S.jpg"), 0, 2)
        self.a_img = pygame.transform.rotozoom(pygame.image.load("png/A.jpg"), 0, 2)
        self.left_click = pygame.transform.rotozoom(pygame.image.load("png/left_click.png"), 0, 1/20)
    def draw(self, screen):
        pygame.draw.line(screen, (255,255,255), (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+525), (SCREEN.width - RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+525))
        screen.blit(self.p_img, (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+560))
        screen.blit(self.text_p, (RIGHT_AREA.left + RIGHT_AREA_MARGIN + 90, RIGHT_AREA_MARGIN+560))
        screen.blit(self.a_img, (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+670))
        screen.blit(self.text_a, (RIGHT_AREA.left + RIGHT_AREA_MARGIN + 90, RIGHT_AREA_MARGIN+670))
        screen.blit(self.s_img, (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+780))
        screen.blit(self.text_s, (RIGHT_AREA.left + RIGHT_AREA_MARGIN + 90, RIGHT_AREA_MARGIN+780))
        screen.blit(self.left_click, (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+890))
        screen.blit(self.text_left, (RIGHT_AREA.left + RIGHT_AREA_MARGIN + 90, RIGHT_AREA_MARGIN+890))

class Button():
    def __init__(self, x, y, size, pad, color, txtcolor, text, description1, description2, center=False):
        self.x = x
        self.y = y
        self.pad = pad
        self.color = color
        self.font = pygame.font.SysFont("notosanscjksc", size)
        self.font2 = pygame.font.SysFont("notosanscjksc", 40)
        self.text = self.font.render(text, True, txtcolor)
        if (center):
            self.x = x-(self.text.get_width() + pad//2)//2
            self.y = y+(self.text.get_height() + pad//2)//2
        self.button = Rect((self.x,self.y), (self.text.get_width() + pad, self.text.get_height() + pad))
        self.initial_button = Rect((self.x,self.y), (self.text.get_width() + pad, self.text.get_height() + pad))
        self.buttonUp = 1
        self.description1 = self.font2.render(description1, True, (0,0,0))
        self.description2 = self.font2.render(description2, True, (0,0,0))
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
            screen.blit(self.description1, Rect(self.initial_button.right + 10, self.initial_button.y-10, 200, self.initial_button.height))
            screen.blit(self.description2, Rect(self.initial_button.right + 10, self.initial_button.y-10+self.initial_button.height//2, 200, self.initial_button.height))
    
    def invFlag(self):
        self.hide = not self.hide

class Title():
    def __init__(self, logofile, musicfile, backfile):
        self.logo = pygame.image.load(logofile)
        pygame.mixer.music.load(musicfile)
        self.back_img = pygame.image.load(backfile)
        back_rect = self.back_img.get_rect()
        scale = SCREEN.width / back_rect.width
        self.back_img = pygame.transform.rotozoom(self.back_img, 0, scale)
        self.logo_rect = self.logo.get_rect()
        self.logo_img = pygame.transform.rotozoom(self.logo, 0, 0.9*SCREEN.width/self.logo_rect.width)
        self.logo_img_rect = self.logo_img.get_rect()
        # 画像の左上座標
        self.logo_img_rect.left = SCREEN.centerx - self.logo_img_rect.width // 2
        self.logo_img_rect.top = 30
        self.start_btn = Button(SCREEN.centerx, SCREEN.height * 0.7, 80, 16, (255, 0, 0), (255, 255, 255), "ゲーム開始", "", "", True)
        self.start_btn.hide = False
        self.play_bgm()

    def update(self):
        pass

    def draw(self, screen):
        screen.blit(self.back_img, (0, -50))
        screen.blit(self.logo_img, (SCREEN.centerx - self.logo_img_rect.width//2, SCREEN.height * 0.1))
        self.start_btn.draw(screen)

    def play_bgm(self):
        pygame.mixer.music.play(-1)      # BGM
    
    def stop_bgm(self):
        pygame.mixer.music.stop()

class Camera():
    def __init__(self, path, video, filename):
        self.path = path
        self.video = video
        self.detect_btn = Button(CAMERA_FRAME.x, SCREEN.height - CAMERA_MARGIN*4, 60, 16, (255, 0, 0), (255, 255, 255), "顔検出", "画面に顔が映るようにしてください。", "準備ができたらこのボタンを押してください。")
        self.playgame_btn = Button(CAMERA_FRAME.x+100, SCREEN.height - CAMERA_MARGIN*4, 60, 16, (255, 0, 0), (255, 255, 255), "ゲーム開始", "", "")
        self.reshoot_btn = Button(CAMERA_FRAME.x+850, SCREEN.height - CAMERA_MARGIN*4, 60, 16, (255, 0, 0), (255, 255, 255), "再検出", "", "")
        self.img = pygame.image.load(filename)
        self.img = pygame.transform.rotozoom(self.img, 0, 1.72)
        self.cascade = cv.CascadeClassifier(self.path)     # カスケード
        self.cap = cv.VideoCapture(self.video)             # ビデオキャプチャ
        if not (self.cap.isOpened()):
            print("cannot open video")
            exit(1)
        self.cap.set(cv.CAP_PROP_FPS, CAMERA_FPS)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.display_left = SCREEN.centerx - CAMERA_WIDTH/2
        self.display_top = CAMERA_MARGIN*5
        self.faces = []
        self.recognized = False
        self.face_num = 0

    def update(self):
        self.ret, self.frame = self.cap.read()
        if self.ret == False:
            print("cannot update video")
            exit(1)
        self.recognition()
        self.surface = self.cvtToSurface(self.frame)

    def draw(self, screen):
        screen.fill((200,200,200))
        screen.blit(self.img, (SCREEN.centerx - self.img.get_width()/2,-100))
        screen.blit(self.surface, (self.display_left-132, self.display_top+75))
        self.detect_btn.draw(screen)
        self.playgame_btn.draw(screen)
        self.reshoot_btn.draw(screen)
    
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
            self.copy2_frame = np.copy(self.frame)
            for x, y, w, h in self.faces:
                cv.rectangle(self.frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv.imwrite('png/detect.png', self.frame)
            self.recognized = True
        else:
            self.recognized = False
    
    def detect_num(self):
        return len(self.faces)

    def mosaic(self, img, size):
        return cv.resize(img, dsize=size, interpolation=cv.INTER_NEAREST)
    
    def create_block(self):
        x, y, width, height = self.faces[self.face_num]
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        roi = self.copy_frame[y:y+height, x:x+width]
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
            roi = cv.rotate(roi, cv.ROTATE_90_COUNTERCLOCKWISE)
            self.mosaic_frame = self.mosaic(roi, (int(width*SIZE_OF_MOSAIC/height), SIZE_OF_MOSAIC))
            scale = BLOCK_SIZE*SIZE_OF_MOSAIC/height
            self.inside_frame = self.copy2_frame[int(y-FACE_AREA.y/scale):CAMERA_HEIGHT,0:int(x+width+FACE_AREA.x/scale)]
            self.copy_surface = self.cvtToSurface(cv.resize(self.inside_frame,dsize=None,fx=scale,fy=scale,interpolation=cv.INTER_NEAREST))
            num_w = len(self.mosaic_frame[0])
            for i in range(SIZE_OF_MOSAIC):
                for j in range(num_w):
                    Block(self.mosaic_frame[i][j], FACE_AREA.y + i * BLOCK_SIZE, FACE_AREA.centerx - (num_w//2 - j) * BLOCK_SIZE)
        else:
            roi = cv.rotate(roi, cv.ROTATE_90_COUNTERCLOCKWISE)
            self.mosaic_frame = self.mosaic(roi, (SIZE_OF_MOSAIC, int(height*SIZE_OF_MOSAIC/width)))
            scale = BLOCK_SIZE*SIZE_OF_MOSAIC/width
            self.inside_frame = self.copy2_frame[int(y-FACE_AREA.y/scale):CAMERA_HEIGHT,0:int(x+width+FACE_AREA.x/scale)]
            self.copy_surface = self.cvtToSurface(cv.resize(self.inside_frame,dsize=None,fx=scale,fy=scale,interpolation=cv.INTER_NEAREST))
            num_h = len(self.mosaic_frame)
            for i in range(num_h):
                for j in range(SIZE_OF_MOSAIC):
                    Block(self.mosaic_frame[i][j], FACE_AREA.centery - (num_h//2 - i) * BLOCK_SIZE, FACE_AREA.x + j * BLOCK_SIZE)
        self.face_num += 1


class block_breaker:
    def __init__(self):
        """初期化"""
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN.size)
        pygame.display.set_caption("Block Breaker")
        self.space_sound = pygame.mixer.Sound("sound/space.wav")    
        self.backspace_sound = pygame.mixer.Sound("sound/backspace.wav")   
        self.posed_sound = pygame.mixer.Sound("sound/posed.wav")    
        # 描画用のスプライトグループ
        """TITLE"""
        self.title = Title("png/logo.png", "sound/bgm.wav", "png/lena_block.png")                      # タイトル画面
        """CAMERA"""
        self.path = '../../opencv/data/haarcascades/haarcascade_frontalface_default.xml'
        self.camera = Camera(self.path, 0, "png/camera.png")     # カメラ
        """RCOGNIZE"""
        """GAME"""
        Ball.paddle_sound = pygame.mixer.Sound("sound/paddle.wav")    # パドルにボールが衝突した時の効果音取得
        Ball.block_sound = pygame.mixer.Sound("sound/block.wav") # ブロックにボールが衝突した時の効果音取得
        Ball.increase_sound = pygame.mixer.Sound("sound/increase.wav") #
        self.gameover_sound = pygame.mixer.Sound("sound/over.wav")    # ゲームオーバー時の効果音取得
        self.gameclear_sound = pygame.mixer.Sound("sound/clear.wav")    # ゲームクリア時の効果音取得
        # 描画用のスプライトグループ
        self.game_group = pygame.sprite.RenderUpdates()
        self.game_group2 = pygame.sprite.RenderUpdates()
        # 衝突判定用のスプライトグループ
        self.blocks = pygame.sprite.Group()
        # ボール保持用のスプライトグループ   
        self.balls = pygame.sprite.Group()
        # スプライトグループに追加    
        Paddle.containers = self.game_group
        Ball.containers = self.game_group, self.balls, self.game_group2
        Block.containers = self.game_group, self.blocks, self.game_group2
        self.paddle = Paddle("png/paddle.png")                                  # パドルの作成
        self.score = Score(RIGHT_AREA.left+RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+140)                                          # スコアを画面(10, 10)に表示
        self.gauge = Gauge(RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+210)
        Ball("png/rectangle.png", self.paddle, self.blocks, self.balls, self.score, 5, 135, 45)  # ボールを作成
        self.key = Key()
        """POSED"""
        self.alpha_screen =pygame.Surface(SCREEN.size,flags=pygame.SRCALPHA) 
        self.font = pygame.font.SysFont("notosanscjksc", 90)
        """OVER"""
        """CLEAR"""
        self.finish_btn = Button(SCREEN.centerx, SCREEN.height * 0.7, 70, 16, (255, 0, 0), (255, 255, 255), "ゲーム終了", "", "", True)
        """NEXT"""
        self.next_btn = Button(SCREEN.centerx, SCREEN.height * 0.7, 70, 16, (255, 0, 0), (255, 255, 255), "次のステージ", "", "", True)
        """ループ開始"""
        self.game_state = TITLE                                             # ゲームの状態をTITLEにする
        self.fps = 60
        self.main_loop()                                                    # メインループを起動
    
    def main_loop(self):    
        clock = pygame.time.Clock()
        while True:
            clock.tick(self.fps)              # フレームレート(60fps)
            self.update()             # ゲーム状態の更新
            self.render()             # ゲームオブジェクトのレンダリング
            pygame.display.update()  # 画面に描画
            self.check_event()        # イベントハンドラ
    
    def update(self):
        """ゲーム状態の更新"""
        if self.game_state == TITLE:
            self.title.update()
        elif self.game_state == CAMERA:
            self.camera.update()
        elif self.game_state == RECOGNIZE:
            pass
        elif self.game_state == GAME:
            self.game_group.update()        # 全てのスプライトグループを更新
        elif self.game_state == POSED or self.game_state == OVER or self.game_state == CLEAR or self.game_state == NEXT:
            pass
        elif self.game_state == AUTO:
            self.game_group2.update()
            self.paddle.auto_update(self.balls)

    def render(self):
        """ゲームオブジェクトのレンダリング"""
        if self.game_state == TITLE:
            self.title.draw(self.screen)
        elif self.game_state == CAMERA:
            self.camera.draw(self.screen)
        elif self.game_state == RECOGNIZE:
            self.camera.draw(self.screen)
            text1 = pygame.font.SysFont("notosanscjksc", 40).render(str(self.detect_num)+"   個の顔を", True, (255,0,0))
            text2 = pygame.font.SysFont("notosanscjksc", 40).render("検知しました", True, (255,0,0))
            rect1 = text1.get_rect()
            self.screen.blit(text1, (SCREEN.centerx - rect1.width//4, SCREEN.height - CAMERA_MARGIN*4))
            self.screen.blit(text2, (SCREEN.centerx - rect1.width//4, SCREEN.height - CAMERA_MARGIN*4 + rect1.height))
        elif self.game_state == GAME:
            self.screen.fill((200,200,200))
            self.screen.blit(self.camera.copy_surface, (0,0))
            self.game_group.draw(self.screen)   # 全てのスプライトグループを描画 
            self.draw_right_area(self.screen)
        elif self.game_state == POSED:
            pass
        elif self.game_state == OVER or self.game_state == CLEAR:
            self.finish_btn.draw(self.screen)
        elif self.game_state == AUTO:
            self.screen.fill((200,200,200))
            self.screen.blit(self.camera.copy_surface, (0,0))
            self.game_group2.draw(self.screen)
            self.paddle.auto_draw(self.screen)
            self.draw_right_area(self.screen)
        elif self.game_state == NEXT:
            self.next_btn.draw(self.screen)
        
    def draw_right_area(self, screen):
        pygame.draw.rect(screen, (0,0,0), RIGHT_AREA)
        self.stage.draw(screen)        
        pygame.draw.line(screen, (255,255,255), (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+130), (SCREEN.width - RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+130))
        self.score.draw(screen)        
        pygame.draw.line(screen, (255,255,255), (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+200), (SCREEN.width - RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+200))
        hit_sum = Ball.hit_sum
        self.gauge.draw(screen, hit_sum)
        pygame.draw.line(screen, (255,255,255), (RIGHT_AREA.left + RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+335), (SCREEN.width - RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN+335))
        mode = ""
        if self.game_state == GAME:
            mode = "手動"
        else:
            mode = "自動"
        text1 = pygame.font.SysFont("notosanscjksc", 40).render(mode , True, (255,255,255))
        text1 = pygame.transform.rotozoom(text1, 0, 2)
        text2 = pygame.font.SysFont("notosanscjksc", 40).render("プレイ中", True, (255,255,255))
        rect1 = text1.get_rect()
        rect2 = text2.get_rect()
        screen.blit(text1, (RIGHT_AREA.centerx-rect1.width//2, RIGHT_AREA_MARGIN+340))
        screen.blit(text2, (RIGHT_AREA.centerx-rect2.width//2, RIGHT_AREA_MARGIN+450))
        self.key.draw(screen)

        
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
            elif self.game_state == CAMERA:
                self.camera_handler(event)
            elif self.game_state == RECOGNIZE:
                self.recognize_handler(event)
            elif self.game_state == GAME:
                self.game_handler(event)
                self.common_handler(event)
            elif self.game_state == POSED:
                self.posed_handler(event)
            elif self.game_state == OVER or self.game_state == CLEAR:
                self.finish_handler(event)
            elif self.game_state == AUTO:
                self.auto_handler(event)
                self.common_handler(event)
            elif self.game_state == NEXT:
                self.next_handler(event)

    def title_handler(self, event):
        """タイトル画面のイベントハンドラ"""
        if (self.title.start_btn.pushed(event)) or (event.type == KEYDOWN and event.key == K_SPACE):
            self.space_sound.play()
            self.camera.detect_btn.invFlag()
            self.game_state = CAMERA
    
    def camera_handler(self, event):
        """カメラ画面のイベントハンドラ"""
        if self.camera.detect_btn.pushed(event) or (event.type == KEYDOWN and event.key == K_SPACE):
            if self.camera.recognized:
                self.space_sound.play()
                self.camera.detect_btn.invFlag()
                self.camera.playgame_btn.invFlag()
                self.camera.reshoot_btn.invFlag()
                self.detect_num = self.camera.detect_num()
                self.game_state = RECOGNIZE
    
    def recognize_handler(self, event):
        """RECOGNIZEモードのイベントハンドラ"""
        if self.camera.playgame_btn.pushed(event) or (event.type == KEYDOWN and event.key == K_SPACE):
            self.space_sound.play()
            self.camera.playgame_btn.invFlag()
            self.camera.reshoot_btn.invFlag()
            self.camera.create_block()
            self.stage = Stage(RIGHT_AREA.left+RIGHT_AREA_MARGIN, RIGHT_AREA_MARGIN-10, self.detect_num)
            self.game_state = GAME
        elif self.camera.reshoot_btn.pushed(event) or (event.type == KEYDOWN and event.key == K_BACKSPACE):
            self.backspace_sound.play()
            self.camera.playgame_btn.invFlag()
            self.camera.reshoot_btn.invFlag()
            self.camera.detect_btn.invFlag()
            self.game_state = CAMERA
    
    def game_handler(self, event):
        """ゲーム画面のイベントハンドラ"""
        if event.type == KEYDOWN and event.key == K_a:
            self.fps = 120
            self.game_state = AUTO
        elif pygame.mouse.get_pressed()[0] == 1:
            self.fps = 120
        else:
            self.fps = 60
    
    def posed_handler(self, event):
        if event.type == KEYDOWN and event.key == K_p:
            self.posed_sound.play()
            self.game_state = GAME
        elif event.type == KEYDOWN and event.key == K_a:
            self.fps = 120
            self.posed_sound.play()
            self.game_state = AUTO
    
    def finish_handler(self, event):
        if self.finish_btn.pushed(event)  or (event.type == KEYDOWN and event.key == K_SPACE):
            self.space_sound.play()
            exit(1)

    def auto_handler(self, event):
        if event.type == KEYDOWN and event.key == K_a:
            self.fps = 60
            self.game_state = GAME
        
        
    def common_handler(self, event):
        if event.type == KEYDOWN and event.key == K_p:
            self.posed_sound.play()
            self.blit_alpah_screen("ポーズ")
            self.game_state = POSED
        elif event.type == GAMEOVER:
            self.title.stop_bgm()
            self.gameover_sound.play()
            self.finish_btn.invFlag()
            self.blit_alpah_screen("ゲームオーバー")
            self.game_state = OVER
        elif event.type == GAMECLEAR or (event.type == KEYDOWN and event.key == K_s):
            self.title.stop_bgm()
            self.gameclear_sound.play()
            if self.stage.stage_num < self.detect_num:
                self.next_btn.invFlag()
                self.blit_alpah_screen("ステージクリア！")
                self.game_state = NEXT
            else:
                self.finish_btn.invFlag()
                self.blit_alpah_screen("ゲームクリア！")
                self.game_state = CLEAR
    
    def next_handler(self, event):
        if self.finish_btn.pushed(event)  or (event.type == KEYDOWN and event.key == K_SPACE):
            self.stage.next_stage()
            for ball in self.balls:
                ball.rect.x = 100
                ball.rect.y = SCREEN.height + 100
                ball.dx = 0
                ball.dy = 0
                self.hit_sum = 0
                self.balls.remove(ball)
                self.game_group.remove(ball)
                self.game_group2.remove(ball)
            Ball("png/rectangle.png", self.paddle, self.blocks, self.balls, self.score, 5, 135, 45)  # ボールを作成
            for block in self.blocks:
                self.blocks.remove(block)
                self.game_group.remove(block)
                self.game_group2.remove(block)
            self.camera.create_block()
            self.game_state = GAME

    def blit_alpah_screen(self, txt):
        self.alpha_screen.fill((0,0,0,128))
        text = self.font.render(txt, True, (255,255,255))
        rect = text.get_rect()
        self.alpha_screen.blit(text, (SCREEN.centerx-rect.width/2, SCREEN.centery-rect.height))
        self.screen.blit(self.alpha_screen,(0,0))

if __name__ == "__main__":
    block_breaker()