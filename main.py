import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100
HEIGHT = 650
os.chdir(os.path.dirname(os.path.abspath(__file__)))


# 共通関数
def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内にあるかを判定する関数
    戻り値：(横方向, 縦方向)
    True  : 画面内
    False : 画面外
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    org から dst への方向ベクトルを計算する関数
    敵の爆弾が自機を狙うために使用
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2 + y_diff**2)
    return x_diff/norm, y_diff/norm


# 自機（こうかとん）
class Bird(pg.sprite.Sprite):
    """
    プレイヤーが操作するキャラクター
    矢印キーで移動
    """
    delta = {
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)

        # 向きごとの画像
        self.imgs = {
            (+1, 0): img,
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),
            (-1, 0): img0,
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),
        }

        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect(center=xy)
        self.speed = 10

    def update(self, key_lst, screen):
        """
        押下キーに応じて移動処理
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]

        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])

        # 画面外に出たら元に戻す
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])

        # 向きが変わったら画像更新
        if sum_mv != [0, 0]:
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        screen.blit(self.image, self.rect)



# ビーム（自機攻撃）
class Beam(pg.sprite.Sprite):
    """
    自機が発射するビーム
    向いている方向に直進
    """
    def __init__(self, bird: Bird):
        super().__init__()
        vx, vy = bird.dire
        angle = math.degrees(math.atan2(-vy, vx))
        self.image = pg.transform.rotozoom(pg.image.load("fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centerx = bird.rect.centerx + bird.rect.width*self.vx
        self.rect.centery = bird.rect.centery + bird.rect.height*self.vy
        self.speed = 10

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()



# 敵キャラ（HP・レベル制）
class Enemy(pg.sprite.Sprite):
    """
    敵機クラス
    ・HP制
    ・レベルに応じてHP増加
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self, level: int):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect(center=(random.randint(0, WIDTH), 0))

        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)
        self.state = "down"
        self.interval = random.randint(50, 300)

        # 追加機能：敵HP（最初から一撃死しない）
        self.level = level
        self.max_hp = 2 + level
        self.hp = self.max_hp

    def update(self):
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)



# 敵の爆弾
class Bomb(pg.sprite.Sprite):
    """
    敵が投下する弾
    自機を狙って飛ぶ
    """
    def __init__(self, emy: Enemy, bird: Bird):
        super().__init__()
        rad = random.randint(10, 30)
        self.image = pg.Surface((2*rad, 2*rad))
        pg.draw.circle(self.image, (255, 0, 0), (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect(center=emy.rect.center)
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.speed = 6

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()



# 爆発エフェクト
class Explosion(pg.sprite.Sprite):
    """
    敵撃破時の爆発演出
    """
    def __init__(self, obj, life):
        super().__init__()
        img = pg.image.load("fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        self.life -= 1
        self.image = self.imgs[self.life//10 % 2]
        if self.life < 0:
            self.kill()


# スコア管理
class Score:
    """
    スコア表示クラス
    ・命中で加点
    ・撃破でボーナス
    """
    def __init__(self):
        self.font = pg.font.Font(None, 40)
        self.value = 2000

    def update(self, screen):
        img = self.font.render(f"Score: {self.value}", True, (0, 0, 255))
        screen.blit(img, (20, HEIGHT-40))



# レベル表示UI
class LevelUI:
    """
    現在のゲームレベルを表示
    """
    def __init__(self):
        self.font = pg.font.Font(None, 40)

    def update(self, screen, level):
        img = self.font.render(f"Level: {level}", True, (0, 0, 255))
        screen.blit(img, (20, HEIGHT-80))


# メイン処理
def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg = pg.image.load("fig/pg_bg.jpg")

    bird = Bird(3, (900, 400))
    beams = pg.sprite.Group()
    bombs = pg.sprite.Group()
    emys = pg.sprite.Group()
    exps = pg.sprite.Group()

    score = Score()
    level_ui = LevelUI()

    clock = pg.time.Clock()
    tmr = 0

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                beams.add(Beam(bird))

        screen.blit(bg, (0, 0))
        key_lst = pg.key.get_pressed()

        #追加機能：時間経過によるレベル
        level = tmr // 1000 + 1

        # 敵生成
        if tmr % 200 == 0:
            emys.add(Enemy(level))

        # 敵の爆弾投下
        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        #追加機能：命中・撃破処理
        hits = pg.sprite.groupcollide(emys, beams, False, True)
        for emy, hit_beams in hits.items():
            emy.hp -= len(hit_beams)
            score.value += len(hit_beams)

            if emy.hp <= 0:
                exps.add(Explosion(emy, 100))
                emy.kill()
                score.value += 10 + emy.level*5

        # 被弾でゲーム終了
        if pg.sprite.spritecollide(bird, bombs, True):
            return

        bird.update(key_lst, screen)
        beams.update()
        bombs.update()
        emys.update()
        exps.update()

        beams.draw(screen)
        bombs.draw(screen)
        emys.draw(screen)
        exps.draw(screen)

        score.update(screen)
        level_ui.update(screen, level)

        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
