# -*- coding: utf-8 -*-
from ctypes.wintypes import tagRECT
import pygame
from pygame.locals import *
import math
import sys
import pygame.mixer
import cv2 as cv
import numpy as np
from PIL import Image, ImageDraw

CAMERA_FPS = 30

# サイズ
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_MARGIN = 40
FACE_MARGIN = 104

CAMERA_AREA = Rect(0, 0, CAMERA_WIDTH+CAMERA_MARGIN*2, CAMERA_HEIGHT+CAMERA_MARGIN*2)
CAMERA_FRAME = Rect(CAMERA_MARGIN, CAMERA_MARGIN, CAMERA_WIDTH, CAMERA_HEIGHT)
LEFT_AREA = Rect(0, 0, CAMERA_AREA.width, CAMERA_AREA.height+320)
RIGHT_AREA = Rect(LEFT_AREA.width, 0, 320, LEFT_AREA.height)
SCREEN = Rect(0, 0, LEFT_AREA.width+RIGHT_AREA.width, LEFT_AREA.height)
FACE_AREA = Rect(FACE_MARGIN, FACE_MARGIN, LEFT_AREA.width-FACE_MARGIN*2, LEFT_AREA.width-FACE_MARGIN*2)

SIZE_OF_MOSAIC = 32

BLOCK_SIZE = int(FACE_AREA.width / SIZE_OF_MOSAIC)

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
    def __init__(self, color, x, y):
        pygame.sprite.Sprite.__init__(self, self.containers)
        print(color)
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
        self.sysfont = pygame.font.SysFont(None, 20)
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
    
    def invFlag(self):
        self.hide = not self.hide

class Title():
    def __init__(self, filename):
        self.logo = pygame.image.load(filename)
        self.logo_rect = self.logo.get_rect()
        self.logo_img = pygame.transform.rotozoom(self.logo, 0, 0.9*SCREEN.width/self.logo_rect.width)
        self.logo_img_rect = self.logo_img.get_rect()
        # 画像の左上座標
        self.logo_img_rect.left = SCREEN.centerx - self.logo_img_rect.width // 2
        self.logo_img_rect.top = 30
        self.start_btn = Button(SCREEN.centerx, SCREEN.height * 0.6, 80, 16, (255, 0, 0), (255, 255, 255), "START", True)
        self.start_btn.hide = False
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
    def __init__(self, path, video):
        self.path = path
        self.video = video
        self.detect_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height+100, 80, 16, (255, 0, 0), (255, 255, 255), "DETECT", True)
        self.playgame_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height+60, 80, 16, (255, 0, 0), (255, 255, 255), "PLAY GAME", True)
        self.reshoot_btn = Button(LEFT_AREA.centerx, CAMERA_AREA.height+140, 80, 16, (255, 0, 0), (255, 255, 255), "RESHOOT", True)
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

    def update(self):
        self.ret, self.frame = self.cap.read()
        if self.ret == False:
            print("cannot update video")
            exit(1)
        cv.imshow("result", self.frame)
        if(cv.waitKey(10) & 0xFF == ord('q')):
            cv.destroyAllWindows()
            self.cap.release()
        self.recognition()
        self.surface = self.cvtToSurface(self.frame)

    def draw(self, screen):
        screen.fill((0,128,0))
        screen.blit(self.surface, (self.display_left, self.display_top))
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
            for x, y, w, h in self.faces:
                cv.rectangle(self.frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv.imwrite('detect.png', self.frame)
            self.recognized = True
        else:
            self.recognized = False

    def mosaic(self, img, scale):
        h, w = img.shape[:2]  # 画像の大きさ
        # 画像を scale (0 < scale <= 1) 倍に縮小する。
        tmp = cv.resize(img, dsize=None, fx=scale, fy=scale, interpolation=cv.INTER_NEAREST)
        # # 元の大きさに拡大する。
        # dst = cv.resize(tmp, dsize=(w, h), interpolation=cv.INTER_NEAREST)
        # return dst
        return tmp
    
    def create_block(self):
        x, y, width, height = self.faces[self.face_num]
        y0 = int(y - height*0.3)
        y1 = int(y + height*1.3)
        x0 = int(x - width*0.3)
        x1 = int(x + width*1.3)
        roi = self.copy_frame[y0:y1, x0:x1]
        if width < height:
            # self.copy_frame[y0:y1, x0:x1] = self.mosaic(roi, SIZE_OF_MOSAIC/height)
            self.mosaic_frame = self.mosaic(roi, SIZE_OF_MOSAIC/height)
            self.cvtToSurface(self.mosaic_frame)
            num_w = len(self.mosaic_frame[0])
            for i in range(len(self.mosaic_frame[0])):
                for j in range(SIZE_OF_MOSAIC):
                    Block(self.mosaic_frame[i][j], LEFT_AREA.centerx - (num_w - i) * BLOCK_SIZE, FACE_AREA.y + j * BLOCK_SIZE)
        else:
            self.mosaic_frame = self.mosaic(roi, SIZE_OF_MOSAIC/width)
            self.cvtToSurface(self.mosaic_frame)
            num_h = len(self.mosaic_frame)
            for i in range(SIZE_OF_MOSAIC):
                for j in range(len(self.mosaic_frame)):
                    Block(self.mosaic_frame[i][j], LEFT_AREA.x + i * BLOCK_SIZE, FACE_AREA.centery - (num_h - j) * BLOCK_SIZE)

        cv.imshow("result", self.copy_frame)
        if(cv.waitKey(10) & 0xFF == ord('q')):
            cv.destroyAllWindows()
            self.cap.release()



class block_breaker:
    def __init__(self):
        """初期化"""
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN.size)
        pygame.display.set_caption("Block Breaker")
        """TITLE"""
        Title.bgm_sound = pygame.mixer.Sound("sound/dq1.wav") # タイトル画面のBGM取得
        self.title = Title("png/logo.png")                      # タイトル画面
        """SELECT"""
        self.select =  Select()                                             # セレクト画面
        """CAMERA"""
        self.path = '../../opencv/data/haarcascades/haarcascade_frontalface_default.xml'
        self.camera = Camera(self.path, 0)     # カメラ
        """RCOGNIZE"""
        """GAME"""
        Ball.paddle_sound = pygame.mixer.Sound("sound/dq1.wav")    # パドルにボールが衝突した時の効果音取得
        Ball.block_sound = pygame.mixer.Sound("sound/dq1.wav") # ブロックにボールが衝突した時の効果音取得
        Ball.gameover_sound = pygame.mixer.Sound("sound/dq1.wav")    # ゲームオーバー時の効果音取得
        # 描画用のスプライトグループ
        self.game_group = pygame.sprite.RenderUpdates()
        # 衝突判定用のスプライトグループ
        self.blocks = pygame.sprite.Group()   
        # スプライトグループに追加    
        Paddle.containers = self.game_group
        Ball.containers = self.game_group
        Block.containers = self.game_group, self.blocks
        self.paddle = Paddle("png/paddle.png")                                  # パドルの作成
        self.score = Score(10, 10)                                          # スコアを画面(10, 10)に表示
        Ball("png/ball.png", self.paddle, self.blocks, self.score, 5, 135, 45)  # ボールを作成
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
            self.game_state = GAME
        elif self.camera.reshoot_btn.pushed(event):
            self.camera.playgame_btn.invFlag()
            self.camera.reshoot_btn.invFlag()
            self.camera.detect_btn.invFlag()
            self.game_state = CAMERA
    
    def game_handler(self, event):
        """ゲーム画面のイベントハンドラ"""
        if event.type == KEYDOWN and event.key == K_p:
            print('pushed "P"')

if __name__ == "__main__":
    block_breaker()