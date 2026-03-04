import pygame
import random
import heapq
import time


# ---------------- 配置参数 ----------------
IMG_FILE = "XXX.jpg"   # 请确保是 512x512
SIZE = 128                # 每块大小 (512/4)
N = 4                     # 4x4 拼图
WIDTH, HEIGHT = SIZE * N, SIZE * N + 60  # 底部留空间放按钮
FPS = 60
SHUFFLE_MOVES = 80        # 打乱步数（越多越难/越慢）

# -----------------------------------------

# 目标状态 (tuple)
GOAL = tuple(list(range(1, N*N)) + [0])  # 1..15,0

# ---------------- 状态与 AI 算法 ----------------
def manhattan(state):
    """曼哈顿距离启发函数：单块到目标位置的水平+垂直距离之和"""
    dist = 0
    for idx, v in enumerate(state):
        if v == 0:
            continue
        goal_idx = v - 1
        x1, y1 = idx % N, idx // N
        x2, y2 = goal_idx % N, goal_idx // N
        dist += abs(x1 - x2) + abs(y1 - y2)
    return dist

def neighbors(state):
    """产生所有合法相邻状态及移动方向"""
    zero = state.index(0)
    zx, zy = zero % N, zero // N
    moves = []
    for dx, dy, action in ((0,-1,'U'), (0,1,'D'), (-1,0,'L'), (1,0,'R')):
        nx, ny = zx + dx, zy + dy
        if 0 <= nx < N and 0 <= ny < N:
            npos = ny * N + nx
            s = list(state)
            s[zero], s[npos] = s[npos], s[zero]
            moves.append((tuple(s), action))
    return moves

def a_star(start, max_nodes=500000):
    """AI搜索，返回从 start 到 GOAL 的动作序列（如 ['L','U',...]），若找不到返回 None
       为了防止爆炸，max_nodes限制扩展节点数量（默认为500k，可以根据需要调整）"""
    if start == GOAL:
        return []

    open_heap = []
    gscore = {start: 0}
    fscore = manhattan(start)
    heapq.heappush(open_heap, (fscore, 0, start))
    came_from = {}
    visited = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        visited += 1
        if visited > max_nodes:
            return None
        if current == GOAL:
            # 重建路径
            path = []
            cur = current
            while cur in came_from:
                cur, act = came_from[cur]
                path.append(act)
            return list(reversed(path))
        gcur = gscore[current]
        for nb, action in neighbors(current):
            tentative = gcur + 1
            if nb not in gscore or tentative < gscore[nb]:
                gscore[nb] = tentative
                f = tentative + manhattan(nb)
                heapq.heappush(open_heap, (f, -tentative, nb))  # -tentative使得g大的先出以稳定
                came_from[nb] = (current, action)
    return None

def random_solvable_state(shuffle_moves=SHUFFLE_MOVES):
    """通过从目标状态做随机合法移动若干步来生成可解初始状态（保证可解）"""
    state = list(GOAL)
    zero_pos = state.index(0)
    for _ in range(shuffle_moves):
        zx, zy = zero_pos % N, zero_pos // N
        choices = []
        for dx, dy in ((0,-1),(0,1),(-1,0),(1,0)):
            nx, ny = zx + dx, zy + dy
            if 0 <= nx < N and 0 <= ny < N:
                choices.append(ny*N + nx)
        nxt = random.choice(choices)
        state[zero_pos], state[nxt] = state[nxt], state[zero_pos]
        zero_pos = nxt
    return tuple(state)

# ---------------- Pygame UI ----------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("15-Puzzle with AI (Hint/Auto)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("SimHei", 24)
font_big = pygame.font.SysFont("SimHei", 40)

# 加载并分割图片
try:
    full_img = pygame.image.load(IMG_FILE).convert()
except Exception as e:
    raise SystemExit(f"无法加载图片 {IMG_FILE}。请确认有个 512x512 的图片并命名为 {IMG_FILE}. 错误: {e}")

# 确保图片大小
if full_img.get_width() != SIZE*N or full_img.get_height() != SIZE*N:
    full_img = pygame.transform.scale(full_img, (SIZE*N, SIZE*N))

tiles_img = []
for y in range(N):
    for x in range(N):
        rect = pygame.Rect(x*SIZE, y*SIZE, SIZE, SIZE)
        sub = full_img.subsurface(rect).copy()
        tiles_img.append(sub)
# 最后一块作为空白（不绘制）
tiles_img[ -1 ] = None

# 初始拼图（从目标开始）
current_state = GOAL
auto_moves = []      # AI 求解得到的动作序列（如 ['L','U',...])，用于 Auto 播放
auto_index = 0
auto_mode = False
show_success = False
last_solved_time = 0

# 在底部绘制按钮
class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text
    def draw(self, surf):
        pygame.draw.rect(surf, (200,200,200), self.rect)
        pygame.draw.rect(surf, (50,50,50), self.rect, 2)
        txt = font.render(self.text, True, (10,10,10))
        surf.blit(txt, (self.rect.x + 8, self.rect.y + 6))
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

btn_start = Button((10, HEIGHT-50, 80, 36), "Start")
btn_hint  = Button((190, HEIGHT-50, 80, 36), "Hint")


# 绘制当前拼图
def draw_state(state):
    screen.fill((245,245,245))
    for idx, val in enumerate(state):
        x, y = idx % N, idx // N
        rx, ry = x*SIZE, y*SIZE
        if val == 0:
            # 空白块，画白背景
            pygame.draw.rect(screen, (240,240,240), (rx, ry, SIZE, SIZE))
            pygame.draw.rect(screen, (200,200,200), (rx, ry, SIZE, SIZE), 1)
        else:
            img = tiles_img[val-1]
            screen.blit(img, (rx, ry))
    # 网格线
    for i in range(N+1):
        pygame.draw.line(screen, (180,180,180), (i*SIZE,0), (i*SIZE, SIZE*N))
        pygame.draw.line(screen, (180,180,180), (0,i*SIZE), (SIZE*N, i*SIZE))
    # 按钮
    btn_start.draw(screen)
    btn_hint.draw(screen)
    # 状态提示
    if show_success:
        screen.blit(font_big.render("Success!", True, (10,120,10)), (WIDTH-170, HEIGHT-48))
    pygame.display.flip()

# 操作 state，按 action 移动（action 是 'L','R','U','D' —— 表示空格与哪个方向的块交换）
def apply_action(state, action):
    s = list(state)
    zero = s.index(0)
    zx, zy = zero % N, zero // N
    if action == 'L':
        nx, ny = zx - 1, zy
    elif action == 'R':
        nx, ny = zx + 1, zy
    elif action == 'U':
        nx, ny = zx, zy - 1
    elif action == 'D':
        nx, ny = zx, zy + 1
    else:
        return state
    if 0 <= nx < N and 0 <= ny < N:
        pos = ny * N + nx
        s[zero], s[pos] = s[pos], s[zero]
    return tuple(s)

# 根据鼠标点击的格子移动（如果格子在空格可达的4邻域）
def click_move(state, mouse_pos):
    mx, my = mouse_pos
    if mx < 0 or mx >= SIZE*N or my < 0 or my >= SIZE*N:
        return state
    gx, gy = mx // SIZE, my // SIZE
    pos = gy*N + gx
    zero = state.index(0)
    zx, zy = zero % N, zero // N
    # 如果点击的是与空格相邻的格子就交换
    if abs(zx - gx) + abs(zy - gy) == 1:
        s = list(state)
        s[zero], s[pos] = s[pos], s[zero]
        return tuple(s)
    return state

# ---------------- 主循环 ----------------
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx,my = event.pos
            # 点击按钮区域优先
            if btn_start.is_clicked((mx,my)):
                # start: 打乱并退出 auto 模式
                current_state = random_solvable_state()
                auto_mode = False
                auto_moves = []
                show_success = False

            elif btn_hint.is_clicked((mx,my)):
                # 计算 AI ，并且只取第一步显示
                sol = a_star(current_state, max_nodes=500000)
                if sol:
                    # 执行第一步作为提示（不改变 state ，而是绘制高亮? 简单起见直接执行一步）
                    # 我们不直接执行改变 state，而是将其作为 ephemeral: 这里直接执行一步
                    current_state = apply_action(current_state, sol[0])
                    show_success = (current_state == GOAL)
                else:
                    print("Hint: AI 未找到解（可能超时或节点数受限）")
            else:
                # 点击地图移动
                prev = current_state
                current_state = click_move(current_state, (mx,my))
                if current_state != prev:
                    show_success = (current_state == GOAL)
                    auto_mode = False
                    auto_moves = []
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # space 当作 Start（打乱）
                current_state = random_solvable_state()
                auto_mode = False
                auto_moves = []
                show_success = False
            # 方向键移动空格（以空格为中心的移动）
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                action = None
                if event.key == pygame.K_LEFT: action = 'L'
                if event.key == pygame.K_RIGHT: action = 'R'
                if event.key == pygame.K_UP: action = 'U'
                if event.key == pygame.K_DOWN: action = 'D'
                if action:
                    current_state = apply_action(current_state, action)
                    show_success = (current_state == GOAL)
                    auto_mode = False
                    auto_moves = []

    draw_state(current_state)
pygame.quit()
