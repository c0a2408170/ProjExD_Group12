import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1200
HEIGHT = 750
HUD_WIDTH = 300
GAME_WIDTH = WIDTH - HUD_WIDTH # ゲーム画面の幅

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
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
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
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
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
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
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

        self.invincible = False
        self.invincible_timer = 0
        self.rapid_fire = False
        self.shot_interval = 10
        self.shot_timer = 0

    def skill(self, skill_count: int, fps: int = 50) -> tuple[bool, int]:
        if skill_count <= 0:
            return False, skill_count
        skill_count -= 1
        self.invincible = True
        self.invincible_timer = fps * 5
        self.rapid_fire = True
        return True, skill_count

    def change_img(self, num: int, screen: pg.Surface):
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False
                self.rapid_fire = False

        self.shot_interval = 5 if self.rapid_fire else 10
        self.shot_timer += 1
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", rad: int, speed: int, angle: int):
        super().__init__()
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        radian = math.radians(angle)
        self.vx = speed * math.cos(radian)
        self.vy = -speed * math.sin(radian)

    def update(self):
        self.rect.move_ip(self.vx, self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0 = 0):
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = 90
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle + angle0, 1.0)
        self.vx = math.cos(math.radians(angle + angle0))
        self.vy = -math.sin(math.radians(angle + angle0))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        self.attack = 1

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam(pg.sprite.Sprite):
    """
    弾幕に関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        super().__init__()
        self.bird = bird
        self.num = num
    
    def gen_beams(self):
        beams = []
        for arg in range(-30, 31, int(60/(self.num-1))):
            angle0 = arg
            beam = Beam(self.bird, angle0)
            beams.append(beam)
        return beams


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        self.life -= 1
        self.image = self.imgs[self.life//10 % 2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self, level: int = 1):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect(center=(random.randint(0, GAME_WIDTH), 0))
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)
        self.state = "moving"
        self.interval = random.randint(50, 80)
        self.max_hp = 3 + level
        self.hp = self.max_hp
        self.offset_frames = 0
        self.ready_to_shoot = True
        

    def update(self):
        if self.state == "moving":
            self.rect.move_ip(self.vx, self.vy)
            if self.rect.centery >= self.bound:
                self.vy = 0
                self.state = "stop"
                self.ready_to_shoot = True

        elif self.state == "stop":
            pass

        elif self.state == "shoot":
            self.offset_frames = 20
            self.offset_vx = random.randint(-3, 3)
            self.offset_vy = random.randint(-3, 3)
            self.state = "offset"

        elif self.state == "offset":
            if self.offset_frames > 0:
                self.rect.y += self.offset_vx
                self.rect.x += self.offset_vy
                self.offset_frames -= 1
            else:
                self.state = "stop"

    def draw_hp(self, screen: pg.Surface):
        bar_width = self.rect.width
        bar_height = 5
        hp_ratio = max(self.hp / self.max_hp, 0)
        fill_width = int(bar_width * hp_ratio)
        bg_rect = pg.Rect(self.rect.left, self.rect.top - bar_height - 2, bar_width, bar_height) 
        pg.draw.rect(screen, (255, 0, 0), bg_rect) 
        fg_rect = pg.Rect(self.rect.left, self.rect.top - bar_height - 2, fill_width, bar_height) 
        pg.draw.rect(screen, (0, 255, 0), fg_rect)


class EnemyAttack(pg.sprite.Sprite):
    """
    敵の弾幕を設定するクラス
    """
    def __init__(self, enemy: Enemy, bird: Bird):
        self.enemy = enemy
        self.bird = bird

    def kotei(self, rad: int, speed: int, num: int, angle_hani: int):
        self.rad = rad
        self.speed = speed
        self.num = num
        self.angle_hani = angle_hani
        bombs = []
        base_angle = 270  #下向き
        if self.num == 1:
            angle = base_angle
            bomb = Bomb(self.enemy, rad, speed, angle)
            bombs.append(bomb)
        else:
            start = -self.angle_hani // 2 
            step = self.angle_hani // (self.num - 1)
            for i in range(self.num):
                angle = base_angle + start + step * i
                bomb = Bomb(self.enemy, self.rad, self.speed, angle)
                bombs.append(bomb)
        return bombs

    def jiki(self, rad: int, speed: int, num: int, angle_hani: int):
        self.rad = rad
        self.speed = speed
        self.num = num
        self.angle_hani = angle_hani
        bombs = []
        dx = self.bird.rect.centerx - self.enemy.rect.centerx
        dy = self.enemy.rect.centery - self.bird.rect.centery
        base_angle = math.degrees(math.atan2(dy, dx))
        if self.num == 1:
            angle = base_angle
            bomb = Bomb(self.enemy, rad, speed, angle)
            bombs.append(bomb)
        else:
            start = -self.angle_hani // 2
            step = self.angle_hani // (self.num - 1)
            for i in range(self.num):
                angle = base_angle + start + step * i
                bomb = Bomb(self.enemy, self.rad, self.speed, angle)
                bombs.append(bomb)
        return bombs


# class Score:
#     """
#     打ち落とした爆弾，敵機の数をスコアとして表示するクラス
#     爆弾：1点
#     敵機：10点
#     """
#     def __init__(self):
#         self.font = pg.font.Font(None, 50)
#         self.color = (0, 0, 255)
#         self.value = 0
#         self.image = self.font.render(f"Score: {self.value}", 0, self.color)
#         self.rect = self.image.get_rect()
#         self.rect.center = 100, HEIGHT-50

#     def update(self, screen: pg.Surface):
#         self.image = self.font.render(f"Score: {self.value}", 0, self.color)
#         screen.blit(self.image, self.rect)


class EMP(pg.sprite.Sprite):
    """
    発動時に存在する敵機と爆弾を無効化するクラス
    """
    def __init__(self, emy_group: pg.sprite.Group, bomb_group: pg.sprite.Group, screen: pg.Surface, life_frames: int = 3):
        super().__init__()
        # 修正：エフェクトのサイズをゲーム画面幅に合わせる
        surf = pg.Surface((GAME_WIDTH, HEIGHT), flags=pg.SRCALPHA)
        surf.fill((255, 255, 0, 100))  # 透過黄色
        self.image = surf
        self.rect = self.image.get_rect()
        self.life = life_frames
        
        for emy in list(emy_group):
            emy.interval = math.inf
            emy.disabled_by_emp = True
            emy.image = pg.transform.laplacian(emy.image)
        for bomb in list(bomb_group):
            bomb.speed /= 2
            bomb.inactive = True

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


class shield(pg.sprite.Sprite):
    """
    防御壁を展開するクラス
    """
    def __init__(self, bird, life = 400):
        super().__init__()
        w, h = 20, bird.rect.height * 2
        self.image = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, w, h))
        vx, vy = bird.dire
        angel = math.degrees(math.atan2(-vy, vx))
        self.image = pg.transform.rotozoom(self.image, angel, 1.0)
        self.rect = self.image.get_rect()
        offset = max(bird.rect.width, bird.rect.height)
        self.rect.centerx = bird.rect.centerx + vx * offset
        self.rect.centery = bird.rect.centery + vy * offset
        self.rect.center = (self.rect.centerx, self.rect.centery)
        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


class Gravity(pg.sprite.Sprite):
    """
    重力場（半透明の黒い矩形）に関するクラス
    """
    def __init__(self, life: int):
        super().__init__()
        self.life = life
        # 修正：重力場のサイズをゲーム画面幅に合わせる
        self.image = pg.Surface((GAME_WIDTH, HEIGHT))
        pg.draw.rect(self.image,(0, 0, 0),(0, 0, GAME_WIDTH, HEIGHT))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()


class BossEnemy(Enemy):
    def __init__(self, level: int = 5):
        super().__init__(level)
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 3.0)
        self.rect = self.image.get_rect()
        self.rect.center = GAME_WIDTH//2, 100 # 出現位置をGAME_WIDTH中心に
        self.vx, self.vy = 3, 0
        self.max_hp = 50 + level*10
        self.hp = self.max_hp
        self.state = "alive"

    def update(self):
        self.rect.x += self.vx
        if self.rect.right >= GAME_WIDTH or self.rect.left <= 0: # 範囲をGAME_WIDTHに
            self.vx *= -1

    def draw_hp(self, screen: pg.Surface):
        bar_width = self.rect.width
        bar_height = 15
        hp_ratio = max(self.hp / self.max_hp, 0)
        fill_width = int(bar_width * hp_ratio)
        bg_rect = pg.Rect(self.rect.left, self.rect.top - bar_height - 5, bar_width, bar_height)
        pg.draw.rect(screen, (255, 0, 0), bg_rect)
        fg_rect = pg.Rect(self.rect.left, self.rect.top - bar_height - 5, fill_width, bar_height)
        pg.draw.rect(screen, (0, 255, 0), fg_rect)


class SkillFlash(pg.sprite.Sprite):
    """
    スキル発動時のフラッシュ演出
    """
    def __init__(self, life: int = 12, alpha_hi: int = 180, alpha_lo: int = 0):
        super().__init__()
        # 修正：エフェクトをゲーム画面幅に合わせる
        self.image = pg.Surface((GAME_WIDTH, HEIGHT), flags=pg.SRCALPHA)
        self.image.fill((255, 255, 255, alpha_hi))
        self.rect = self.image.get_rect()
        self.life = life
        self.alpha_hi = alpha_hi
        self.alpha_lo = alpha_lo
        self.toggle_interval = 2

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()
            return
        if (self.life // self.toggle_interval) % 2 == 0:
            self.image.fill((255, 255, 255, self.alpha_hi))
        else:
            self.image.fill((255, 255, 255, self.alpha_lo))


def draw_ui(screen, score, lives, skill_count, decorative_img):
    """
    UI描画関数（右画面用スクリーンを受け取るように修正）
    """
    # 修正：背景クリアの座標を (0, 0) からの相対座標に変更（screen自体がHUD用Surfaceのため）
    pg.draw.rect(screen, (20, 20, 20), (0, 0, HUD_WIDTH, HEIGHT))
    
    font_title = pg.font.Font(None, 60)
    font_big = pg.font.Font(None, 48)
    font_mid = pg.font.Font(None, 36)

    # 修正：描画開始位置 x を 20 に変更（GAME_WIDTHのオフセットを除去）
    x = 20
    y = 30

    screen.blit(font_mid.render("GAME TITLE", True, (255, 255, 0)), (x, y))
    screen.blit(font_title.render("Koukaton", True, (255, 100, 50)), (x, y + 30))

    y += 120

    screen.blit(font_mid.render("SCORE", True, (200, 200, 255)), (x, y))
    screen.blit(font_big.render(str(score), True, (255, 255, 255)), (x, y+30))

    y += 120
    
    screen.blit(font_mid.render("LIFE", True, (255, 200, 200)), (x, y))
    for i in range(lives):
        pg.draw.circle(screen, (255, 100, 100), (x+20+i*35, y+50), 12)

    y += 120
    
    screen.blit(font_mid.render("SKILL", True, (200, 255, 200)), (x, y))
    for i in range(skill_count):
        pg.draw.circle(screen, (100, 255, 100), (x+20+i*35, y+50), 12)

    if decorative_img:
        img_rect = decorative_img.get_rect()
        # 修正：画像の中央揃え計算をHUD幅基準に変更
        img_x = (HUD_WIDTH - img_rect.width) // 2
        img_y = HEIGHT - img_rect.height - 130 
        screen.blit(decorative_img, (img_x, img_y))


def main():
    pg.display.set_caption("東工プロジェクト")
    
    # 修正：Window全体用の親スクリーンを定義
    root_screen = pg.display.set_mode((WIDTH, HEIGHT))
    
    # 修正：ゲーム画面用スクリーンと右UI画面用スクリーンを定義
    screen = pg.Surface((GAME_WIDTH, HEIGHT))
    ui_screen = pg.Surface((HUD_WIDTH, HEIGHT))
    
    bg_img = pg.image.load(f"fig/haikei_2.png")
    score = 0

    bird = Bird(3, (GAME_WIDTH//2, HEIGHT - 100))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emps = pg.sprite.Group()

    gravities = pg.sprite.Group()
    shields = pg.sprite.Group()
    boss_spawned = False
    skill_flashes = pg.sprite.Group()

    try:
        ui_img_original = pg.image.load("fig/3.png") 
        ui_img = pg.transform.rotozoom(ui_img_original, 0, 3.0)
    except FileNotFoundError:
        ui_img = None

    score =500
    lives = 3
    tmr = 0
    clock = pg.time.Clock()
    shot_interval = 10
    boss_spawned = False
    skill_count = 3
    attack = None

    while True:
        key_lst = pg.key.get_pressed()
        shot_interval = bird.shot_interval

        if key_lst[pg.K_SPACE] and tmr % shot_interval == 0:
            nb = NeoBeam(bird, 5)
            dmk = nb.gen_beams()
            beams.add(dmk)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0

            if event.type == pg.KEYDOWN and event.key == pg.K_q:
                activated, skill_count = bird.skill(skill_count, fps=50)
                if activated:
                    skill_flashes.add(SkillFlash(life=12, alpha_hi=180, alpha_lo=0))

            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if score.value >= 20 and len(emps) == 0:
                    score.value -= 20
                    life_frames = max(1, int(0.05 * 50))
                    # 修正：screen引数はゲーム画面用のscreenを渡す
                    emps.add(EMP(emys, bombs, screen, life_frames))
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score >= 200:
                    score -= 200
                    gravities.add(Gravity(400))
                else:
                    pass
            if event.type == pg.KEYDOWN and event.key == pg.K_s:
                if score.value >= 50 and len(shields) == 0:
                    score.value -= 50
                    shields.add(shield(bird, 400))
        
        # 修正：背景描画などはゲーム画面用screenに対して行う
        screen.blit(bg_img, [0, 0])


        if not boss_spawned and tmr % 100 == 0:
            # 確認用：ボスが出やすいように調整する場合はここを調整
            level = tmr // 200 + 1 
            if level % 3 == 0:
                boss = BossEnemy(level)
                emys = pg.sprite.Group()
                emys.add(boss)
                boss_spawned = True
            else:
                emys.add(Enemy(level))

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                attack = random.randint(0,100)
                if attack<=20:
                    bombs.add(EnemyAttack(emy, bird).kotei(10, 5, 5, 60))
                elif attack<=60:
                    bombs.add(EnemyAttack(emy, bird).jiki(10, 5, 5, 60))
                elif attack==80:
                    bombs.add(EnemyAttack(emy, bird).kotei(20, 2, 3, 90))
                else:
                    bombs.add(EnemyAttack(emy, bird).jiki(10, 10, 1, 0))
                emy.state = "shoot"
                emy.ready_to_shoot = False
            if boss_spawned is True:
                if tmr % 300 == 0:
                    attack = random.randint(0,100)
                if attack is None or tmr % 300 >= 200:
                    pass 
                elif attack <= 25:
                    if tmr % 10 == 0:
                        bombs.add(EnemyAttack(emy, bird).kotei(20, 5, 1, 0))
                    if tmr % 50 == 0:
                        bombs.add(EnemyAttack(emy, bird).jiki(10, 5, 5, 60))
                elif attack <= 50:
                    if tmr % 8 == 0:
                        bombs.add(EnemyAttack(emy, bird).jiki(10, 10, 1, 0))
                    if tmr % 50 == 0:
                        bombs.add(EnemyAttack(emy, bird).kotei(10, 5, 3, 30))
                elif attack <= 75:
                    if tmr % 50 == 0:
                        bombs.add(EnemyAttack(emy, bird).kotei(10, 5, 5, 60))
                        bombs.add(EnemyAttack(emy, bird).kotei(10, 4, 4, 45))
                    if tmr % 50 == 25:
                        bombs.add(EnemyAttack(emy, bird).jiki(10, 5, 3, 30))
                elif attack <= 100:
                    if tmr % 10 ==0:
                        bombs.add(EnemyAttack(emy, bird).kotei(10, 5, 20, 360))
            

        hits = pg.sprite.groupcollide(emys, beams, False, True)

        for emy, hit_beams in hits.items():
            for beam in hit_beams:
                emy.hp -= beam.attack
            if emy.hp <= 0:
                exps.add(Explosion(emy, 100))
                emy.kill()
                score += 10
                bird.change_img(6, screen)

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if getattr(bird, "invincible", False):
                exps.add(Explosion(bomb, 50))
                continue
            else:
                lives -= 1
            if lives == 0:
                bird.change_img(8, screen)
                # ゲームオーバー時：現在の画面状態をルートスクリーンに反映させてから止まる
                root_screen.blit(screen, (0, 0))
                root_screen.blit(ui_screen, (GAME_WIDTH, 0))
                pg.display.update()
                time.sleep(2)
                return


        if len(gravities) > 0:
            for bomb in bombs:
                exps.add(Explosion(bomb, 50))
                bomb.kill()
                score.value += 1
            for emy in emys:
                exps.add(Explosion(emy, 100))
                emy.kill()
                score += 10

        
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
        
        # 修正：すべての描画（draw/update）はゲーム画面用screenに対して行う
        shields.draw(screen)
        shields.update()
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        for emy in emys:
            emy.draw_hp(screen)
            if emy.state == "stop" and tmr % emy.interval == 0:
                emy.state = "shoot"
        bombs.update()
        bombs.draw(screen)

        gravities.update()
        gravities.draw(screen)
        exps.update()
        exps.draw(screen)
        
        emps.update()
        emps.draw(screen)

        skill_flashes.update()
        skill_flashes.draw(screen)

        # 修正：UI描画関数には右画面用スクリーンを渡す
        draw_ui(ui_screen, score, lives, skill_count, ui_img)

        # 修正：最後にルートスクリーンへ2つの画面を貼り付けて更新
        root_screen.blit(screen, (0, 0))
        root_screen.blit(ui_screen, (GAME_WIDTH, 0))
        pg.display.update()
        
        tmr += 1

        if boss_spawned and all(not isinstance(e, BossEnemy) for e in emys):
            boss_spawned = False
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()