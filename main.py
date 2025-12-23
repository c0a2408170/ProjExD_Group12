import math
import os
import random
import sys
import time
import pygame as pg

WIDTH = 900
HEIGHT = 800
HUD_WIDTH = 300
GAME_WIDTH = WIDTH - HUD_WIDTH

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数 obj_rct：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or GAME_WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgからdstへの方向ベクトルを計算する関数
    引数 org：始点のRect
    引数 dst：終点のRect
    戻り値：x方向，y方向の単位ベクトル成分のタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数 num：こうかとん画像ファイル名の番号
        引数 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self.imgs = {
            (+1, 0): img,
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),
            (-1, 0): img0,
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect(center=xy)
        self.speed = 10

    def update(self, key_lst, screen):
        """
        押下キーに応じてこうかとんを移動させる
        引数 key_lst：押下キーの辞書
        引数 screen：画面Surface
        """
        mv = [0, 0]
        for k, d in self.delta.items():
            if key_lst[k]:
                mv[0] += d[0]
                mv[1] += d[1]
        self.rect.move_ip(self.speed*mv[0], self.speed*mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*mv[0], -self.speed*mv[1])
        if mv != [0, 0]:
            self.dire = tuple(mv)
            self.image = self.imgs.get(self.dire, self.image)
        screen.blit(self.image, self.rect)


class Enemy(pg.sprite.Sprite):
    """
    敵機（エイリアン）に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        """
        敵機画像Surfaceを生成する
        画面上部からランダムな位置に出現し、降下する
        """
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(self.imgs), 0, 0.8)
        self.rect = self.image.get_rect(center=(random.randint(0, GAME_WIDTH), 0))
        self.vy = 5
        self.bound = random.randint(50, HEIGHT//2)
        self.state = "down"
        self.interval = random.randint(60, 200)

    def update(self):
        """
        敵機を速度ベクトルに従って移動させる
        一定の高さ（self.bound）に達したら停止する
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(0, self.vy)


class Bomb(pg.sprite.Sprite):
    """
    敵機が発射する爆弾に関するクラス
    """
    def __init__(self, emy, bird):
        """
        爆弾画像Surfaceを生成する
        引数 emy：爆弾を放つ敵機インスタンス
        引数 bird：攻撃対象のこうかとんインスタンス
        """
        super().__init__()
        scale = random.randint(1, 3) / 10
        self.image = pg.transform.rotozoom(pg.image.load("fig/敵弾.png"), 0, scale)
        self.rect = self.image.get_rect(center=emy.rect.center)
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.speed = 6
        self.inactive = False

    def update(self):
        """
        爆弾を速度ベクトルに従って移動させる
        画面外に出たら削除される
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    こうかとんが発射するビームに関するクラス
    """
    def __init__(self, bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとんインスタンス
        """
        super().__init__()
        self.image = pg.transform.rotozoom(pg.image.load("fig/弾.png"), 0, 0.1)
        self.rect = self.image.get_rect(center=bird.rect.center)
        self.vx, self.vy = bird.dire
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルに従って移動させる
        画面外に出たら削除される
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound( self.rect) != (True, True):
            self.kill()


class EMP(pg.sprite.Sprite):
    """
    電磁パルス（EMP）に関するクラス
    発動時に敵の攻撃を無効化する
    """
    def __init__(self, emys, bombs):
        """
        EMP発動時の効果を設定する
        引数 emys：敵機グループ
        引数 bombs：敵爆弾グループ
        """
        super().__init__()
        self.life = 10
        for e in emys:
            e.interval = math.inf
        for b in bombs:
            b.inactive = True
            b.speed //= 2

    def update(self):
        """
        EMPの効果時間を管理する
        """
        self.life -= 1
        if self.life < 0:
            self.kill()


def draw_ui(screen, score, lives, skill_count, decorative_img):
    """
    ゲーム画面右側のUIエリア（HUD）を描画する関数
    引数 screen：画面Surface
    引数 score：現在のスコア
    引数 lives：残機数
    引数 skill_count：スキル使用可能回数
    引数 decorative_img：UI下部に表示する装飾画像
    """
    # --- HUD背景 ---
    pg.draw.rect(screen, (20, 20, 20), (GAME_WIDTH, 0, HUD_WIDTH, HEIGHT))
    
    font_title = pg.font.Font(None, 60)
    font_big = pg.font.Font(None, 48)
    font_mid = pg.font.Font(None, 36)

    x = GAME_WIDTH + 20
    y = 30

    # --- TITLE ---
    screen.blit(font_mid.render("GAME TITLE", True, (255, 255, 0)), (x, y))
    screen.blit(font_title.render("Koukaton", True, (255, 100, 50)), (x, y + 30))

    y += 120

    # --- SCORE ---
    screen.blit(font_mid.render("SCORE", True, (200, 200, 255)), (x, y))
    screen.blit(font_big.render(str(score), True, (255, 255, 255)), (x, y+30))

    y += 120
    
    # --- LIFE (赤丸) ---
    screen.blit(font_mid.render("LIFE", True, (255, 200, 200)), (x, y))
    for i in range(lives):
        pg.draw.circle(screen, (255, 100, 100), (x+20+i*35, y+50), 12)

    y += 120
    
    # --- SKILL (緑丸) ---
    screen.blit(font_mid.render("SKILL", True, (200, 255, 200)), (x, y))
    for i in range(skill_count):
        pg.draw.circle(screen, (100, 255, 100), (x+20+i*35, y+50), 12)

    # --- 下部画像追加 ---
    img_rect = decorative_img.get_rect()
    img_x = GAME_WIDTH + (HUD_WIDTH - img_rect.width) // 2
    img_y = HEIGHT - img_rect.height - 130 
    screen.blit(decorative_img, (img_x, img_y))

def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("こうかとん無双 UI完成版")

    bird = Bird(3, (GAME_WIDTH//2, HEIGHT - 100))
    emys = pg.sprite.Group()
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    emps = pg.sprite.Group()

    # 右下の余白に表示するための画像を読み込み
    ui_img_original = pg.image.load("fig/3.png") 
    ui_img = pg.transform.rotozoom(ui_img_original, 0, 3.0)

    score = 0
    lives = 3
    skill_count = 3

    clock = pg.time.Clock()
    tmr = 0

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if skill_count > 0:
                    skill_count -= 1
                    emps.add(EMP(emys, bombs))

        key_lst = pg.key.get_pressed()
        screen.fill((0, 0, 0))

        if tmr % 120 == 0:
            emys.add(Enemy())

        for e in emys:
            if e.state == "stop" and tmr % e.interval == 0:
                bombs.add(Bomb(e, bird))

        bird.update(key_lst, screen)
        beams.update()
        bombs.update()
        emys.update()
        emps.update()

        beams.draw(screen)
        bombs.draw(screen)
        emys.draw(screen)

        for _ in pg.sprite.groupcollide(emys, beams, True, True):
            score += 10
        for b in pg.sprite.spritecollide(bird, bombs, True):
            if not b.inactive:
                lives -= 1
                if lives <= 0:
                    return

        draw_ui(screen, score, lives, skill_count, ui_img)

        pg.display.update()
        tmr += 1
        clock.tick(50)

if __name__ == "__main__":
    main()
    pg.quit()
    sys.exit()