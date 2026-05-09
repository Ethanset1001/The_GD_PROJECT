# version 1

from pathlib import Path
import gmdkit
import tkinter as tk
import math

# 1. DATA LOADING
data = Path("level.gmd").read_text(errors="ignore")
lvl = None

if hasattr(gmdkit, "parse_level"):
    lvl = gmdkit.parse_level(data)
elif hasattr(gmdkit, "load_level"):
    lvl = gmdkit.load_level(data)
elif hasattr(gmdkit, "decode"):
    lvl = gmdkit.decode(data)
elif hasattr(gmdkit, "Level"):
    try: lvl = gmdkit.Level.from_string(data)
    except: lvl = None

if lvl is None:
    raise SystemExit

# 2. SETUP
root = tk.Tk()
root.title("GMD Runner - Precision Spike Hitbox")
cw, ch = 900, 500
c = tk.Canvas(root, width=cw, height=ch, bg="#287DFF", highlightthickness=0)
c.pack()

def gv(o, k):
    try: return o[k]
    except: return getattr(o, k, None)

objs = getattr(lvl, "objects", [])

# 3. GAME STATE
GRID = 30
spawn_off = 300 
px = -spawn_off
py = 300
vx, vy = 0, 0
w, h = 30, 30
rot = 0 

# DO NOT TOUCH THESE. THESE ARE ACCURATE GD PHYSICS. well kinda accurate ya
spd = 6.6        
g = 1.08          
jmp = -12.65     
terminal_v = 18        

ong = False
camx = 0

def aabb(x1, y1, w1, h1, x2, y2, w2, h2):
    return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2

def rotate_point(cx, cy, angle, px, py):
    s = math.sin(math.radians(angle))
    c = math.cos(math.radians(angle))
    px -= cx
    py -= cy
    return (px * c - py * s) + cx, (px * s + py * c) + cy

# 4. GAME LOOP
def update():
    global px, py, vx, vy, ong, camx, rot

    px += spd
    camx = px - 200 

    vy += g
    if vy > terminal_v: vy = terminal_v
    py += vy
    
    ong = False

    # Floor Collision
    if py > ch - h:
        py = ch - h
        vy = 0
        ong = True

    # Hitbox Constants
    inner_size = 30 / 2.5
    inner_off = (30 - inner_size) / 2
    
    # Spike Hitbox Constants (12x16)
    shw, shh = 12, 16
    shx_off = (30 - shw) / 2
    shy_off = 30 - shh # Anchored to the bottom of the grid cell

    for o in objs:
        oid, ox, oy = gv(o, 1), gv(o, 2), gv(o, 3)
        if ox is None or oy is None: continue

        bx, by = ox - (GRID / 2), (ch - oy) - (GRID / 2) 

        # BLOCK LOGIC
        if oid == 1:
            if aabb(px, py, w, h, bx, by, GRID, GRID):
                if vy >= 0 and (py + h - vy) <= by + 15:
                    py = by - h
                    vy = 0
                    ong = True
                elif aabb(px + inner_off, py + inner_off, inner_size, inner_size, bx, by, GRID, GRID):
                    root.destroy()
                    return

        # SPIKE LOGIC (12x16 Hitbox)
        elif oid == 8:
            # We check the player's full 30x30 spike hitbox against the 12x16 spike zone
            if aabb(px, py, w, h, bx + shx_off, by + shy_off, shw, shh):
                root.destroy()
                return

    if not ong:
        rot += 8  
    else:
        rot = (round(rot / 90) * 90) % 360

    draw()
    root.after(16, update) 

# 5. RENDERING
def draw():
    c.delete("all")
    sxp = px - camx
    cx, cy = sxp + w/2, py + h/2

    # Player Cube
    p1 = rotate_point(cx, cy, rot, sxp, py)
    p2 = rotate_point(cx, cy, rot, sxp + w, py)
    p3 = rotate_point(cx, cy, rot, sxp + w, py + h)
    p4 = rotate_point(cx, cy, rot, sxp, py + h)
    c.create_polygon(p1, p2, p3, p4, fill="cyan", outline="white", width=1)

    # DEBUG: Player Hitboxes
    # Hazard Hitbox (Blue)
    c.create_rectangle(sxp, py, sxp + w, py + h, outline="blue")
    # Block Hitbox (Yellow)
    inner_size = 30 / 2.5
    io = (30 - inner_size) / 2
    c.create_rectangle(sxp + io, py + io, sxp + io + inner_size, py + io + inner_size, outline="yellow")

    for o in objs:
        oid, ox, oy = gv(o, 1), gv(o, 2), gv(o, 3)
        if ox is None or oy is None: continue
        sx, sy = (ox - GRID/2) - camx, (ch - oy) - GRID/2

        if -GRID < sx < cw:
            if oid == 1:
                c.create_rectangle(sx, sy, sx + GRID, sy + GRID, fill="grey", outline="white")
            elif oid == 8:
                # Spike visual
                c.create_polygon(sx, sy+GRID, sx+GRID/2, sy, sx+GRID, sy+GRID, fill="grey")
                # Spike Hitbox (Red - 12x16 centered)
                shw, shh = 12, 16
                shx_off = (30 - shw) / 2
                shy_off = 30 - shh
                c.create_rectangle(sx + shx_off, sy + shy_off, sx + shx_off + shw, sy + shy_off + shh, outline="red")

# 6. INPUT
def jump(e):
    global vy
    if ong:
        vy = jmp
root.bind("<space>", jump)

update()
root.mainloop()
