import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100
HEIGHT = 650
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
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
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
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

        # ================================
        # ここから skill 機能のための追加変数
        # ================================
        # 無敵状態かどうかを表すフラグ
        # True なら爆弾に当たってもゲームオーバーにならない（後で判定側で使用する）
        self.invincible = False

        # 無敵があと何フレーム残っているかを管理するタイマー
        # 例：50FPS想定のため 5秒 = 50*5 = 250フレーム
        self.invincible_timer = 0

        # 発射レート（何フレームに1回撃てるか）を管理する変数
        # 通常時は 10フレームに1回（= shot_interval が 10）
        # skill中は 5フレームに1回（= shot_interval が 5）
        self.shot_interval = 10

        # 「最後に撃ってから何フレーム経過したか」を管理するタイマー
        # 毎フレーム加算し、shot_interval以上になったら発射可能とする
        self.shot_timer = 0

        # スキル使用回数（skill_count）
        # スキル発動のたびに 1 減り、0 のときは発動できない
        # 初期値はここで自由に調整可能（例として3回に設定）
        self.skill_count = 3

    def skill(self, fps: int = 50) -> bool:
        """
        skill（スキル）を発動するためのメソッド（追加機能）
        要件：
        ・スキルを発動したら5秒の無敵時間
        ・shot_interval（発射レート）を通常10フレーム→5フレームにする
        ・スキルを使ったらskill_countを1減らす
        ・skill_countが0ならスキルを使えない（発動不可）

        引数 fps：
        ・ゲームのFPS（このプログラムはclock.tick(50)なので基本50）
        ・5秒を「fps*5フレーム」に換算するために使用する
        戻り値：
        ・発動できた場合 True
        ・skill_countが0で発動できない場合 False
        """
        # スキル回数が0以下なら発動不可（要件：0で使えない）
        if self.skill_count <= 0:
            return False

        # スキル回数を消費（要件：使ったら1減らす）
        self.skill_count -= 1

        # 無敵を付与（要件：5秒無敵）
        self.invincible = True
        self.invincible_timer = fps * 5  # 50FPSなら250フレーム

        # 発射レートを上げる（要件：通常10→5）
        self.shot_interval = 5

        return True

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
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

        # ==========================================
        # ここから skill（無敵・発射レート）管理の追加処理
        # ==========================================
        # 無敵状態のときは invincible_timer を毎フレーム減らす
        # 0以下になったら無敵解除し、発射レートも通常値に戻す
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                # 無敵終了
                self.invincible = False
                # 発射レートを通常に戻す（要件：スキル中だけ5フレーム）
                self.shot_interval = 10
                # ※shot_timerはそのままでも問題ないが、
                #   発射感覚を自然にするなら0に戻しても良い。
                #   今回は「元のコード構造を崩さない」ため、変更しない。

        # 発射レート制御用のタイマーを毎フレーム進める
        # 「撃つ」処理はmain側のキーイベントで行うが、
        # shot_timerの更新は鳥の状態管理としてBird側で扱う
        self.shot_timer += 1

        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0 = 0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle + angle0, 1.0)
        self.vx = math.cos(math.radians(angle + angle0))
        self.vy = -math.sin(math.radians(angle + angle0))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class NeoBeam(pg.sprite.Sprite):
    """
    弾幕に関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        弾幕を生成する
        引数1 bird：ビームを放つこうかとん
        引数2 num：一度に発射されるビームの数
        """
        super().__init__()
        self.bird = bird
        self.num = num
    
    def gen_beams(self):
        """
        ビームを生成する
        射撃角度を指定してBeamクラスを呼び出す
        """
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

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)
        self.state = "down"
        self.interval = random.randint(50, 300)

    def update(self):
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 10000
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP(pg.sprite.Sprite):
    """
    発動時に存在する敵機と爆弾を無効化するクラス
    発動した際、画面内のemyとbombを無効化する。
    画面全体に透過黄色矩形を表示
    """
    def __init__(self, emy_group: pg.sprite.Group, bomb_group: pg.sprite.Group, screen: pg.Surface, life_frames: int = 3):
        super().__init__()
        surf = pg.Surface((WIDTH, HEIGHT), flags=pg.SRCALPHA)
        surf.fill((255, 255, 0, 100))  # 透過黄色
        self.image = surf
        self.rect = self.image.get_rect()
        self.life = life_frames
        
        # EMP効果：敵と爆弾を無効化
        for emy in list(emy_group):
            emy.interval = math.inf   # 爆弾を落とさなくする
            emy.disabled_by_emp = True
            emy.image = pg.transform.laplacian(emy.image) #見た目ラプラシアンフィルタ
        for bomb in list(bomb_group):
            bomb.speed /= 2           # 速度半減
            bomb.inactive = True      # 起爆無効化

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


class shield(pg.sprite.Sprite):
    """
    スコアをコストに向いている方向へ防御癖を展開するクラス
    コスト：50
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
    ※写真の手順どおりに実装した版
    """
    def __init__(self, life: int):
        super().__init__()
        self.life = life
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image,(0, 0, 0),(0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()


class SkillFlash(pg.sprite.Sprite):
    """
    スキル発動時に「画面が一瞬チカチカする」ことを表現するクラス（追加機能）

    目的：
    ・スキルを使用したときに、プレイヤーが「今スキルが発動した」と分かるようにする
    ・画面全体に半透明の白い矩形を重ね、数フレームだけ明滅（チカチカ）させる

    実装の考え方：
    ・pygameでは「画面そのものを点滅」させるよりも、
      画面に透明度付きのSurfaceを重ねて表示する方が簡単で安全
    ・Spriteとして作ることで、既存のグループ描画処理に自然に組み込める
    """
    def __init__(self, life: int = 12, alpha_hi: int = 180, alpha_lo: int = 0):
        """
        引数1 life：
        ・このフラッシュエフェクトが何フレーム存在するか
        ・短いほど「一瞬チカッ」長いほど「しっかりチカチカ」する
        ・例：12フレーム（50FPSなら約0.24秒）程度が “一瞬感” が出やすい
        引数2 alpha_hi：
        ・明るい側（チカッと光る側）の透明度（0～255）
        引数3 alpha_lo：
        ・暗い側（消える側）の透明度（0～255）
        """
        super().__init__()

        # 画面全体を覆うSurfaceを作る（透過を使うのでSRCALPHAを指定）
        self.image = pg.Surface((WIDTH, HEIGHT), flags=pg.SRCALPHA)

        # 初期状態は白く光らせる（白い半透明の膜が画面を覆うイメージ）
        # ここではRGB=(255,255,255)にし、alphaで透過度を制御する
        self.image.fill((255, 255, 255, alpha_hi))

        # 画面全体を覆うのでRectも画面サイズに合わせる
        self.rect = self.image.get_rect()

        # 残り寿命（フレーム数）
        self.life = life

        # 明滅に使う透明度を保持
        self.alpha_hi = alpha_hi
        self.alpha_lo = alpha_lo

        # 何フレームごとに切り替えるか（1なら毎フレームで激しくチカチカ）
        # ここでは2にして「2フレームごとにON/OFF」する（見た目が安定しやすい）
        self.toggle_interval = 2

    def update(self):
        """
        毎フレーム呼ばれて、エフェクトの寿命と明滅を制御する
        """
        # 寿命を減らす
        self.life -= 1

        # lifeが0以下になったらエフェクトを消す（Groupからも消える）
        if self.life < 0:
            self.kill()
            return

        # 明滅（チカチカ）処理：
        # ・toggle_intervalごとに透明度を切り替える
        # ・偶数/奇数フレームで alpha_hi / alpha_lo に切り替えることで点滅させる
        if (self.life // self.toggle_interval) % 2 == 0:
            self.image.fill((255, 255, 255, self.alpha_hi))
        else:
            self.image.fill((255, 255, 255, self.alpha_lo))


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emps = pg.sprite.Group()

    gravities = pg.sprite.Group()
    shields = pg.sprite.Group()

    # ============================================================
    # skill発動エフェクト（画面フラッシュ）用のグループ（追加機能）
    # ============================================================
    # 画面全体に重ねて描画するSpriteを入れておく
    # スキル発動時にSkillFlashを生成してここに追加し、毎フレームupdate/drawする
    skill_flashes = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0

            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                # ============================================================
                # 発射レート（shot_interval）による発射制御（追加機能）
                # ============================================================
                # bird.shot_timer はBird.update内で毎フレーム加算されている
                # ここでは「shot_timerがshot_interval以上なら撃てる」と判定している
                #
                # 例：
                # ・通常：shot_interval = 10 → 10フレームに1回
                # ・skill中：shot_interval = 5 → 5フレームに1回（発射レート上昇）
                #
                # 条件を満たさない場合は発射しない（連打しても弾が出ない）
                if bird.shot_timer >= bird.shot_interval:
                    # 発射したのでタイマーをリセット
                    bird.shot_timer = 0

                    # 元のコードの構造（Shift弾幕 / 通常単発）を維持する
                    if pg.key.get_pressed()[pg.K_LSHIFT]:
                        nb = NeoBeam(bird, 5)
                        dmk = nb.gen_beams()
                        beams.add(dmk)
                    else:
                        beams.add(Beam(bird))
                    beams.add(Beam(bird))

            # ============================================================
            # skill 発動キー（追加機能）
            # ============================================================
            # ここでは「Qキー」でスキルを発動する設計にしている
            # ・skill_count が 0 の場合は Bird.skill() が False を返し、発動しない
            # ・発動した場合は
            #   - 5秒無敵（invincible=True, invincible_timer=250フレーム）
            #   - shot_interval を 10 → 5 に変更（発射レート上昇）
            #   - skill_count を 1 減らす（回数消費）
            #
            # 追加要件：
            # ・スキルを使用した時に使ったとわかるようなエフェクト
            # ・画面が一瞬チカチカする
            #
            # → Bird.skill() が True（発動成功）を返したときだけ
            #    SkillFlash を生成して skill_flashes に追加し、画面を明滅させる
            if event.type == pg.KEYDOWN and event.key == pg.K_q:
                if bird.skill(fps=50):
                    # スキルが「成功して発動した」場合のみフラッシュを出す
                    # life=12：短時間でチカチカする
                    # alpha_hi=180：強めに光る
                    # alpha_lo=0：消える（完全透明）
                    skill_flashes.add(SkillFlash(life=12, alpha_hi=180, alpha_lo=0))

            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if score.value >= 20 and len(emps) == 0:
                    score.value -= 20
                    life_frames = max(1, int(0.05 * 50))
                    emps.add(EMP(emys, bombs, screen, life_frames))
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.value >=200:
                score.value -= 200
                gravities.add(Gravity(400))
            if event.type == pg.KEYDOWN and event.key == pg.K_s:
                if score.value >= 50 and len(shields) == 0:
                    score.value -= 50
                    shields.add(shield(bird, 400))
        screen.blit(bg_img, [0, 0])

        if tmr % 200 == 0:
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            # ============================================================
            # skillの無敵判定（追加機能）
            # ============================================================
            # bird.invincible == True の間は爆弾に当たってもゲームオーバーにしない
            #
            # ここで True の場合：
            # ・衝突した爆弾は spritecollide(..., True) によって消えている
            # ・視覚的に分かりやすいように爆発エフェクトだけ追加する
            # ・スコア加算は要件にないので行わない（挙動を余計に変えないため）
            if getattr(bird, "invincible", False):
                exps.add(Explosion(bomb, 50))
                continue

            # EMPで無効化された爆弾ならゲームオーバーにしない
            if getattr(bomb, "inactive", False):
                continue

            # 通常爆弾の場合：ゲームオーバー
            bird.change_img(8, screen)
            score.update(screen)
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
                score.value += 10

        
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
        
        shields.draw(screen)
        shields.update()
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)

        gravities.update()
        gravities.draw(screen)
        exps.update()
        exps.draw(screen)
        
        emps.update()
        emps.draw(screen)

        # ============================================================
        # skill発動エフェクト（画面フラッシュ）の更新・描画（追加機能）
        # ============================================================
        # 「画面がチカチカする」演出は、背景やキャラの上に重ねる必要がある。
        # そのため描画順としては
        #   1) 背景・キャラ・弾・爆発など全部描く
        #   2) 最後にフラッシュを重ねる
        # が自然（フラッシュが前面に出る）
        skill_flashes.update()
        skill_flashes.draw(screen)

        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
