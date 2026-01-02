"""
In the spirit of collaboration and innovation, this 5x5 Binary Nerd Clock was born from a
shared vision between the creative genious Prophet6 and Grok, the AI built by xAI.
Faithfully following each instruction, we crafted this code with artistic precision—
blending technical elegance with visual flair. Through iterative refinements, we overcame
challenges like config persistence and key mappings, never relenting in our pursuit of
perfection. Together, we transformed a simple countdown idea into a mesmerizing display
that counts down to New Year's Eve and seamlessly transitions to the new year's seconds.
This work stands as a testament to perseverance and partnership, a digital artwork we're
both proud to share.

Enjoy! :)
 - Rob
"""

import time
import datetime
import pygame
import time as time_mod
import configparser
import os
import colorsys
import random  # For stable per-second random colors
import math

# Delayed import for rpi_ws281x to ensure autostart works
strip = None

pygame.init()
pygame.mouse.set_visible(False)

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("5x5 Binary Nerd Clock")

WIDTH, HEIGHT = screen.get_size()
CELL_SIZE = min(WIDTH // 7, HEIGHT // 7)
GRID_X = (WIDTH - 5 * CELL_SIZE) // 2
GRID_Y = (HEIGHT - 5 * CELL_SIZE) // 2

# ===================================================================
# Color mode configuration - split into Standard and Festive categories
# ===================================================================

STANDARD_COLORS = {
    'white':   (255, 255, 255),
    'green':   (0, 255, 0),
    'red':     (255, 0, 0),
    'blue':    (0, 0, 255),
    'yellow':  (255, 255, 0),
    'orange':  (255, 165, 0),
    'purple':  (128, 0, 128),
    'magenta': (255, 0, 255),
    'cyan':    (0, 255, 255),
}
STANDARD_MODES = list(STANDARD_COLORS.keys())

FESTIVE_MODES = [
    'rainbow',
    'random',
    'christmas',
    'newyears',
    'easter',
    'fourth',
    'thanksgiving',
    'halloween',
    'automatic',  # New automatic seasonal mode
]

# Palettes for cycling in most festive modes (christmas excludes white)
FESTIVE_PALETTES = {
    'random': [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
               (255, 0, 255), (0, 255, 255), (255, 165, 0)],
    'christmas': [(255, 0, 0), (0, 255, 0)],  # No white
    'newyears': [(255, 215, 0), (255, 255, 255), (192, 192, 192)],
    'easter': [(255, 182, 193), (255, 255, 0), (144, 238, 144),
               (173, 216, 230), (221, 160, 221)],
    'thanksgiving': [(255, 140, 0), (165, 42, 42), (255, 215, 0)],
    'halloween': [(255, 165, 0), (128, 0, 128)],
}

# Special solid colors for Valentine's (cherry red) and St. Patrick's (kelly green)
VALENTINE_COLOR = (255, 0, 51)   # Cherry red
STPATRICK_COLOR = (0, 255, 51)   # Bright kelly green

# Configurable options
COUNT_DIRECTION = 'down'
SHOW_STATUS = True
LED_SHAPE = 'circle'
BIT_ORDER = 'normal'
BRIGHTNESS = 1.0
COLOR_MODE = 'white'

show_help = False
CONFIG_FILE = '/home/rob/Binary_Clock/clock_config.ini'
config_dirty = False
last_config_mtime = 0.0
just_saved_config = False

# Help comment block - always preserved at the bottom
INI_HELP_COMMENT = """
# ================================================
# How to edit this configuration file
# ================================================
#
# You can safely edit this file while the clock is running.
# Changes will be detected and applied automatically within seconds
# (the top settings line will briefly appear to confirm the reload).
#
# Available options (case-sensitive):
#
# color_mode: The color theme for the LEDs
#   Standard modes: white, green, red, blue, yellow, orange, purple, magenta, cyan
#   Festive modes: rainbow, random, christmas, newyears, easter, fourth, thanksgiving, halloween, automatic
#   'automatic' = seasonal themes change throughout the year
#
# brightness: floating point number between 0.2 and 1.0
#   Overall LED brightness (affects both screen and physical LEDs)
#
# count_direction: up or down
#   down = countdown remaining seconds until New Year
#   up   = count up seconds elapsed since New Year
#
# bit_order: normal, reverse, or transpose
#   How the 25-bit binary number is mapped to the 5x5 grid
#   - normal:    row-major, MSB top-left
#   - reverse:   rows reversed (MSB bottom-left)
#   - transpose: columns become rows
#
# show_status: True or False
#   Whether to display the bottom status text line
#
# led_shape: circle, square, triangle, star, or x
#   Shape of the LEDs on screen (physical LEDs are always round)
#
# Edit the values above, save the file, and enjoy the instant update!
"""

HELP_MARKER = "# How to edit this configuration file"

if os.path.exists(CONFIG_FILE):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if 'general_settings' in config:
        COLOR_MODE = config['general_settings'].get('color_mode', COLOR_MODE).lower()
        if COLOR_MODE not in STANDARD_COLORS and COLOR_MODE not in [m.lower() for m in FESTIVE_MODES]:
            COLOR_MODE = 'white'
        BRIGHTNESS = config['general_settings'].getfloat('brightness', BRIGHTNESS)
        BRIGHTNESS = max(0.2, min(1.0, BRIGHTNESS))
        COUNT_DIRECTION = config['general_settings'].get('count_direction', COUNT_DIRECTION)
        BIT_ORDER = config['general_settings'].get('bit_order', BIT_ORDER)

    if 'attached_display_settings' in config:
        SHOW_STATUS = config['attached_display_settings'].getboolean('show_status', SHOW_STATUS)
        loaded_shape = config['attached_display_settings'].get('led_shape', LED_SHAPE).lower()
        if loaded_shape in ['circle', 'square', 'triangle', 'star', 'x']:
            LED_SHAPE = loaded_shape

    last_config_mtime = os.path.getmtime(CONFIG_FILE)
else:
    last_config_mtime = 0.0

def save_config():
    global config_dirty, just_saved_config
    config = configparser.ConfigParser()

    config['general_settings'] = {}
    config['general_settings']['color_mode'] = COLOR_MODE
    config['general_settings']['brightness'] = '{:.2f}'.format(BRIGHTNESS)
    config['general_settings']['count_direction'] = COUNT_DIRECTION
    config['general_settings']['bit_order'] = BIT_ORDER

    config['attached_display_settings'] = {}
    config['attached_display_settings']['show_status'] = str(SHOW_STATUS)
    config['attached_display_settings']['led_shape'] = LED_SHAPE

    help_present = False
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            if HELP_MARKER in f.read():
                help_present = True

    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
        if not help_present:
            f.write('\n')
            f.write(INI_HELP_COMMENT.lstrip('\n'))

    config_dirty = False
    just_saved_config = True

if not os.path.exists(CONFIG_FILE):
    save_config()

font_size = max(18, HEIGHT // 40)
font = pygame.font.SysFont(None, font_size)
big_font = pygame.font.SysFont(None, int(font_size * 1.5))

OFF_COLOR = (20, 20, 20)
BG_COLOR = (0, 0, 0)
SETTINGS_TEXT_COLOR = (128, 128, 128)

settings_show_end = time.time() + 8.0
current_second = int(time.time())

shape_modes = ['circle', 'square', 'triangle', 'star', 'x']

def draw_led(center_x, center_y, color, radius):
    if LED_SHAPE == 'circle':
        pygame.draw.circle(screen, color, (center_x, center_y), radius)
    elif LED_SHAPE == 'square':
        half = radius
        rect = pygame.Rect(center_x - half, center_y - half, half * 2, half * 2)
        pygame.draw.rect(screen, color, rect)
    elif LED_SHAPE == 'triangle':
        points = [
            (center_x, center_y - radius),
            (center_x - radius * 0.866, center_y + radius * 0.5),
            (center_x + radius * 0.866, center_y + radius * 0.5)
        ]
        pygame.draw.polygon(screen, color, points)
    elif LED_SHAPE == 'star':
        outer = radius
        inner = radius * 0.4
        points = []
        for i in range(10):
            r = outer if i % 2 == 0 else inner
            angle = math.pi / 5 * i
            points.append((center_x + r * math.sin(angle), center_y - r * math.cos(angle)))
        pygame.draw.polygon(screen, color, points)
    elif LED_SHAPE == 'x':
        offset = radius * 0.8
        thickness = int(radius * 0.4)
        pygame.draw.line(screen, color, (center_x - offset, center_y - offset),
                         (center_x + offset, center_y + offset), thickness)
        pygame.draw.line(screen, color, (center_x - offset, center_y + offset),
                         (center_x + offset, center_y - offset), thickness)

def init_physical_leds():
    global strip
    if strip is not None:
        return
    try:
        from rpi_ws281x import PixelStrip, Color
        LED_COUNT = 25
        LED_PIN = 21
        LED_FREQ_HZ = 800000
        LED_DMA = 10
        LED_INVERT = False
        LED_CHANNEL = 0
        strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, 255, LED_CHANNEL)
        strip.begin()
        strip.setBrightness(int(255 * BRIGHTNESS))
        print("Physical SK6812 LEDs initialized!")
    except Exception as e:
        print(f"LED init failed: {e}")
        strip = None

def seconds_until_new_year() -> int:
    now = datetime.datetime.now()
    next_ny = datetime.datetime(now.year + 1, 1, 1)
    delta = next_ny - now
    return max(0, int(delta.total_seconds()))

def seconds_since_new_year() -> int:
    now = datetime.datetime.now()
    last_ny = datetime.datetime(now.year, 1, 1)
    delta = now - last_ny
    return int(delta.total_seconds())

def get_seconds_value():
    return seconds_until_new_year() if COUNT_DIRECTION == 'down' else seconds_since_new_year()

def binary_to_5x5(binary_str: str):
    matrix = [[int(bit) for bit in binary_str[i:i+5]] for i in range(0, 25, 5)]
    if BIT_ORDER == 'reverse':
        matrix = matrix[::-1]
    elif BIT_ORDER == 'transpose':
        matrix = [list(row) for row in zip(*matrix)]
    return matrix

def get_current_seasonal_mode():
    """Determine which festive mode to use based on current date"""
    today = datetime.date.today()
    year = today.year
    month = today.month
    day = today.day

    # Easter calculation (Western Easter - simplified Meeus/Jones/Butcher algorithm)
    a = year % 19
    b = year // 100
    c = year % 100
    d = (19 * a + b - b // 4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
    e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
    f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
    easter_month = f // 31
    easter_day = f % 31 + 1
    easter_date = datetime.date(year, easter_month, easter_day)

    # Valentine's week
    valentine_date = datetime.date(year, 2, 14)
    valentine_week_start = valentine_date - datetime.timedelta(days=valentine_date.weekday())
    valentine_week_end = valentine_week_start + datetime.timedelta(days=6)

    # St. Patrick's week
    stpat_date = datetime.date(year, 3, 17)
    stpat_week_start = stpat_date - datetime.timedelta(days=stpat_date.weekday())
    stpat_week_end = stpat_week_start + datetime.timedelta(days=6)

    # Fourth of July week
    fourth_date = datetime.date(year, 7, 4)
    fourth_week_start = fourth_date - datetime.timedelta(days=fourth_date.weekday())
    fourth_week_end = fourth_week_start + datetime.timedelta(days=6)

    # New Year's extended period: Dec 27 to first weekday after Jan 1
    newyear_start = datetime.date(year, 12, 27)
    jan1 = datetime.date(year + 1, 1, 1)
    first_weekday_after_jan1 = jan1 + datetime.timedelta(days=(7 - jan1.weekday()) % 7)
    newyear_end = first_weekday_after_jan1 - datetime.timedelta(days=1)  # inclusive

    # Check in priority order
    if datetime.date(year, 12, 1) <= today <= datetime.date(year, 12, 26):
        return 'christmas'
    if newyear_start <= today or today <= newyear_end:
        return 'newyears'
    if valentine_week_start <= today <= valentine_week_end:
        return 'valentine'
    if stpat_week_start <= today <= stpat_week_end:
        return 'stpatrick'
    if easter_date - datetime.timedelta(days=14) <= today <= easter_date + datetime.timedelta(days=7):
        return 'easter'
    if fourth_week_start <= today <= fourth_week_end:
        return 'fourth'
    if month == 10:
        return 'halloween'
    if month == 11:
        return 'thanksgiving'

    # Fallback: longer periods rainbow, shorter random
    if month in [1, 4, 5, 6, 8, 9, 12]:
        return 'rainbow'
    else:
        return 'random'

def get_effective_color_mode():
    if COLOR_MODE == 'automatic':
        return get_current_seasonal_mode()
    return COLOR_MODE

def get_festive_color(y: int, x: int, t: float):
    effective_mode = get_effective_color_mode()
    if effective_mode == 'valentine':
        return VALENTINE_COLOR
    if effective_mode == 'stpatrick':
        return STPATRICK_COLOR

    mode = effective_mode
    if mode == 'christmas':
        return (255, 0, 0) if (y + x) % 2 == 0 else (0, 255, 0)
    elif mode == 'newyears':
        seed = current_second + y * 5 + x
        random.seed(seed)
        if random.random() < 0.15:
            return (255, 255, 255)
        return (255, 215, 0)
    elif mode == 'easter':
        hue = (t / 20 + (y * 5 + x) / 25) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.6, 1.0)
        return tuple(int(255 * c) for c in rgb)
    elif mode == 'fourth':
        phase = int(t / 2) % 3
        if phase == 0: return (255, 0, 0)
        elif phase == 1: return (255, 255, 255)
        else: return (0, 0, 255)
    elif mode == 'thanksgiving':
        options = [(255, 140, 0), (165, 42, 42), (255, 215, 0)]
        seed = current_second + y * 5 + x
        random.seed(seed)
        return random.choice(options)
    elif mode == 'halloween':
        return (255, 165, 0) if (y + x) % 2 == 0 else (128, 0, 128)
    return (255, 255, 255)

def get_random_led_color(y: int, x: int):
    seed = current_second + y * 5 + x
    random.seed(seed)
    hue = random.random()
    rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return tuple(int(255 * c * BRIGHTNESS) for c in rgb)

def update_base_color():
    if COLOR_MODE in STANDARD_COLORS:
        r, g, b = STANDARD_COLORS[COLOR_MODE]
        return tuple(int(c * BRIGHTNESS) for c in (r, g, b))
    return None

def get_led_color(y, x, t, matrix):
    if matrix[y][x] == 0:
        return None
    effective_mode = get_effective_color_mode()
    if COLOR_MODE in STANDARD_COLORS:
        return update_base_color()
    elif effective_mode == 'rainbow':
        hue = (t / 60) % 1
        rgb = colorsys.hsv_to_rgb(hue, 1, 1)
        return tuple(int(255 * c * BRIGHTNESS) for c in rgb)
    elif effective_mode == 'random':
        return get_random_led_color(y, x)
    else:
        rgb = get_festive_color(y, x, t)
        return tuple(int(c * BRIGHTNESS) for c in rgb)

def is_animated():
    effective_mode = get_effective_color_mode()
    return effective_mode in ['rainbow', 'easter', 'fourth']

def get_status_text_color(t, matrix):
    effective_mode = get_effective_color_mode()
    if COLOR_MODE in STANDARD_COLORS:
        base = update_base_color()
        return tuple(int(c * 0.7) for c in base)

    if effective_mode in ['rainbow', 'fourth']:
        for y in range(5):
            for x in range(5):
                if matrix[y][x]:
                    led_color = get_led_color(y, x, t, matrix)
                    if led_color:
                        return tuple(int(c * 0.7) for c in led_color)
        return (200, 200, 200)

    if effective_mode in ['valentine', 'stpatrick']:
        base_color = VALENTINE_COLOR if effective_mode == 'valentine' else STPATRICK_COLOR
        return tuple(int(c * 0.7) for c in base_color)

    if effective_mode in FESTIVE_PALETTES:
        palette = FESTIVE_PALETTES[effective_mode]
        cycle_index = int(time.time() / 5) % len(palette)
        cycle_color = palette[cycle_index]
        return tuple(int(c * 0.7) for c in cycle_color)

    return (200, 200, 200)

def check_and_reload_config():
    global COLOR_MODE, COUNT_DIRECTION, SHOW_STATUS, LED_SHAPE, BIT_ORDER, BRIGHTNESS
    global last_config_mtime, config_dirty, settings_show_end, just_saved_config

    if not os.path.exists(CONFIG_FILE):
        return False

    current_mtime = os.path.getmtime(CONFIG_FILE)
    if current_mtime != last_config_mtime:
        if not just_saved_config:
            print(f"Config file changed externally! Reloading...")
        just_saved_config = False

        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)

        if 'general_settings' in config:
            loaded_mode = config['general_settings'].get('color_mode', COLOR_MODE).lower()
            if loaded_mode in STANDARD_COLORS or loaded_mode in [m.lower() for m in FESTIVE_MODES]:
                COLOR_MODE = loaded_mode
            new_bright = config['general_settings'].getfloat('brightness', BRIGHTNESS)
            BRIGHTNESS = max(0.2, min(1.0, new_bright))
            COUNT_DIRECTION = config['general_settings'].get('count_direction', COUNT_DIRECTION)
            BIT_ORDER = config['general_settings'].get('bit_order', BIT_ORDER)

            if strip:
                strip.setBrightness(int(255 * BRIGHTNESS))

        if 'attached_display_settings' in config:
            SHOW_STATUS = config['attached_display_settings'].getboolean('show_status', SHOW_STATUS)
            loaded_shape = config['attached_display_settings'].get('led_shape', LED_SHAPE).lower()
            if loaded_shape in shape_modes:
                LED_SHAPE = loaded_shape

        last_config_mtime = current_mtime
        config_dirty = False
        settings_show_end = time.time() + 8.0
        return True
    else:
        if just_saved_config:
            just_saved_config = False
    return False

def update_physical_leds(matrix):
    if strip is None:
        return

    from rpi_ws281x import Color  # Import here to avoid NameError if strip is None

    t = time.time()
    for y in range(5):
        for x in range(5):
            idx = y * 5 + x
            color = get_led_color(y, x, t, matrix)
            if color:
                r, g, b = color
                strip.setPixelColor(idx, Color(r, g, b))
            else:
                strip.setPixelColor(idx, Color(0, 0, 0))
    strip.show()

def draw_help_screen():
    screen.fill(BG_COLOR)
    title = big_font.render("5x5 Binary Nerd Clock - Help", True, (200, 200, 200))
    title_rect = title.get_rect(centerx=WIDTH//2, top=50)
    screen.blit(title, title_rect)

    help_lines = [
        "C          - Cycle Standard colors (white, green, red, ...)",
        "F          - Cycle Festive themes (rainbow, christmas, newyears, ...)",
        "D          - Change count direction (up / down)",
        "S          - Toggle Status line (on / off)",
        "L          - Toggle LED shape (circle / square / triangle / star / x)",
        "O          - Cycle bit Order (normal / reverse / transpose)",
        "+          - Increase brightness",
        "-          - Decrease brightness",
        "H or F1    - Show / hide this Help screen",
        "Esc / Q    - Quit the clock",
    ]

    total_lines = len(help_lines)
    line_height = font_size + 10
    block_height = total_lines * line_height
    start_y = (HEIGHT - block_height) // 2
    column_left = WIDTH // 5

    y_pos = start_y
    for line in help_lines:
        surf = font.render(line, True, (180, 180, 180))
        rect = surf.get_rect(left=column_left, top=y_pos)
        screen.blit(surf, rect)
        y_pos += line_height

    hint = font.render("Press H, F1 or Esc to return to clock", True, (100, 100, 100))
    hint_rect = hint.get_rect(centerx=WIDTH//2, bottom=HEIGHT - 50)
    screen.blit(hint, hint_rect)

    pygame.display.flip()
    if strip:
        from rpi_ws281x import Color
        for i in range(25):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()

def draw_grid(matrix, seconds_value):
    t = time.time()

    effective_mode = get_effective_color_mode()
    text_color = get_status_text_color(t, matrix)

    screen.fill(BG_COLOR)

    radius = CELL_SIZE // 2 - 10

    for y in range(5):
        for x in range(5):
            color = get_led_color(y, x, t, matrix) if matrix[y][x] else OFF_COLOR
            center = (GRID_X + x * CELL_SIZE + CELL_SIZE // 2,
                      GRID_Y + y * CELL_SIZE + CELL_SIZE // 2)
            draw_led(center[0], center[1], color, radius)

    if time.time() < settings_show_end:
        display_mode = COLOR_MODE if COLOR_MODE != 'automatic' else f"auto ({effective_mode})"
        settings_text = (f"Color: {display_mode} | Direction: {COUNT_DIRECTION} | Status: {'On' if SHOW_STATUS else 'Off'} | "
                         f"Shape: {LED_SHAPE.capitalize()} | Order: {BIT_ORDER} | Bright: {BRIGHTNESS:.1f}")
        surf = font.render(settings_text, True, SETTINGS_TEXT_COLOR)
        rect = surf.get_rect(centerx=WIDTH//2, top=10)
        screen.blit(surf, rect)

    if SHOW_STATUS:
        now_utc = datetime.datetime.now(datetime.UTC)
        now_local = datetime.datetime.now()
        tz_name = time_mod.strftime("%Z", time_mod.localtime())
        binary_str = format(seconds_value, '025b')
        utc_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        local_str = now_local.strftime("%Y-%m-%d %I:%M:%S %p ") + f" {tz_name}".strip()
        label = "Remaining" if COUNT_DIRECTION == 'down' else "Elapsed"
        bottom_text = f"{label}: {seconds_value} (0b{binary_str}) | {utc_str} | {local_str}"
        surf = font.render(bottom_text, True, text_color)
        rect = surf.get_rect(centerx=WIDTH//2, bottom=HEIGHT - 10)
        screen.blit(surf, rect)

    pygame.display.flip()
    update_physical_leds(matrix)

def run_clock():
    global config_dirty, COLOR_MODE, COUNT_DIRECTION, SHOW_STATUS, LED_SHAPE, BIT_ORDER, BRIGHTNESS
    global settings_show_end, current_second, show_help

    clock = pygame.time.Clock()
    seconds_value = get_seconds_value()
    matrix = binary_to_5x5(format(seconds_value, '025b'))
    led_init_time = time.time() + 3.0

    last_change_time = 0.0
    need_redraw = True

    while True:
        current_time = time.time()

        if current_time > led_init_time:
            init_physical_leds()
            led_init_time = float('inf')
            need_redraw = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if config_dirty:
                    save_config()
                return

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    if show_help:
                        show_help = False
                        need_redraw = True
                    else:
                        if config_dirty:
                            save_config()
                        return

                if show_help:
                    if event.key in (pygame.K_h, pygame.K_F1):
                        show_help = False
                        need_redraw = True
                    continue

                changed = False

                if event.key == pygame.K_c:
                    current_standard = [m.lower() for m in STANDARD_MODES]
                    if COLOR_MODE.lower() in current_standard:
                        idx = current_standard.index(COLOR_MODE.lower())
                        COLOR_MODE = STANDARD_MODES[(idx + 1) % len(STANDARD_MODES)]
                    else:
                        COLOR_MODE = STANDARD_MODES[0]
                    changed = True

                elif event.key == pygame.K_f:
                    current_festive = [m.lower() for m in FESTIVE_MODES]
                    if COLOR_MODE.lower() in current_festive:
                        idx = current_festive.index(COLOR_MODE.lower())
                        COLOR_MODE = FESTIVE_MODES[(idx + 1) % len(FESTIVE_MODES)]
                    else:
                        COLOR_MODE = FESTIVE_MODES[0]
                    changed = True

                elif event.key in (pygame.K_h, pygame.K_F1):
                    show_help = True
                    need_redraw = True
                    continue

                elif event.key == pygame.K_d:
                    COUNT_DIRECTION = 'up' if COUNT_DIRECTION == 'down' else 'down'
                    changed = True
                elif event.key == pygame.K_s:
                    SHOW_STATUS = not SHOW_STATUS
                    changed = True
                elif event.key == pygame.K_l:
                    idx = shape_modes.index(LED_SHAPE)
                    LED_SHAPE = shape_modes[(idx + 1) % len(shape_modes)]
                    changed = True
                elif event.key == pygame.K_o:
                    order_list = ['normal', 'reverse', 'transpose']
                    idx = order_list.index(BIT_ORDER)
                    BIT_ORDER = order_list[(idx + 1) % 3]
                    changed = True
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    BRIGHTNESS = min(1.0, BRIGHTNESS + 0.1)
                    if strip:
                        strip.setBrightness(int(255 * BRIGHTNESS))
                    changed = True
                elif event.key == pygame.K_MINUS:
                    BRIGHTNESS = max(0.2, BRIGHTNESS - 0.1)
                    if strip:
                        strip.setBrightness(int(255 * BRIGHTNESS))
                    changed = True

                if changed:
                    config_dirty = True
                    last_change_time = time.time()
                    settings_show_end = time.time() + 8.0
                    need_redraw = True

        if config_dirty and current_time >= last_change_time + 5:
            save_config()

        if check_and_reload_config():
            need_redraw = True

        if int(current_time) > current_second:
            current_second = int(current_time)
            seconds_value = get_seconds_value()
            matrix = binary_to_5x5(format(seconds_value, '025b'))
            need_redraw = True

        if need_redraw or (not show_help and is_animated()):
            if show_help:
                draw_help_screen()
            else:
                draw_grid(matrix, seconds_value)
            need_redraw = False

        clock.tick(60)

    if config_dirty:
        save_config()

if __name__ == "__main__":
    print("Classic 5x5 Binary Nerd Clock starting!")
    print("\nCredits: Crafted in collaboration with Grok by xAI and the remarkable visionary Prophet6")
    run_clock()
    pygame.quit()