from pathlib import Path
import gmdkit
import tkinter as tk
import math
import time

# 1. DATA LOADING
data = Path("level.gmd").read_text(errors="ignore")
lvl = None

for method in ["parse_level", "load_level", "decode"]:
    if hasattr(gmdkit, method):
        lvl = getattr(gmdkit, method)(data)
        break
if lvl is None and hasattr(gmdkit, "Level"):
    try: lvl = gmdkit.Level.from_string(data)
    except: pass

if lvl is None:
    raise SystemExit

# 2. SETUP
root = tk.Tk()
root.title("GMD Runner - 1 Orb Per Click")
cw, ch = 900, 500
c = tk.Canvas(root, width=cw, height=ch, bg="#287DFF", highlightthickness=0)
c.pack()

def gv(o, k):
    try: return o[k]
    except: return getattr(o, k, None)

objs = getattr(lvl, "objects", [])

# 3. GAME STATE
GRID = 30
SPAWN_X, SPAWN_Y = -300, 300
px, py = SPAWN_X, SPAWN_Y
vx, vy = 0, 0
w, h = 30, 30
rot, camx = 0, 0
ong, pressing, dead = False, False, False
gravity_dir = 1 
last_orb_id = -1 
click_used_for_orb = False # THE FIX: Tracks if the current held click already popped an orb

# PHYSICS
spd = 5.5        
base_g = 1.05          
jmp_power = -11.65     
terminal_v = 18   

BLOCK_IDS = {1, 2, 3, 4, 6, 7, 63, 69, 70, 71, 72, 74, 75}
SPIKE_IDS = {8, 9}
SMALL_SPIKE_ID = 39
ORB_YELLOW = 36
ORB_BLUE = 84

last_frame_time = time.time()

def respawn():
    global px, py, vy, rot, camx, ong, dead, gravity_dir, last_orb_id, click_used_for_orb
    px, py, vy, rot, dead, gravity_dir = SPAWN_X, SPAWN_Y, 0, 0, False, 1
    last_orb_id = -1
    click_used_for_orb = False
    camx = px - 200

def trigger_death():
    global dead
    if not dead:
        dead = True
        root.after(400, respawn)

# 4. GAME LOOP
def update():
    global px, py, vy, ong, camx, rot, last_frame_time, gravity_dir, last_orb_id, click_used_for_orb

    current_time = time.time()
    elapsed = current_time - last_frame_time
    
    if elapsed >= 0.016:
        last_frame_time = current_time

        if not dead:
            if pressing and ong:
                vy = jmp_power * gravity_dir
                # Jumping on ground doesn't count as an orb use, but we reset it for safety
                click_used_for_orb = False 

            px += spd
            camx = px - 200 
            
            vy += (base_g * gravity_dir)
            if abs(vy) > terminal_v: vy = terminal_v * (1 if vy > 0 else -1)
            py += vy
            
            ong = False
            if gravity_dir == 1 and py > ch - h:
                py, vy, ong = ch - h, 0, True
                click_used_for_orb = False # Reset when landing
            elif gravity_dir == -1 and py < 0:
                py, vy, ong = 0, 0, True
                click_used_for_orb = False

            orb_touched_this_frame = False
            io, is_ = 9, 12 

            for o in objs:
                oid, ox, oy = gv(o, 1), gv(o, 2), gv(o, 3)
                if ox is None or oy is None: continue
                bx, by = ox - 15, (ch - oy) - 15

                if abs(px - bx) > 60: continue

                if oid in BLOCK_IDS:
                    if px < bx + 30 and px + 30 > bx and py < by + 30 and py + 30 > by:
                        is_falling = (gravity_dir == 1 and vy >= 0) or (gravity_dir == -1 and vy <= 0)
                        feet_y = (py + 30) if gravity_dir == 1 else py
                        prev_feet_y = (feet_y - vy)
                        
                        if is_falling and ((gravity_dir == 1 and prev_feet_y <= by + 12) or 
                                           (gravity_dir == -1 and prev_feet_y >= by + 18)):
                            py = (by - 30) if gravity_dir == 1 else (by + 30)
                            vy, ong = 0, True
                            click_used_for_orb = False
                        else:
                            if (px + io < bx + 30 and px + io + is_ > bx and 
                                py + io < by + 30 and py + io + is_ > by):
                                if (gravity_dir == 1 and vy < 0) or (gravity_dir == -1 and vy > 0):
                                    py = (by + 30 - io) if gravity_dir == 1 else (by - is_ - io)
                                    vy = 0
                                else:
                                    trigger_death()
                
                elif oid in SPIKE_IDS:
                    if px < bx + 19 and px + 11 > bx and py < by + 26 and py + 14 > by:
                        trigger_death()
                elif oid == SMALL_SPIKE_ID:
                    if px < bx + 19 and px + 11 > bx and py < by + 22.5 and py + 16.5 > by:
                        trigger_death()

                # ORB LOGIC
                elif oid in {ORB_YELLOW, ORB_BLUE}:
                    dist = math.sqrt((px+15 - (bx+15))**2 + (py+15 - (by+15))**2)
                    if dist < 25:
                        orb_touched_this_frame = True
                        # NEW CHECK: Must be pressing AND the click must not be "spent" yet
                        if pressing and not click_used_for_orb and id(o) != last_orb_id:
                            last_orb_id = id(o)
                            click_used_for_orb = True # Spend the click
                            
                            if oid == ORB_YELLOW:
                                vy = -11.5 * gravity_dir 
                            elif oid == ORB_BLUE:
                                gravity_dir *= -1
                                vy = 0 
            
            if not orb_touched_this_frame: last_orb_id = -1

            if not ong: rot += 8 * gravity_dir
            else: rot = (round(rot / 90) * 90) % 360

        draw()

    root.after(1, update) 

# 5. RENDERING
def rotate_point(cx, cy, angle, px, py):
    s, c_val = math.sin(math.radians(angle)), math.cos(math.radians(angle))
    px, py = px - cx, py - cy
    return (px * c_val - py * s) + cx, (px * s + py * c_val) + cy

def draw():
    c.delete("all")
    sxp = px - camx
    cx, cy = sxp + 15, py + 15
    p_color = "red" if dead else "cyan"
    
    p = [rotate_point(cx, cy, rot, sxp + dx, py + dy) for dx, dy in [(0,0), (30,0), (30,30), (0,30)]]
    c.create_polygon(p, fill=p_color, outline="white")
    
    for o in objs:
        oid, ox, oy = gv(o, 1), gv(o, 2), gv(o, 3)
        if ox is None or oy is None: continue
        sx, sy = (ox - 15) - camx, (ch - oy) - 15
        if -30 < sx < cw:
            if oid in BLOCK_IDS:
                c.create_rectangle(sx, sy, sx+30, sy+30, fill="grey", outline="white")
            elif oid in SPIKE_IDS:
                c.create_polygon(sx, sy+30, sx+15, sy, sx+30, sy+30, fill="grey")
            elif oid == SMALL_SPIKE_ID:
                c.create_polygon(sx, sy+22.5, sx+15, sy+7.5, sx+30, sy+22.5, fill="grey")
            elif oid == ORB_YELLOW:
                c.create_oval(sx+5, sy+5, sx+25, sy+25, outline="yellow", width=2)
            elif oid == ORB_BLUE:
                c.create_oval(sx+5, sy+5, sx+25, sy+25, outline="#00A2FF", width=2)

# 6. INPUT
def p_dn(e): global pressing; pressing = True
def p_up(e): 
    global pressing, click_used_for_orb
    pressing = False
    click_used_for_orb = False # Release to refresh the click

root.bind("<Button-1>", p_dn); root.bind("<ButtonRelease-1>", p_up)
root.bind("<KeyPress-space>", p_dn); root.bind("<KeyRelease-space>", p_up)

update()
root.mainloop()
