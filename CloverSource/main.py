# WARNING: SPAGHETTI! PROCEED AT YOUR OWN RISK

import os
# import random
import pygame
import json
import sys
import ctypes
import shutil
import webbrowser

# inicjalizacja
pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)

WIDTH = 1280
HEIGHT = 768

clock = pygame.time.Clock()
transparent = (0, 0, 0, 0)

FPS = 30

MAX_TEXT_LENGTH = 12 # Najdłuższe hasło jakie można wpisać

# Koordynaty lewej i prawej strony
L_P_OFFSET = 237
R_P_OFFSET = 704

# Odnowienie inputów
CD = 1

# Dopuszczalne wydażenia
EVENTS = (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)

NUMPAD = (pygame.K_KP0, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4, pygame.K_KP5, pygame.K_KP6, pygame.K_KP7, pygame.K_KP8, pygame.K_KP9)

try: USERNAME = str(os.getlogin()) # Nazwa gracza
except: USERNAME = 'Joe'

# obiekt z którym nie można wejść w interakcję
class StaticObject:
    def __init__(self, x, y, sprite_path: str, scaling: float = None):
        if scaling is None: scaling = SCALE
        self.scaling = scaling
        self.x = int(x * scaling)
        self.y = int(y * scaling)

        self.sprite_path = sprite_path
        self.current_sprite_path = sprite_path
        self.sprite = pygame.image.load(sprite_path).convert_alpha()
        if scaling != 1: self.resize(scaling)

        self.created = True  # sprawdzenie czy obiekt jest stworzony na ekranie przed możliwością interakcji z nim
        self.fade_in_enabler = False
        self.alpha = 245  # Przezroczystość obrazu

    def draw(self):
        if self.created:
            self.sprite.set_alpha(self.alpha)
            self.draw_always()

    def draw_always(self):
        screen.blit(self.sprite, (self.x, self.y))

    def draw_with_fade_in(self, speed: int):
        if self.fade_in_enabler:
            if self.alpha < 260:  # Trzeba ustawić alfę na 0
                self.sprite.set_alpha(self.alpha)
                self.alpha += speed
            else:
                self.alpha = 245
                self.fade_in_enabler = False
        self.draw()

    def resize(self, mul: float):
        a, b = self.sprite.get_size()
        a, b = int(a * mul), int(b * mul)
        self.sprite = pygame.transform.scale(self.sprite, (a, b))

    def remove(self):
        if self.created:
            self.sprite.set_alpha(0)
            self.created = False

    def recreate(self):
        if not self.created:
            self.sprite.set_alpha(300)
            self.created = True

    def switch_sprite(self, sprite_path: str):
        self.current_sprite_path = sprite_path
        self.sprite = pygame.image.load(sprite_path).convert_alpha()
        if self.scaling != 1: self.resize(self.scaling)

    def move(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

    def set_position(self, x, y):
        self.x = x
        self.y = y


# obiekt z którym można wejść w interakcję

class ActiveObject(StaticObject):
    def __init__(self, x, y, sprite_path: str, hbox_coords: list = None, scaling: float = None):
        if scaling is None: scaling = SCALE
        super().__init__(x, y, sprite_path, scaling)

        # Opcjonalne podanie kolejno koordynatów lewego-górnego, oraz prawego-dolnego punktu hitboxa
        # Jeśli nie są podane wartości, hitbox będzie taki sam jak obrazek

        if hbox_coords is None:
            hbox_coords = [self.x, self.y, self.sprite.get_width(), self.sprite.get_height()]
        else:
            # Modyfikacja zamieniająca koordynaty 2go punktu na szerokość i wysokość dla Rect
            hbox_coords[2] -= hbox_coords[0]
            hbox_coords[3] -= hbox_coords[1]
            for i, coord in enumerate(hbox_coords):
                hbox_coords[i] = int(coord * scaling)

        self.hitbox = pygame.Rect(hbox_coords)
        self.hbox_coords = hbox_coords
        self.hbox_distance = [hbox_coords[0] - self.x, hbox_coords[1] - self.y]

    def move(self, dx: float, dy: float):
        super().move(dx, dy)
        self.hitbox = pygame.Rect.move(self.hitbox, dx, dy)

    def set_position(self, x, y):
        super().set_position(x, y)
        self.hbox_coords[0] = x + self.hbox_distance[0]
        self.hbox_coords[1] = y + self.hbox_distance[1]
        self.hitbox.update(self.hbox_coords)

    def scale_set_pos(self, x, y, scaling=None):
        if scaling is None: scaling = SCALE
        x = int(x * scaling)
        y = int(y * scaling)
        self.set_position(x, y)

    def cursor_overlap(self):
        if self.created:
            x, y = pygame.mouse.get_pos()
            if self.hitbox.collidepoint(x, y):
                return True

    def left_clicked(self, event):
        global cooldown
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and cooldown == 0:
            if self.cursor_overlap():
                cooldown = CD
                return True


class Checkbox(ActiveObject):
    def __init__(self, x, y, sprite_path: str, checked_sprite_path: str, hbox_coords: list = None):
        super().__init__(x, y, sprite_path, hbox_coords)
        self.checked = False
        self.checked_sprite_path = checked_sprite_path

    def checkbox_check(self, event):
        if self.left_clicked(event):
            hover_sound.play()
            self.checked = not self.checked

    def draw_checkbox(self):
        self.switch_sprite(self.checked_sprite_path) if self.checked else self.switch_sprite(self.sprite_path)
        super().draw()


class Button(ActiveObject):
    def __init__(self, x, y, sprite_path: str, hovered_sprite_path: str = None, hbox_coords: list = None):
        super().__init__(x, y, sprite_path, hbox_coords)
        self.hovered_sprite_path = hovered_sprite_path
        self.on_button = False

    def draw_button(self):
        if not self.on_button and self.cursor_overlap():
            self.on_button = True
            hover_sound.play()
        elif not self.cursor_overlap():
            self.on_button = False
        self.switch_sprite(self.hovered_sprite_path) if self.cursor_overlap() else self.switch_sprite(self.sprite_path)
        super().draw()


class AnimButton(ActiveObject): # anim = 0 żeby trzeba było zjechać kursorem
    def __init__(self, x, y, sprite_path: str, anim_sprite_path: str = None, hbox_coords: list = None, anim=10):
        super().__init__(x, y, sprite_path, hbox_coords)
        self.anim_sprite_path = anim_sprite_path
        self.play_anim = False
        self.ANIM = anim
        self.anim_counter = anim
        self.hold_timer = 0 # Używane tylko kiedy anim == 0

    def left_clicked(self, event):
        if super().left_clicked(event):
            self.hold_timer = 0
            self.play_anim = True
            self.anim_counter = self.ANIM
            return True

    def click_released(self, event): # tylko dla ANIM == 0
        if self.ANIM == 0 and self.play_anim:
            if (event.type == pygame.MOUSEBUTTONUP and event.button == 1) or not self.cursor_overlap():
                self.play_anim = False
                self.switch_sprite(self.sprite_path)
                return True

    def draw_button(self):
        if self.ANIM > 0:
            if self.play_anim and self.anim_counter == self.ANIM:
                self.switch_sprite(self.anim_sprite_path)
            if self.play_anim and self.anim_counter > 0:
                self.anim_counter -= 1
            elif self.play_anim and self.anim_counter <= 0:
                self.switch_sprite(self.sprite_path)
                self.play_anim = False
                self.anim_counter = self.ANIM

        elif self.ANIM == 0 and self.play_anim:
            if self.hold_timer == 0:
                self.switch_sprite(self.anim_sprite_path)
            self.hold_timer += 1

        self.draw()


class MovableObject(ActiveObject):
    speed = 49

    def __init__(self, x, y, sprite_path: str, boundaries: list = None, hbox_coords: list = None, static: bool = False):
        super().__init__(x, y, 'data/graphics/active_images/' + sprite_path + '.png', hbox_coords)
        self.left_click_held = False
        self.mouse_diff_x = 0
        self.mouse_diff_y = 0
        if boundaries is None: boundaries = [243, 75, 1180, 690]
        self.boundaries = [int(el * SCALE) for el in boundaries]
        self.active_points = []
        self.held_obj_dir = None
        self.static = static
        self.blocked = {'left': False, 'right': False, 'up': False, 'down': False}

    def block_with_boundaries(self, bounds):
        if self.x <= bounds[0]: self.set_position(bounds[0], self.y)
        if self.y <= bounds[1]: self.set_position(self.x, bounds[1])
        if self.x + self.sprite.get_width() >= bounds[2]: self.set_position(bounds[2] - self.sprite.get_width(), self.y)
        if self.y + self.sprite.get_height() >= bounds[3]: self.set_position(self.x, bounds[3] - self.sprite.get_height())

    def mouse_mech_event(self, event):
        if self.created:
            if self.left_clicked(event):
                x, y = pygame.mouse.get_pos()
                self.left_click_held = True
                self.mouse_diff_x = x - self.x
                self.mouse_diff_y = y - self.y
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.left_click_held = False

    def mouse_mech(self):
        if self.created:
            if self.left_click_held:
                x, y = pygame.mouse.get_pos()
                x_diff, y_diff = self.x - x + self.mouse_diff_x, self.y - y + self.mouse_diff_y
                x_change = min(MovableObject.speed, x_diff) if x_diff > 0 else max(-MovableObject.speed, x_diff)
                y_change = min(MovableObject.speed, y_diff) if y_diff > 0 else max(-MovableObject.speed, y_diff)
                if (self.blocked['left'] and x_change > 0) or (self.blocked['right'] and x_change < 0):
                    x_change = 0
                if (self.blocked['up'] and y_change > 0) or (self.blocked['down'] and y_change < 0):
                    y_change = 0
                self.set_position(self.x - x_change, self.y - y_change)
                self.block_with_boundaries(self.boundaries)

    def point_overlap(self, coords_list: list):
        if SCALE != 1: coords_list = [(int(el[0] * SCALE), int(el[1] * SCALE)) for el in coords_list]
        if self.created:
            for coords in coords_list:
                if self.hitbox.collidepoint(coords):
                    return True


def block_movables(movable_list: list[MovableObject]):
    for mov1 in movable_list:
        if mov1.left_click_held:
            mov1.blocked = {'left': False, 'right': False, 'up': False, 'down': False}
            for mov2 in movable_list:
                if mov2 != mov1:
                    left = mov1.x + mov1.sprite.get_width() <= mov2.x
                    right = mov1.x >= mov2.x + mov2.sprite.get_width()
                    up = mov1.y + mov1.sprite.get_height() <= mov2.y
                    down = mov1.y >= mov2.y + mov2.sprite.get_height()
                    if left: mov2.held_obj_dir = 'left'
                    elif right: mov2.held_obj_dir = 'right'
                    elif up: mov2.held_obj_dir = 'up'
                    elif down: mov2.held_obj_dir = 'down'
                    if right and (up or down): mov2.held_obj_dir = 'right_l'
                    elif left and (up or down): mov2.held_obj_dir = 'left_l'

                    if mov2.held_obj_dir in ['left', 'left_l'] and mov1.x + mov1.sprite.get_width() >= mov2.x:
                        mov1.set_position(mov2.x - mov1.sprite.get_width(), mov1.y)
                        if mov2.held_obj_dir == 'left': mov1.blocked['right'] = True
                    if mov2.held_obj_dir in ['right', 'right_l'] and mov1.x <= mov2.x + mov2.sprite.get_width():
                        mov1.set_position(mov2.x + mov2.sprite.get_width(), mov1.y)
                        if mov2.held_obj_dir == 'right': mov1.blocked['left'] = True
                    if mov2.held_obj_dir == 'up' and mov1.y + mov1.sprite.get_height() >= mov2.y:
                        mov1.set_position(mov1.x, mov2.y - mov1.sprite.get_height())
                        mov1.blocked['down'] = True
                    if mov2.held_obj_dir == 'down' and mov1.y <= mov2.y + mov2.sprite.get_height():
                        mov1.set_position(mov1.x, mov2.y + mov2.sprite.get_height())
                        mov1.blocked['up'] = True


class ObjectList:
    def __init__(self, obj_type: str, n, x, y, sprite_path_1: str, sprite_path_2: str, dx, dy, dependent: bool = False, counter_start: int = 0, anim=10):
        self.lst = []
        self.len = n
        self.obj_type = obj_type
        self.dependent = dependent
        for i in range(n):
            if obj_type == 'Button':
                self.lst.append(Button(x, y, sprite_path_1, sprite_path_2))
            elif obj_type == 'AnimButton':
                self.lst.append(AnimButton(x, y, sprite_path_1, sprite_path_2, anim=anim))
            else:
                self.lst.append(Checkbox(x, y, sprite_path_1, sprite_path_2))
            x += dx
            y += dy
        if dependent:
            self.lst[0].checked = True
        self.counter = counter_start

    def __getitem__(self, key):
        return self.lst[key]

    def draw(self):
        for obj in self:
            obj.draw_button() if self.obj_type in ['Button', 'AnimButton'] else obj.draw_checkbox()

    def checkboxes_check(self, event):
        if self.obj_type == 'Checkbox':
            for obj in self:
                if (self.dependent and obj.checked == False) or not self.dependent:
                    obj.checkbox_check(event)
                if self.dependent:
                    for other_obj in self:
                        if other_obj != obj and obj.checked:
                            other_obj.checked = False

    def counter_mech(self):
        if self.counter > self.len:
            self.counter = self.len
        for i in range(self.len):
            self[i].checked = True if i < self.counter else False


def clip(surf,x,y,x_size,y_size):
    handle_surf = surf.copy()
    clipR = pygame.Rect(x,y,x_size,y_size)
    handle_surf.set_clip(clipR)
    image = surf.subsurface(handle_surf.get_clip())
    return image.copy()


# Renderowanie czcionek


class Font:
    def __init__(self, path):
        self.spacing = 0
        self.character_order = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','.','-',',',':',';','+','/','!','?','0','1','2','3','4','5','6','7','8','9','\'','"','(',')','[',']','=','*','<','>']
        font_img = pygame.image.load(path).convert()
        current_char_width = 0
        self.characters = {}
        character_count = 0
        for x in range(font_img.get_width()):
            c = font_img.get_at((x, 0))
            if c[0] == 127:
                char_img = clip(font_img, x - current_char_width, 0, current_char_width, font_img.get_height())
                char_img.set_colorkey((0, 255, 0))
                ch = char_img.copy()
                a, b = ch.get_size()
                a, b = int(a * SCALE), int(b * SCALE)
                ch = pygame.transform.scale(ch, (a, b))
                self.characters[self.character_order[character_count]] = ch
                character_count += 1
                current_char_width = 0
            else:
                current_char_width += 1
        self.space_width = self.characters['A'].get_width()

    def render(self, surf, text, loc):
        x_offset = 0
        for char in text:
            if char != ' ':
                try: rend_char = self.characters[char]
                except KeyError: rend_char = self.characters['?']
                surf.blit(rend_char, (loc[0] + x_offset, loc[1]))
                x_offset += rend_char.get_width() + self.spacing
            else:
                x_offset += self.space_width + self.spacing


def set_mouse_speed(speed: int = 10):
    ctypes.windll.user32.SystemParametersInfoA(113, 0, speed, 0)

# Funkcja wyświetlająca tekst

def display_text(x: float, y: float, text_to_d: list[str], color: str = 'black', distance_between_lines: int = 70):
    x = int(x * SCALE)
    y = int(y * SCALE)
    distance_between_lines = int(distance_between_lines * SCALE)
    for line in text_to_d:
        if line == '>user': line = USERNAME
        if color == 'black': black_font.render(screen, line, (x, y))
        elif color == 'gray': gray_font.render(screen, line, (x, y))
        else: white_font.render(screen, line, (x, y))
        y += distance_between_lines


# Aktualizacja wyświetlacza

def screen_update(rect_coords: list = None):
    clock.tick(FPS)
    if rect_coords is None:
        pygame.display.update()
    else:
        pygame.display.update(pygame.Rect(rect_coords))


# Obiekty i zmienne globalne:

# Do zapisyywania gry
progress_data: dict
preferences_data: dict

try:
    with open('data/preferences.json') as preferences_file:
        preferences_data = json.load(preferences_file)
        preferences_file.close()
except:
    preferences_data = {'disable_fade': False, 'disable_music': True, 'small_window': False, 'which_ambience': 1}

# Skalowanie obrazu
SCALE = 2 / 3 if preferences_data['small_window'] else 1

FINAL_LEVEL = 41

# Ekran
screen = pygame.display.set_mode((int(WIDTH * SCALE), int(HEIGHT * SCALE)))

# Numer poziomu w którym aktualnie znajduje się gracz,
current_level: int = 1

# Ostatni poziom do którego gracz doszedł (nie licząc menu)
max_level: int = 0

# Na której cutscence jest gracz
cutscene = 0
cscreen = StaticObject(0, 0, 'data/graphics/transparent.png')  # Obrazek do cutscenki
ctext = [""]
FINAL_CUTSCENE = 9

# Progress sekretu
sec_prog: int = 0 # 1 - zerowy poziom zrobiony, 2 - drzwi otworzone
sec_max_level: int = 0
sec_cutscene: int = 100

# Zanikanie ekranu
fade_alpha: int = 0
fade = pygame.Surface((WIDTH, HEIGHT))
fade.fill((0, 0, 0))

# Czy gracz był kiedykolwiek na najpóźniejszym poziomie?
was_on_max_level, was_on_sec_max_level = True, True

# Przejście między poziomami
transition: bool = False

# Jeśli to jest prawdziwe, to gracz nigdy nie włączał nowej gry
first_new_game = False

# Tło
notebook = StaticObject(0, 0, 'data/graphics/notebook.png')

# Muzyka w tle dla poziomów
pygame.mixer.music.load('data/audio/music/ambience_' + str(preferences_data['which_ambience']) + '.ogg')
MUSIC_VOL = 0.2
# pygame.mixer.music.load('data/audio/music/Illuminate.wav')

# Tekst wpisywany przez gracza do przejścia poziomu
input_text: str = ''

# Tekst wyświetlany na ekranie
text_to_display = [[], []]
# Hasło
passwords = ''

# Informacja w którym podlevelu jest gracz
blind_way = None  # None - oryginalny ekran

# Progress przejścia każdego poziomu
progress: int = 0

# Informacja zwrotna po przejściu każdego poziomu
state = 0

cooldown = 0  # Żeby się nie dało spamować
# Zmienne globalne do wszelakich użyć
global_var_reset: int = 0
global_var: int = 0

# Czcionka
black_font = Font('data/graphics/fonts/black.png')
white_font = Font('data/graphics/fonts/white.png')
gray_font = Font('data/graphics/fonts/gray.png')

# Ikona okna
icon = pygame.image.load('data/icon.png')
pygame.display.set_icon(icon)

# Ustawienie muzyki
pygame.mixer.music.set_volume(0) if preferences_data['disable_music'] else pygame.mixer.music.set_volume(MUSIC_VOL)
pygame.mixer.music.play(-1)


# Globalne obiekty
# main_title = StaticObject(0, 0, 'data/graphics/menus/main_title.png')
clover_indicator = ActiveObject(1085, 615, 'data/graphics/clover_indicator.png')
clover_indicator_red = ActiveObject(1085, 615, 'data/graphics/clover_indicator_red.png')
clover_animation_var: int = 0
pass_line = StaticObject(765, 665, 'data/graphics/password_line.png')
hint_button = ActiveObject(34, 630, 'data/graphics/hint_button.png')
back_to_menu_arrow = ActiveObject(10, 708, 'data/graphics/back_to_menu_arrow.png')
sketch_left = StaticObject(L_P_OFFSET, 0, 'data/graphics/transparent.png')
sketch_right = StaticObject(R_P_OFFSET, 0, 'data/graphics/transparent.png')
# question_mark = StaticObject(80, 80, 'data/graphics/question_mark.png')

# Dźwięki
# page_flips_long = [pygame.mixer.Sound('data/audio/sounds/pflip_A.wav'), pygame.mixer.Sound('data/audio/sounds/pflip_B.wav'),
#                    pygame.mixer.Sound('data/audio/sounds/pflip_C.wav'), pygame.mixer.Sound('data/audio/sounds/pflip_B.wav')]
page_flip_long = pygame.mixer.Sound('data/audio/sounds/pflip_B.wav')
page_flip_long.set_volume(0.4)
clover_indicator_sound = pygame.mixer.Sound('data/audio/sounds/clover_sound.wav')
clover_indicator_sound.set_volume(0.5)
short_sound = pygame.mixer.Sound('data/audio/sounds/short_sound.wav')
short_sound.set_volume(0.5)
hover_sound = pygame.mixer.Sound('data/audio/sounds/small_sound.wav')
hover_sound.set_volume(0.02)
click_sound = pygame.mixer.Sound('data/audio/sounds/click_sound.wav')
click_sound.set_volume(0.1)
new_game_sound = pygame.mixer.Sound('data/audio/sounds/new_game_sound.wav')
new_game_sound.set_volume(0.5)
door_sound = pygame.mixer.Sound('data/audio/sounds/door.wav')
door_sound.set_volume(0.2)


# Funkcja zapisująca grę
def save_and_exit():
    global progress_data
    progress_data = {'CurrentLevel': current_level, 'MaxLevel': max_level, 'Cutscene': cutscene, 'SecProg': sec_prog, 'SecMaxLevel': sec_max_level, 'SecCutscene': sec_cutscene}

    with open('data/save.json', 'w') as save_f:
        json.dump(progress_data, save_f)
    with open('data/preferences.json', 'w') as preferences_f:
        json.dump(preferences_data, preferences_f)

    pygame.quit()
    sys.exit()


# Specjalne obiekty poszczególnych poziomów
class SO:
    the_key = MovableObject(335, 405, 'the_key', None)

    n_back_to_start_fetus_level = 9
    bw_bts_fetus = ">level_fetus"
    n_back_to_start_second = 36
    bw_bts_second = ">level_cosmos"

    n_letters_in_grid = 34

    n_arrows_level = 8
    counter_arrows = 0
    order_arrows = [-1, -1, -1, 1, -1, -1, 1, 1, 1, 1, -1, 1]
    bw_arrows = ">level_arrows"

    n_door_level = 16
    new_menu_cutscene = 4

    n_cards_level = 17

    n_shiny_a = 18
    shiny_hand_level = MovableObject(900, 500, 'shiny_right', None, [912, 515, 1011, 621])

    n_level_repeat_sound = 33

    sketch_to_copy = 'data/graphics/static_images/4_chess_right.png'

    n_level_beyond = 42


def reset_the_key():
    SO.the_key.left_click_held = False
    SO.the_key.scale_set_pos(335, 405)  # Resetowanie położenia


def reset_special_objects():
    SO.shiny_hand_level = MovableObject(900, 500, 'shiny_right', None, [912, 515, 1011, 621])
    SO.counter_arrows = 0


def start_end_fade(speed_fadein=10, speed_fadeout=10):
    global fade_alpha
    global transition
    global state

    # Przechodzenie do nowego poziomu
    if transition:
        pygame.time.delay(10)
        fade.set_alpha(fade_alpha)
        screen.blit(fade, (0, 0))

        # Zanikanie ekranu na końcu poziomu
        if progress == 1:
            fade_alpha += speed_fadeout

        # Pojawianie się ekranu na początku poziomu
        elif progress == 0:
            fade_alpha -= speed_fadein

    if fade_alpha > 260 and progress == 1:
        state = 1  # Przejście do następnego poziomu po poczekaniu
    if fade_alpha < 0:
        transition = False
        fade_alpha = 0


def sketch_set(ls_s_end: str = ">0", rs_s_end: str = ">0"):
    if ls_s_end != ">0":
        if ls_s_end == "":
            sketch_left.switch_sprite('data/graphics/transparent.png')
        else:
            sketch_left.switch_sprite('data/graphics/static_images/' + ls_s_end + '.png')

    if rs_s_end != ">0":
        if rs_s_end == "":
            sketch_right.switch_sprite('data/graphics/transparent.png')
        else:
            sketch_right.switch_sprite('data/graphics/static_images/' + rs_s_end + '.png')


def level_set(level_data):
    global text_to_display
    if level_data[0] != ">0":
        text_to_display[0] = level_data[0]
    if level_data[1] != ">0":
        text_to_display[1] = level_data[1]
    if level_data[2] == "":
        sketch_set("", "0_question_mark")
    else:
        sketch_set(level_data[2][0], level_data[2][1])


def level_reset():
    sketch_left.recreate()
    sketch_right.recreate()
    level_set(data_text_pictures[str(current_level)])


def spawn_gf(f_name: str, dire='data/gfspawns/'):
    try: shutil.copy(dire + f_name, f_name)
    except PermissionError: save_and_exit()


def level_start():
    global passwords

    # Levele bez podpowiedzi
    dbw = data_blind_ways[str(current_level)]
    hint_button.remove() if dbw == ">0" or ">hint" not in dbw.keys() else hint_button.recreate()

    # Ustawianie hasła tytułu i plików gry
    dptg = data_pass_title_gfspawns[str(current_level)]
    passwords = dptg["pass"]
    title = dptg["title"]
    # question_mark.recreate() if dptg["qm"] else question_mark.remove()
    pygame.display.set_caption(title) if title != "" else pygame.display.set_caption("Clover")
    if (current_level == max_level or current_level == sec_max_level) and "gfspawns" in dptg.keys():
        for file_name in dptg["gfspawns"]:
            if not os.path.exists(file_name):
                spawn_gf(file_name)
    level_reset()


def level_end():
    global current_level

    # Usuwanie redundantnych plików
    dptg = data_pass_title_gfspawns[str(current_level)]
    if (max_level > current_level or sec_max_level > current_level) and "gfspawns" in dptg.keys():
        for file_name in dptg["gfspawns"]:
            if os.path.exists(file_name):
                try: os.remove(file_name)
                except PermissionError: save_and_exit()


def level_draw_bottom():
    global progress
    global max_level, sec_max_level
    global was_on_max_level, was_on_sec_max_level
    global clover_animation_var
    global blind_way
    global sec_prog

    screen.fill((0, 0, 0))
    notebook.draw_always()

    if current_level == max_level or (current_level == sec_max_level and current_level != 0):
        if progress == 1:  # Zapisywanie postępu
            if current_level < 100:
                max_level += 1
                was_on_max_level = False if not preferences_data['disable_fade'] else True
            else:
                sec_max_level += 1
                was_on_sec_max_level = False if not preferences_data['disable_fade'] else True

            # Pojawienie się znacznika
            clover_indicator.alpha = 0
            clover_indicator.fade_in_enabler = True
            clover_indicator_red.alpha = 0
            clover_indicator_red.fade_in_enabler = True
            clover_indicator_sound.play()

            # To jest po to żeby przejście działo się tylko jeden raz (plus wyłączanie przejść w opcjach powyżej)
        elif progress == 0:
            was_on_max_level, was_on_sec_max_level = True, True

    if sec_prog == 0 and current_level == 0 and progress == 1: # Znacznik w zerowym poziomie
        sec_prog = 1
        clover_indicator.alpha = 0
        clover_indicator.fade_in_enabler = True
        clover_indicator_red.alpha = 0
        clover_indicator_red.fade_in_enabler = True
        clover_indicator_sound.play()

    if current_level != 0 or sec_prog > 0: # Wyjątek dla zerowego poziomu
        if current_level < max_level or (100 <= current_level < sec_max_level):  # Jeśli przeszedłeś poziom to jest zrobiony
            progress = 1
    if (100 > current_level > max_level) or (current_level > sec_max_level >= 100):  # Zabezpieczenie
        max_level = current_level

    # Zmiana danych w przypadku subpoziomu
    if blind_way is not None and blind_way != '>hintM' and (blind_way != 'clover' or max_level >= FINAL_LEVEL): # DO OSTATNI POZIOM
        level_set(data_blind_ways[str(current_level)][blind_way])
        if blind_way == '>hint' or (current_level == SO.n_level_beyond and blind_way is not None): blind_way = '>hintM'
        else: blind_way = None

    # Wyświetlanie linijek tekstu
    display_text(255, 90, text_to_display[0])
    display_text(730, 90, text_to_display[1])

    # Wyświetlanie szkiców
    sketch_left.draw_always()
    sketch_right.draw_always()

    # Wyświetlanie tekstu gracza i numeru strony
    if passwords != ">0":
        pass_line.draw()
    display_text(780, 620, [input_text])
    if current_level < FINAL_LEVEL or current_level >= 100: display_text(265, 655, [str(current_level)]) # TODO: Usuń wyświetlanie po 100

    # Wyświetlanie znaczka ukończenia poziomu (kod poniżej zawiera animację pojawiania się znacznika)
    if progress == 1:
        if clover_indicator.fade_in_enabler:
            clover_indicator_red.draw_with_fade_in(20)
            if clover_indicator.alpha == 0:
                clover_animation_var += 1
        if clover_animation_var > 20 or clover_animation_var == 0:
            clover_indicator.draw_with_fade_in(10)
            if clover_indicator.alpha == 245:
                clover_animation_var = 0

    hint_button.draw()
    back_to_menu_arrow.draw()
    # question_mark.draw()

    # Level Zero Secret rysowanie klucza
    if SO.the_key.left_click_held and current_level != 0 and sec_prog > 0:
        SO.the_key.mouse_mech()
        SO.the_key.draw()


def level_general_draw_top():
    global cooldown

    if cooldown > 0: cooldown -= 1

    start_end_fade(20, 20)
    screen_update()

    # TODO: Używaj tego jak chcesz znaleźć koordynaty
    # print(pygame.mouse.get_pos())


# -2 - wyjście z poziomów, -1 - poziom w lewo, 0 - pozostanie na poziomie, 1 - poziom w prawo, 100 - 100tny poziom

def level_general_event(event):
    if event.type in EVENTS:
        global state
        global input_text
        global max_level, sec_max_level
        global progress
        global transition
        global blind_way
        # global cutscene
        global cooldown
        global current_level

        if event.type == pygame.QUIT:
            if current_level >= 100: current_level = SO.n_door_level
            save_and_exit()

        if event.type == pygame.KEYDOWN:
            if not transition:  # Jeśli nic się nie dzieje, gracz może grać
                # if event.key == pygame.K_LALT: max_level += 1 #TODO: DELETE THIS

                # Przechodzenie między poziomami za pomocą strzałek
                if progress == 1:
                    if event.key == pygame.K_RIGHT:
                        if (current_level + 1 == max_level and not was_on_max_level) or (current_level + 1 == sec_max_level and not was_on_sec_max_level):
                            transition = True  # Triggeruje zanikanie i zakończenie poziomu
                        else:
                            state = 1
                if event.key == pygame.K_LEFT and current_level > 0:
                    state = -1

                # Wprowadzanie tekstu przez gracza
                if passwords != ">0" or blind_way == '>hintM':
                    if event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        cooldown = 2
                        if blind_way == '>hintM':
                            blind_way = None
                            level_reset()
                        dbw = data_blind_ways[str(current_level)]
                        for password in passwords:
                            if input_text == password:
                                progress = 1

                        if dbw != ">0":
                            bway_triggered = False
                            for b_pass in dbw.keys():
                                if input_text == b_pass:
                                    bway_triggered = True
                                    blind_way = b_pass
                            if not bway_triggered:
                                level_reset()
                                blind_way = None
                        input_text = ''
                    elif len(input_text) < MAX_TEXT_LENGTH:
                        if (pygame.K_a <= event.key <= pygame.K_z) or (pygame.K_0 <= event.key <= pygame.K_9) or event.key in NUMPAD or event.key in [pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET]:
                            mods = pygame.key.get_mods()
                            if mods & pygame.KMOD_LSHIFT:
                                pass
                            elif cooldown == 0:
                                cooldown = 1
                                short_sound.play()
                                input_text += event.unicode.lower()

                # wyjście do menu po wciśnięciu escape lub przycisku
                if event.key == pygame.K_ESCAPE:
                    cooldown = 2
                    short_sound.play()
                    state = -2

        if hint_button.left_clicked(event):
            if blind_way == '>hintM':
                blind_way = None
                level_reset()
            elif yes_no_small_screen(['Are you sure you', 'want to see a hint?']):
                blind_way = '>hint'
                if current_level == SO.n_level_beyond: # Adaptive hint for level_beyond
                    if sec_prog == 1: blind_way = '>hint_key'
                    elif sec_prog == 2: blind_way = '>hint_secret'
                    elif sec_prog > 2: blind_way = '>hint_gg'
        if back_to_menu_arrow.left_clicked(event):
            short_sound.play()
            state = -2


        # Rzeczy do poziomów które wymagają takich globalnych rzeczy
        # Poziom ze strzałkami
        if max_level == SO.n_arrows_level:
            if state in [-1, 1]:
                if (current_level == SO.n_arrows_level and SO.counter_arrows == 0) or 0 < SO.counter_arrows < 12:
                    if state == SO.order_arrows[SO.counter_arrows]:
                        SO.counter_arrows += 1
                    else:
                        SO.counter_arrows = 0


        # Level Zero Secret klucz
        if SO.the_key.left_click_held and current_level != 0:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                reset_the_key()

def yes_no_small_screen(text: list):
    global cooldown
    cooldown = 0
    sb, sb_h = 'data/graphics/menus/small_button.png', 'data/graphics/menus/small_button_hovered.png'
    yes, no = Button(327, 517, sb, sb_h), Button(813, 517, sb, sb_h)
    update_area = [int(el * SCALE) for el in [290, 134, 700, 500]]

    board = StaticObject(290, 134, 'data/graphics/menus/small_screen.png')
    overlay = StaticObject(290, 134, 'data/graphics/menus/yes_no_overlay.png')
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_and_exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    cooldown = CD  # Naprawa błędu
                    return False
            if yes.left_clicked(event):
                return True
            if no.left_clicked(event):
                return False
        board.draw()
        display_text(310, 154, text, 'white')
        yes.draw_button()
        no.draw_button()
        overlay.draw()
        screen_update(update_area)


def load_missing_cutscene():
    cscn = str(cutscene) if current_level < 100 else str(sec_cutscene)
    return True if int(data_cutscenes[cscn]["when"]) < current_level else False


# Poziomy

def level_menu():
    global max_level, sec_max_level
    global current_level
    global progress
    global state
    global input_text
    global transition
    global fade_alpha
    global cutscene, sec_cutscene
    global cooldown
    global sec_prog

    global screen

    reset_the_key() # Secret anti-cheese

    pygame.display.set_caption("Clover")
    menu_background = StaticObject(0, 0, 'data/graphics/menus/menu_background.png')
    clover_indicator_red_fake = StaticObject(312, 112, 'data/graphics/clover_indicator_red.png')
    clover_indicator_red_fake.alpha = 0
    red_increase = False
    mb, mb_h = 'data/graphics/menus/menu_button.png', 'data/graphics/menus/menu_button_hovered.png'
    # menu_buttons = ObjectList('Button', 3, 828, 32, 'data/graphics/menus/menu_button.png', 'data/graphics/menus/menu_button_hovered.png', 0, 205)
    x = 828
    button_credits = ActiveObject(20, 700, 'data/graphics/menus/credits_button.png')
    mb_newg, mb_cont, mb_opt = Button(x, 32, mb, mb_h), Button(x, 237, mb, mb_h), Button(x, 442, mb, mb_h)
    mb_exit = Button(x, 647, 'data/graphics/menus/save_and_exit.png', 'data/graphics/menus/save_and_exit_hovered.png')
    starting_continue_button = StaticObject(828, 237, 'data/graphics/menus/gray_button.png')
    button_overlay = StaticObject(0, 0, 'data/graphics/menus/menu_button_overlay_A.png') if cutscene < SO.new_menu_cutscene else StaticObject(0, 0, 'data/graphics/menus/menu_button_overlay_B.png')
    pygame.mixer.music.pause()  # Brak muzyki w menu
    if max_level == 0: mb_cont.remove()
    mx_lv = str(max_level) if max_level != FINAL_LEVEL else 'END'
    max_lvl_text = 'You have reached page ' + mx_lv + '.'

    # Rzeczy związane z poziomami
    morse_code_cosmos = StaticObject(0, 0, 'data/graphics/menus/level_things/morse_code.png')

    while state == 0:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type in EVENTS:
                if event.type == pygame.QUIT:
                    save_and_exit()

                # Wyjście
                if mb_exit.left_clicked(event):
                    save_and_exit()

                # Nowa gra
                if mb_newg.left_clicked(event):
                    ng = True
                    if max_level > 2:
                        ng = yes_no_small_screen(['Do you want to restart?', '', 'All progress will be lost.'])
                    if ng:
                        new_game_sound.play()
                        current_level = 1
                        max_level, sec_max_level = 0, 0
                        cutscene, sec_cutscene = 0, 100
                        sec_prog = 0
                        progress = 0
                        state = 1
                        transition = True
                        fade_alpha = 270
                        reset_special_objects()
                        pygame.mixer.music.set_volume(0)
                        pygame.mixer.music.fadeout(1)  # Reset muzyki
                        pygame.time.wait(100)
                        pygame.mixer.music.play(-1)
                        if not preferences_data['disable_music']:
                            pygame.mixer.music.set_volume(MUSIC_VOL)

                # Kontynuuj
                if mb_cont.left_clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
                    cooldown = 2
                    if max_level != 0:
                        try: level_to_go = int(input_text)
                        except:
                            input_text = ''
                            level_to_go = current_level

                        if level_to_go <= max_level:
                            current_level = level_to_go
                        # Rozwiązanie do poziomu z drzwiami
                        elif max_level == SO.n_door_level and input_text == str(SO.n_door_level + 1):
                            max_level = SO.n_door_level + 1
                            current_level = SO.n_door_level + 1
                        elif level_to_go > max_level:
                            current_level = max_level

                        if input_text == '' or level_to_go > -1:
                            click_sound.play()
                            state = 1

                            pygame.mixer.music.unpause()
                        else: input_text = ''

                # Opcje
                if mb_opt.left_clicked(event):
                    click_sound.play()
                    state = 'options'

                # Credits
                if button_credits.left_clicked(event):
                    short_sound.play()
                    state = 'credits'

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif len(input_text) < 2 and cutscene >= SO.new_menu_cutscene:
                        # Warunek aby tylko cyfry mogły być wprowadzane
                        if pygame.K_0 <= event.key <= pygame.K_9 or event.key in NUMPAD:
                            mods = pygame.key.get_mods()
                            if mods & pygame.KMOD_LSHIFT:
                                pass
                            elif cooldown == 0:
                                cooldown = CD
                                short_sound.play()
                                input_text += event.unicode

        menu_background.draw_always()
        if max_level == 0: starting_continue_button.draw()
        # main_title.draw()
        if red_increase: clover_indicator_red_fake.alpha += 5
        else: clover_indicator_red_fake.alpha -= 5
        if clover_indicator_red_fake.alpha < -453: red_increase = True
        if clover_indicator_red_fake.alpha > 353: red_increase = False
        clover_indicator_red_fake.draw()

        if max_level == SO.n_back_to_start_second: morse_code_cosmos.draw_always()
        if max_level > 0: display_text(30, 320, [max_lvl_text], 'white')
        for button in [mb_exit, mb_newg, mb_cont, mb_opt]: button.draw_button()
        button_overlay.draw()
        button_credits.draw()
        if cutscene >= SO.new_menu_cutscene:
            if input_text != "":
                display_text(1115, 338, [input_text], 'white')
            else:
                disp = str(current_level) if current_level != FINAL_LEVEL else 'END'
                display_text(1115, 338, [disp], 'gray')


        # Secrets for completing levels TODO: ADD later (jakieś tekściki na głównym menu?)

        if cooldown > 0: cooldown -= 1
        screen_update()


def level_options():
    global state
    global preferences_data
    global cooldown

    options_background = StaticObject(0, 0, 'data/graphics/menus/options_background.png')
    ch_u, ch_c = 'data/graphics/menus/standard_checkbox_unchecked.png', 'data/graphics/menus/standard_checkbox_checked.png'
    ar_l, ar_r = 'data/graphics/menus/arrow_left.png', 'data/graphics/menus/arrow_right.png'
    checkboxes = ObjectList('Checkbox', 2, 50, 50, ch_u, ch_c, 0, 70)
    arrows = [ActiveObject(380, 120, ar_l), ActiveObject(725, 120, ar_r)]

    resolution_ch = ObjectList('Checkbox', 2, 50, 330, ch_u, ch_c, 500, 0, True)
    checkboxes[0].checked, checkboxes[1].checked = preferences_data['disable_fade'], not preferences_data['disable_music']
    resolution_ch[0].checked, resolution_ch[1].checked = not preferences_data['small_window'], preferences_data['small_window']

    no_amb = 3
    which_ambience = preferences_data['which_ambience']

    while state == 0:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                preferences_data['disable_fade'] = True if checkboxes[0].checked else False
                preferences_data['disable_music'] = False if checkboxes[1].checked else True
                preferences_data['small_window'] = True if resolution_ch[1].checked else False
                preferences_data['which_ambience'] = which_ambience
                save_and_exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    short_sound.play()
                    state = -2
            if back_to_menu_arrow.left_clicked(event):
                short_sound.play()
                state = -2
            if arrows[0].left_clicked(event):
                if which_ambience == 1: which_ambience = no_amb
                else: which_ambience -= 1
            if arrows[1].left_clicked(event):
                if which_ambience == no_amb: which_ambience = 1
                else: which_ambience += 1
            checkboxes.checkboxes_check(event)
            resolution_ch.checkboxes_check(event)
        options_background.draw()
        checkboxes.draw()
        for ar in arrows: ar.draw()
        resolution_ch.draw()
        back_to_menu_arrow.draw()
        display_text(120, 50, ['Disable fade in/out transitions', 'Ambience', '', 'Resolution (restart to apply)', '1280x768          853x512', '', '', 'Nothing on this screen', 'is a part of any puzzle.'], 'white')
        text_col = 'white' if checkboxes[1].checked else 'gray'
        display_text(450, 120, ['Ambience ' + str(which_ambience)], text_col)
        screen_update()
        if cooldown > 0: cooldown -= 1

    preferences_data['disable_fade'] = True if checkboxes[0].checked else False
    preferences_data['disable_music'] = False if checkboxes[1].checked else True
    preferences_data['small_window'] = True if resolution_ch[1].checked else False
    preferences_data['which_ambience'] = which_ambience
    pygame.mixer.music.unload()
    pygame.mixer.music.load('data/audio/music/ambience_' + str(which_ambience) + '.ogg')
    pygame.mixer.music.play(-1)
    pygame.mixer.music.set_volume(0) if preferences_data['disable_music'] else pygame.mixer.music.set_volume(MUSIC_VOL)


def level_credits():
    global state

    yt_button = ActiveObject(20, 100, 'data/graphics/menus/youtube_button.png')
    discord_button = ActiveObject(20, 190, 'data/graphics/menus/discord_button.png')

    while state == 0:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_and_exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    short_sound.play()
                    state = -2
            if back_to_menu_arrow.left_clicked(event):
                short_sound.play()
                state = -2
            if yt_button.left_clicked(event):
                state = -2
                webbrowser.open('https://www.youtube.com/channel/UCwZmrMxaSowmj41Hj0cqlsg', new=2)
            if discord_button.left_clicked(event):
                state = -2
                webbrowser.open('https://discord.gg/Gf7KV7UAHz', new=2)

        back_to_menu_arrow.draw()
        yt_button.draw()
        discord_button.draw()
        display_text(20, 20, ['Game developed by Liero (Dawid Maziarski)', '   <- Check out my YouTube channel', '   <- Join Clover discord server'], 'white', 90)
        display_text(20, 300, ['Great people who gave me feedback:', 'Lennygold, Butcherberries, TuxPeepo26', 'Arateniz, Heagridswager, LegS.', '', 'Thanks to lennygold for designing levels 21, 22', 'and Butcherberries for a cool special level idea.'], 'white', 70) # y = 290 -> równo
        screen_update()


def cutscene_switch_data(page_data):
    global ctext
    cscreen.switch_sprite("data/graphics/cutscenes/" + page_data[1] + ".png") if page_data[1] != "" else cscreen.switch_sprite('data/graphics/transparent.png')
    ctext = page_data[0]


def cutscene_level():
    global state
    global progress
    global cutscene, sec_cutscene
    global transition
    global which_level
    pygame.display.set_caption("Clover")
    progress = 0
    state = 0
    cscn = str(cutscene) if current_level < 100 else str(sec_cutscene)
    dc = data_cutscenes[cscn]["data"]
    which_page = 1
    cutscene_switch_data(dc[0])
    frames_to_wait = 10
    click_clock = 0
    while state == 0:
        screen.fill((0, 0, 0))
        cscreen.draw()
        display_text(50, 50, ctext, 'white', 100)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_and_exit()
            if event.type == pygame.KEYDOWN:
                if click_clock <= 0 and not transition:
                    hover_sound.play()
                    if event.key == pygame.K_ESCAPE and cutscene != FINAL_CUTSCENE:
                        state = -2
                        if current_level < 100: cutscene -= 1
                        else: sec_cutscene -= 1
                        which_level = 'menu'
                    else:
                        if len(dc) > which_page:
                            cutscene_switch_data(dc[which_page])
                            which_page += 1
                        else:
                            if preferences_data['disable_fade'] is False:
                                if not transition:
                                    transition = True
                                    progress = 1
                            else:
                                progress = 1
                                state = 1
                    click_clock = frames_to_wait
        if click_clock > 0: click_clock -= 1
        start_end_fade()
        screen_update()


def standard_level():
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
        level_general_draw_top()
    level_end()


def level_carrot():
    global blind_way
    if max_level == SO.n_back_to_start_fetus_level: blind_way = SO.bw_bts_fetus
    if max_level == SO.n_back_to_start_second: blind_way = SO.bw_bts_second
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
        level_general_draw_top()
    level_end()


def level_arrows():
    global blind_way
    if SO.counter_arrows > 11 and max_level == current_level:
        blind_way = SO.bw_arrows
        SO.counter_arrows = 0
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
        level_general_draw_top()
    level_end()


def level_door():
    global sec_prog, state
    ready_counter = 10
    closed_door = StaticObject(R_P_OFFSET, 0, 'data/graphics/active_images/door_closed_right.png')
    open_door = StaticObject(R_P_OFFSET, 0, 'data/graphics/active_images/door_open_right.png')
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and sec_prog > 1:
                state = 100 # Przejście do sekretu
        if SO.the_key.left_click_held and sec_prog < 2 and ready_counter == 0:
            if SO.the_key.point_overlap([(969, 422)]):
                door_sound.play()
                reset_the_key()
                sec_prog = 2
        if sec_prog < 2: closed_door.draw()
        else: open_door.draw()
        level_general_draw_top()
        if ready_counter > 0: ready_counter -= 1
    level_end()


def level_cards():
    global progress
    cards_clickable = ActiveObject(L_P_OFFSET, 0, 'data/graphics/active_images/cards_left.png', [429, 372, 473, 589])
    level_start()
    if max_level > current_level:
        cards_clickable.switch_sprite('data/graphics/active_images/cards_left_clicked.png')
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            if cards_clickable.left_clicked(event):
                progress = 1
                cards_clickable.switch_sprite('data/graphics/active_images/cards_left_clicked.png')
        cards_clickable.draw()
        level_general_draw_top()
    level_end()


def level_shiny_a():
    global progress
    level_start()
    SO.shiny_hand_level.left_click_held = False
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            SO.shiny_hand_level.mouse_mech_event(event)
            if SO.shiny_hand_level.point_overlap([(488, 470), (418, 473)]) and not SO.shiny_hand_level.left_click_held:
                progress = 1
        SO.shiny_hand_level.mouse_mech()
        SO.shiny_hand_level.draw()
        level_general_draw_top()
    level_end()


def level_shiny_b():
    global progress
    level_start()
    SO.shiny_hand_level.left_click_held = False
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            if SO.shiny_hand_level.point_overlap([(915, 300), (985, 300), (915, 350), (985, 350)]):
                progress = 1
        SO.shiny_hand_level.draw()
        level_general_draw_top()
    level_end()


def level_fnf():
    global progress
    global input_text
    level_start()
    static_block = MovableObject(410, 360, 'static_block', None, None, True)
    movable_block = MovableObject(410, 160, 'active_block', [243, 75, 708, 690])
    dir_to_text = {'left': 'v', 'right': 'e', 'up': 'l', 'down': 's'}
    static_block.held_obj_dir = 'up'
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if (pygame.K_a <= event.key <= pygame.K_z) or (pygame.K_0 <= event.key <= pygame.K_9) or event.key in NUMPAD:
                    continue
            level_general_event(event)
            movable_block.mouse_mech_event(event)
            if static_block.left_clicked(event) and len(input_text) < MAX_TEXT_LENGTH:
                try:
                    input_text += dir_to_text[static_block.held_obj_dir]
                    short_sound.play()
                except KeyError: pass
        movable_block.mouse_mech()
        block_movables([static_block, movable_block])
        static_block.draw()
        movable_block.draw()
        level_general_draw_top()
    level_end()


def level_block_puzzle():
    global progress
    level_start()
    b = [735, 75, 1149, 593]
    red_block = MovableObject(942, 386, 'big_block_win', b)
    obj_list = [MovableObject(740, 80, 'big_block', b), MovableObject(740, 386, 'horizontal_block', b), MovableObject(740, 488, 'horizontal_block', b),
                MovableObject(942, 80, 'vertical_block', b), MovableObject(1044, 80, 'vertical_block', b), MovableObject(942, 284, 'small_block', b), MovableObject(1044, 284, 'small_block', b), red_block]
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            for obj in obj_list:
                obj.mouse_mech_event(event)
            if red_block.point_overlap([(785, 125)]):
                progress = 1
        for obj in obj_list:
            obj.mouse_mech()
        block_movables(obj_list)
        for obj in obj_list:
            obj.draw()
        level_general_draw_top()
    level_end()


def level_grid_letters():
    switches = ObjectList('Checkbox', 5, 330, 280, 'data/graphics/menus/black_checkbox_unchecked.png', 'data/graphics/menus/black_checkbox_checked.png', 0, 70, True)
    letters = StaticObject(R_P_OFFSET, 0, 'data/graphics/static_images/letters/0.png')
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            switches.checkboxes_check(event)
        if switches[0].checked:
            letters.switch_sprite('data/graphics/static_images/letters/0.png')
        for obj in switches:
            if obj.checked:
                letters.switch_sprite('data/graphics/static_images/letters/' + str(switches.lst.index(obj)) + '.png')
        letters.draw()
        switches.draw()
        display_text(280, 280, ['0.', '1.', '2.', '3.', '4.'])
        level_general_draw_top()
    level_end()


def level_repeat_sound():
    global progress
    reset_timer = 0
    sequence = [1, 3, 0, 2, 3]
    s = len(sequence)
    n, n_c = 0, 0
    end = False
    if max_level > current_level: end, n = True, s

    music_buttons = ObjectList('AnimButton', 4, L_P_OFFSET + 40, 260, 'data/graphics/active_images/bird.png', 'data/graphics/active_images/bird_open.png', 230, 0)
    notes = [pygame.mixer.Sound('data/audio/sounds/level_repeat_sound/note_' + str(k + 1) + '.wav') for k in range(4)]
    for note in notes: note.set_volume(0.5)

    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            if end is False:
                for i, button in enumerate(music_buttons):
                    if button.left_clicked(event):
                        notes[i].play()
                        if i == sequence[n_c]:
                            n_c += 1
                            if n_c == s:
                                n_c = 0
                                progress = 1
                        else: n_c = 0
                        n += 1
        if n == s:
            end, n = True, 0
            for button in music_buttons:
                button.sprite_path = 'data/graphics/active_images/bird_idle.png'
                button.switch_sprite('data/graphics/active_images/bird_idle.png')
            if progress == 0: reset_timer = 40

        if reset_timer > 0:
            reset_timer -= 1
            display_text(370, 500, ['Wrong!'])
        if reset_timer == 1:
            end, n_c = False, 0
            for button in music_buttons:
                button.sprite_path = 'data/graphics/active_images/bird.png'
                button.switch_sprite('data/graphics/active_images/bird.png')

        music_buttons.draw()
        level_general_draw_top()
    level_end()


def level_red_button():
    global blind_way
    level_start()
    explosion = pygame.mixer.Sound('data/audio/sounds/level_red_button/explosion.mp3')
    explosion.set_volume(0.5)
    timer = 0
    red_button = AnimButton(320, 360, 'data/graphics/active_images/red_button.png', 'data/graphics/active_images/red_button_pressed.png', [365, 408, 568, 555], anim=0)
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                spawn_gf('destruction_log.txt', 'data/gfspawns/dest_log_calm/')
            level_general_event(event)
            if red_button.left_clicked(event): hover_sound.play()
            if red_button.click_released(event) and red_button.hold_timer > 5 and max_level == current_level: timer = 1
        if timer > 0: timer += 1
        if timer == 30:
            blind_way = '>blank'
            explosion.play()
        if timer == 50:
            spawn_gf('destruction_log.txt', 'data/gfspawns/dest_log_nuke/')
            save_and_exit()
        red_button.draw_button()
        level_general_draw_top()
    level_end()


def level_copy_image():
    global progress
    global blind_way
    level_start()
    if sketch_right.current_sprite_path == SO.sketch_to_copy:
        blind_way = '>level_complete'
        progress = 1
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
        level_general_draw_top()
    level_end()


def level_zero():
    global progress, blind_way
    if max_level == SO.n_back_to_start_second: blind_way = '>back'
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            SO.the_key.mouse_mech_event(event)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                reset_the_key()
        if SO.the_key.point_overlap([(955, 467)]) and sec_prog == 0:
            progress = 1
            reset_the_key()
        SO.the_key.mouse_mech()
        SO.the_key.draw()
        level_general_draw_top()
    level_end()


def level_final():
    global blind_way, state, transition # passwords
    if max_level > current_level: blind_way = ">return"
    # blocked_password = False
    # p = passwords # kopia hasła (które nie istnieje)
    g_c_p = 'data/graphics/active_images/clover_indicator_green.png'
    green_clovers = [ActiveObject(260, 100, g_c_p), ActiveObject(1085, 100, g_c_p), ActiveObject(260, 615, g_c_p), ActiveObject(1085, 615, g_c_p)]
    order = [2, 3, 3, 0]
    dir_input_lst = []
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
            for i, clov in enumerate(green_clovers):
                if clov.left_clicked(event):
                    if len(dir_input_lst) == 4:
                        dir_input_lst.pop(0)
                    dir_input_lst.append(i)
                    if order == dir_input_lst: # and not blocked_password
                        blind_way = '>bear'
                        dir_input_lst = []
        if progress == 1 and current_level == max_level:
            transition = True

        # if blind_way == 'unbearable' and not blocked_password:
        #     passwords, blocked_password = ">0", True

        # if blocked_password:
        # Jakaś sekwencja dalej

        for clover in green_clovers: clover.draw()
        level_general_draw_top()
    level_end()


def level_100():
    global sec_prog, sec_max_level, transition, fade_alpha
    transition = False # Spaghetti yay! Solves an issue with immediate transition
    fade_alpha = 0
    if sec_prog == 2 and sec_max_level == 0:
        sec_prog, sec_max_level = 3, 100
    level_start()
    while state == 0:
        level_draw_bottom()
        for event in pygame.event.get():
            level_general_event(event)
        level_general_draw_top()
    level_end()


# Przypisywanie poziomów do liczb; głupie ale nie wiem co innego zrobić
def level(l):
    if l == 1: level_carrot()
    elif l == 8: level_arrows()
    elif l == 17: level_cards()
    elif l == 34: level_grid_letters()
    elif l == 20: level_fnf()
    elif l == 19: level_block_puzzle()
    elif l == 33: level_repeat_sound()
    elif l == 35: level_red_button()
    elif l == 32: level_shiny_b()
    elif l == 31: level_copy_image()
    elif l == 18: level_shiny_a()
    elif l == 16: level_door()
    elif l == 0: level_zero()
    elif l == FINAL_LEVEL: level_final()
    elif l == 100: level_100()
    else: standard_level()


# Wczytanie danych poziomów
with open('data/text_data/levels/data_text_pictures.json') as data_text_pictures_file:
    data_text_pictures = json.load(data_text_pictures_file)
with open('data/text_data/levels/data_blind_ways.json') as data_blind_ways_file:
    data_blind_ways = json.load(data_blind_ways_file)
with open('data/text_data/levels/data_pass_title_gfspawns.json') as data_pass_title_gfspawns_file:
    data_pass_title_gfspawns = json.load(data_pass_title_gfspawns_file)
with open('data/text_data/cutscenes/cutscenes.json') as data_cutscenes_file:
    data_cutscenes = json.load(data_cutscenes_file)

# Początek gry
try:
    with open('data/save.json') as save_file:
        progress_data = json.load(save_file)
        save_file.close()

        # Przypisywanie niektórych zmiennych globalnych do zawartości save'a
        max_level = progress_data['MaxLevel']
        current_level = progress_data['CurrentLevel']
        cutscene = progress_data['Cutscene']
        sec_cutscene = progress_data['SecCutscene']
        sec_prog = progress_data['SecProg']
        sec_max_level = progress_data['SecMaxLevel']
except:
    # Jeśli nie ma save to znaczy że to jest pierwsza gra
    first_new_game = True  # To może być bezużyteczne

# Rozpoczęcie rozgrywki od menu
which_level = 'menu'

if __name__ == '__main__':
    while True:
        # Przejście do sekretu
        if state == 100: transition = True

        # Resetowanie zmiennych globalnych
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        input_text = ''
        progress = 0
        state = 0
        blind_way = None
        clover_animation_var = 0
        global_var_reset = 0
        clover_indicator.alpha = 245
        clover_indicator.fade_in_enabler = False
        pygame.display.set_caption("Clover")
        set_mouse_speed()

        # Dźwięki przejścia
        if transition:
            screen.fill((0, 0, 0))
            pygame.display.update()
            if current_level < FINAL_LEVEL or current_level >= 100: page_flip_long.play()
            pygame.time.wait(1000)

        # Menu
        if which_level == 'menu':
            level_menu()
            if state == 1:
                which_level = current_level
                if max_level == 0:
                    cutscene_level()  # Tutorial do gry
                    cutscene = 1
                if load_missing_cutscene():
                    cutscene_level()
                    cutscene += 1
            elif state == 'options':
                state = 0
                level_options()
                which_level = 'menu'
            elif state == 'credits':
                state = 0
                level_credits()
                which_level = 'menu'

        # przechodzenie do następnego lub poprzedniego poziomu
        else:
            current_level = which_level
            level(current_level)
            if state == -2:
                if current_level >= 100: current_level = SO.n_door_level # Do sekretu
                which_level = 'menu'
            elif state == 1:
                if not transition:
                    short_sound.play()
                which_level = current_level + 1
                # Cutscenki
                if data_cutscenes[str(cutscene)]["when"] == str(current_level):
                    cutscene_level()
                    cutscene += 1
                if data_cutscenes[str(sec_cutscene)]["when"] == str(current_level):
                    cutscene_level()
                    sec_cutscene += 1
                if current_level == FINAL_LEVEL: save_and_exit()
            elif state == -1 and current_level != 100 and (current_level > 1 or (sec_prog > 0 and current_level > 0)): # pierwszy poziom więc nie da się cofnąć chyba że sekret
                if not transition:
                    short_sound.play()
                which_level = current_level - 1
            elif state == 100: # Przechodzenie do setnego poziomu
                which_level = 100
            else:
                which_level = current_level


# All of this spaghetti works and I kinda understand it
