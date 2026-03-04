#!/usr/bin/env python3
"""
================================================================
  DigiPlace — 数字IC自动布局工具
================================================================
  面向数字IC后端物理设计的自动布局引擎

  ● 模拟退火(SA)全局布局 —— HPWL优化目标
  ● Tetris合法化 —— 消除单元重叠, 行对齐
  ● Matplotlib可视化 —— 多视图布局展示

  依赖: numpy, matplotlib
  运行: python digiplace.py
================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
import math
import copy
import time
import colorsys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set

# ╔══════════════════════════════════════════════════════════════╗
# ║                    一、基础数据结构                          ║
# ╚══════════════════════════════════════════════════════════════╝

@dataclass
class Pin:
    """引脚: 属于某个 Cell, 有局部偏移量"""
    cell_id: int
    x_offset: float = 0.0
    y_offset: float = 0.0


@dataclass
class Cell:
    """标准单元 / IO Pad"""
    id: int
    name: str
    width: float
    height: float
    x: float = 0.0          # 左下角 x
    y: float = 0.0          # 左下角 y
    fixed: bool = False
    is_pad: bool = False
    row_id: int = -1

    # ---------- 几何便捷属性 ----------
    @property
    def cx(self) -> float:
        return self.x + self.width / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.height / 2.0

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height

    def overlaps(self, other: 'Cell') -> bool:
        """检测两个单元是否存在重叠"""
        return not (self.x >= other.right or other.x >= self.right or
                    self.y >= other.top  or other.y >= self.top)

    def overlap_area(self, other: 'Cell') -> float:
        """计算重叠面积"""
        dx = min(self.right, other.right) - max(self.x, other.x)
        dy = min(self.top,   other.top)   - max(self.y, other.y)
        return max(dx, 0.0) * max(dy, 0.0)


@dataclass
class Net:
    """线网: 连接若干 Pin"""
    id: int
    name: str
    pins: List[Pin] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class Row:
    """布局行"""
    id: int
    y: float             # 行底部 y 坐标
    x_start: float       # 行左边界
    x_end: float         # 行右边界
    height: float        # 行高
    site_width: float = 1.0

    @property
    def usable_width(self) -> float:
        return self.x_end - self.x_start


class Circuit:
    """电路/芯片数据容器"""

    def __init__(self):
        self.cells: Dict[int, Cell] = {}
        self.nets: List[Net] = []
        self.rows: List[Row] = []
        self.chip_width: float = 0.0
        self.chip_height: float = 0.0
        self.row_height: float = 0.0
        self.name: str = "circuit"

    def add_cell(self, cell: Cell):
        self.cells[cell.id] = cell

    def add_net(self, net: Net):
        self.nets.append(net)

    def movable_cells(self) -> List[Cell]:
        return [c for c in self.cells.values() if not c.fixed and not c.is_pad]

    def total_cell_area(self) -> float:
        return sum(c.width * c.height for c in self.cells.values() if not c.is_pad)


# ╔══════════════════════════════════════════════════════════════╗
# ║                    二、HPWL 计算器                          ║
# ╚══════════════════════════════════════════════════════════════╝

class HPWLCalculator:
    """半周线长 (Half-Perimeter Wire Length) 计算"""

    @staticmethod
    def net_hpwl(net: Net, cells: Dict[int, Cell]) -> float:
        if len(net.pins) < 2:
            return 0.0
        xs, ys = [], []
        for pin in net.pins:
            c = cells[pin.cell_id]
            xs.append(c.x + pin.x_offset)
            ys.append(c.y + pin.y_offset)
        return net.weight * ((max(xs) - min(xs)) + (max(ys) - min(ys)))

    @staticmethod
    def total_hpwl(nets: List[Net], cells: Dict[int, Cell]) -> float:
        return sum(HPWLCalculator.net_hpwl(n, cells) for n in nets)


# ╔══════════════════════════════════════════════════════════════╗
# ║                   三、基准电路生成器                         ║
# ╚══════════════════════════════════════════════════════════════╝

class BenchmarkGenerator:
    """
    自动生成随机基准电路 (标准单元 + IO Pad + 线网)
    用于算法验证与演示
    """

    @staticmethod
    def generate(num_cells: int = 200,
                 num_nets: int = 300,
                 num_pads: int = 20,
                 avg_fanout: int = 4,
                 utilization: float = 0.60,
                 row_height: float = 10.0,
                 site_width: float = 1.0,
                 seed: int = 42) -> Circuit:
        random.seed(seed)
        np.random.seed(seed)

        ckt = Circuit()
        ckt.row_height = row_height
        ckt.name = f"bench_{num_cells}c_{num_nets}n"

        # --- 1. 生成标准单元 (宽度为 site_width 整数倍) ---
        widths = []
        for i in range(num_cells):
            w = site_width * random.choice([2, 3, 4, 5, 6, 7, 8])
            ckt.add_cell(Cell(id=i, name=f"U{i}", width=w, height=row_height))
            widths.append(w)

        # --- 2. 根据利用率推导芯片尺寸 ---
        total_area = sum(w * row_height for w in widths)
        chip_area  = total_area / utilization
        ar = random.uniform(0.85, 1.15)
        chip_h = math.sqrt(chip_area / ar)
        chip_w = chip_area / chip_h

        n_rows = max(int(chip_h / row_height), 1)
        chip_h = n_rows * row_height
        chip_w = math.ceil(chip_w / site_width) * site_width

        ckt.chip_width  = chip_w
        ckt.chip_height = chip_h

        for r in range(n_rows):
            ckt.rows.append(Row(id=r, y=r * row_height,
                                x_start=0.0, x_end=chip_w,
                                height=row_height, site_width=site_width))

        # --- 3. 生成 IO Pad (固定在芯片四周) ---
        pid = num_cells
        for i in range(num_pads):
            side = i % 4
            pw, ph = site_width * 2, row_height
            if side == 0:   px, py = random.uniform(0, chip_w - pw), -ph
            elif side == 1: px, py = chip_w, random.uniform(0, chip_h - ph)
            elif side == 2: px, py = random.uniform(0, chip_w - pw), chip_h
            else:           px, py = -pw, random.uniform(0, chip_h - ph)
            ckt.add_cell(Cell(id=pid, name=f"P{i}", width=pw, height=ph,
                              x=px, y=py, fixed=True, is_pad=True))
            pid += 1

        # --- 4. 生成线网 ---
        all_cids = list(range(num_cells))
        all_pids = list(range(num_cells, num_cells + num_pads))

        for n in range(num_nets):
            npins = min(max(2, int(np.random.exponential(avg_fanout - 1)) + 1),
                        min(12, num_cells))
            net = Net(id=n, name=f"N{n}")

            # 有概率连接 IO Pad
            if random.random() < 0.3 and num_pads > 0:
                pad = ckt.cells[random.choice(all_pids)]
                net.pins.append(Pin(pad.id, pad.width / 2, pad.height / 2))

            chosen: Set[int] = set()
            for _ in range(npins * 3):
                if len(chosen) >= npins:
                    break
                cid = random.choice(all_cids)
                if cid not in chosen:
                    chosen.add(cid)
                    c = ckt.cells[cid]
                    net.pins.append(Pin(cid, random.uniform(0, c.width), c.height / 2))

            if len(net.pins) >= 2:
                ckt.add_net(net)

        # --- 打印摘要 ---
        print(f"{'='*60}")
        print(f"  [BenchmarkGenerator] 电路: {ckt.name}")
        print(f"  单元={num_cells}  线网={len(ckt.nets)}  Pad={num_pads}")
        print(f"  芯片 {chip_w:.0f} x {chip_h:.0f}  行={n_rows}  利用率={utilization*100:.0f}%")
        print(f"{'='*60}")
        return ckt


# ╔══════════════════════════════════════════════════════════════╗
# ║             四、模拟退火全局布局器 (SA Placer)               ║
# ╚══════════════════════════════════════════════════════════════╝

class SimulatedAnnealingPlacer:
    """
    经典模拟退火布局算法
    优化目标: 最小化总 HPWL
    扰动策略: 随机位移 + 单元交换
    增量计算加速
    """

    def __init__(self, circuit: Circuit, cfg: dict = None):
        self.ckt   = circuit
        self.cells = circuit.cells
        self.nets  = circuit.nets

        # --- 默认超参 ---
        default = dict(cooling_rate=0.95, max_iter=400, init_accept=0.95,
                       window_ratio=0.5, swap_prob=0.35,
                       moves_per_temp=None, seed=42, verbose=True)
        self.cfg = {**default, **(cfg or {})}
        random.seed(self.cfg['seed'])

        # 可移动单元 id 列表
        self.mov_ids = [c.id for c in circuit.movable_cells()]
        self.n_mov   = len(self.mov_ids)

        # cell -> 相关 net 索引的映射 (加速增量计算)
        self.c2n: Dict[int, List[int]] = {cid: [] for cid in self.cells}
        for i, net in enumerate(self.nets):
            for pin in net.pins:
                if pin.cell_id in self.c2n:
                    self.c2n[pin.cell_id].append(i)

        # 收敛记录
        self.cost_history: List[float] = []
        self.temp_history: List[float] = []
        self.best_cost = float('inf')
        self.best_pos: Dict[int, Tuple[float, float]] = {}

    # ---------- 初始化: 随机布局 ----------
    def random_initial_placement(self):
        W, H = self.ckt.chip_width, self.ckt.chip_height
        for cid in self.mov_ids:
            c = self.cells[cid]
            c.x = random.uniform(0, max(0.1, W - c.width))
            c.y = random.uniform(0, max(0.1, H - c.height))

    # ---------- 代价计算 ----------
    def _cost(self) -> float:
        return HPWLCalculator.total_hpwl(self.nets, self.cells)

    def _delta_move(self, cid: int, nx: float, ny: float) -> float:
        """增量: 移动 cid 到 (nx, ny) 时的 cost 变化量"""
        c = self.cells[cid]
        ox, oy = c.x, c.y
        delta = 0.0
        for ni in self.c2n[cid]:
            net = self.nets[ni]
            old_h = HPWLCalculator.net_hpwl(net, self.cells)
            c.x, c.y = nx, ny
            new_h = HPWLCalculator.net_hpwl(net, self.cells)
            c.x, c.y = ox, oy
            delta += (new_h - old_h)
        return delta

    def _delta_swap(self, id1: int, id2: int) -> float:
        """增量: 交换 id1, id2 时的 cost 变化量"""
        c1, c2 = self.cells[id1], self.cells[id2]
        related = set(self.c2n[id1]) | set(self.c2n[id2])
        ox1, oy1, ox2, oy2 = c1.x, c1.y, c2.x, c2.y
        delta = 0.0
        for ni in related:
            net = self.nets[ni]
            old_h = HPWLCalculator.net_hpwl(net, self.cells)
            c1.x, c1.y, c2.x, c2.y = ox2, oy2, ox1, oy1
            new_h = HPWLCalculator.net_hpwl(net, self.cells)
            c1.x, c1.y, c2.x, c2.y = ox1, oy1, ox2, oy2
            delta += (new_h - old_h)
        return delta

    # ---------- 温度校准 ----------
    def _calibrate_temp(self, n_sample: int = 800) -> float:
        W, H = self.ckt.chip_width, self.ckt.chip_height
        pos_deltas = []
        for _ in range(n_sample):
            cid = random.choice(self.mov_ids)
            c = self.cells[cid]
            nx = random.uniform(0, max(0.1, W - c.width))
            ny = random.uniform(0, max(0.1, H - c.height))
            d = self._delta_move(cid, nx, ny)
            if d > 0:
                pos_deltas.append(d)
        if not pos_deltas:
            return 1000.0
        avg = float(np.mean(pos_deltas))
        return max(-avg / math.log(self.cfg['init_accept']), 1.0)

    # ---------- 保存 / 恢复最优解 ----------
    def _save_best(self, cost: float):
        if cost < self.best_cost:
            self.best_cost = cost
            self.best_pos = {cid: (c.x, c.y) for cid, c in self.cells.items()}

    def _restore_best(self):
        for cid, (x, y) in self.best_pos.items():
            self.cells[cid].x, self.cells[cid].y = x, y

    # ---------- 主循环 ----------
    def optimize(self) -> float:
        """
        执行模拟退火优化 (从当前 cell 位置出发)
        Returns: 最终 HPWL
        """
        W, H = self.ckt.chip_width, self.ckt.chip_height
        alpha = self.cfg['cooling_rate']
        max_iter = self.cfg['max_iter']
        swap_p  = self.cfg['swap_prob']
        mpt = self.cfg['moves_per_temp'] or max(10 * self.n_mov, 500)

        cur_cost = self._cost()
        init_cost = cur_cost
        T = self._calibrate_temp()
        T_min = 1e-4
        T0 = T

        self._save_best(cur_cost)
        self.cost_history.append(cur_cost)
        self.temp_history.append(T)

        print(f"\n  ┌─ 模拟退火参数 ─────────────────────┐")
        print(f"  │ 初始HPWL   = {init_cost:>14.2f}       │")
        print(f"  │ 初始温度T₀ = {T:>14.2f}       │")
        print(f"  │ 冷却速率α  = {alpha:>14.4f}       │")
        print(f"  │ 每温度步数 = {mpt:>14d}       │")
        print(f"  │ 最大迭代   = {max_iter:>14d}       │")
        print(f"  │ 可移动单元 = {self.n_mov:>14d}       │")
        print(f"  └──────────────────────────────────┘\n")

        t0 = time.time()
        it = 0

        while T > T_min and it < max_iter:
            acc, imp = 0, 0
            # 窗口随温度收缩
            wr = self.cfg['window_ratio'] * math.sqrt(T / T0)
            wr = max(wr, 0.01)
            wx, wy = W * wr, H * wr

            for _ in range(mpt):
                if random.random() < swap_p and self.n_mov >= 2:
                    # ---- 交换 ----
                    id1, id2 = random.sample(self.mov_ids, 2)
                    delta = self._delta_swap(id1, id2)
                    if delta < 0 or (T > 0 and random.random() < math.exp(-delta / T)):
                        c1, c2 = self.cells[id1], self.cells[id2]
                        c1.x, c2.x = c2.x, c1.x
                        c1.y, c2.y = c2.y, c1.y
                        cur_cost += delta
                        acc += 1
                        if delta < 0: imp += 1
                else:
                    # ---- 位移 ----
                    cid = random.choice(self.mov_ids)
                    c = self.cells[cid]
                    nx = max(0, min(c.x + random.uniform(-wx, wx), W - c.width))
                    ny = max(0, min(c.y + random.uniform(-wy, wy), H - c.height))
                    delta = self._delta_move(cid, nx, ny)
                    if delta < 0 or (T > 0 and random.random() < math.exp(-delta / T)):
                        c.x, c.y = nx, ny
                        cur_cost += delta
                        acc += 1
                        if delta < 0: imp += 1

            self._save_best(cur_cost)
            self.cost_history.append(cur_cost)
            self.temp_history.append(T)

            ar = acc / mpt
            if self.cfg['verbose'] and it % 25 == 0:
                elapsed = time.time() - t0
                print(f"  iter {it:4d} │ T={T:10.3f} │ HPWL={cur_cost:11.1f} │ "
                      f"best={self.best_cost:11.1f} │ acc={ar:.3f} │ {elapsed:.1f}s")

            T *= alpha
            it += 1
            if ar < 0.001 and it > 60:
                print(f"  ⚠  接受率过低 ({ar:.4f}), 提前收敛")
                break

        self._restore_best()
        final = self._cost()
        pct = (1 - final / init_cost) * 100
        print(f"\n  ╔═══════════════════════════════════╗")
        print(f"  ║  SA 完成 — 迭代 {it} 次, {time.time()-t0:.1f}s   ")
        print(f"  ║  初始 HPWL = {init_cost:>12.1f}        ")
        print(f"  ║  最优 HPWL = {final:>12.1f}        ")
        print(f"  ║  改善       = {pct:>11.2f}%        ")
        print(f"  ╚═══════════════════════════════════╝\n")
        return final


# ╔══════════════════════════════════════════════════════════════╗
# ║                五、合法化器 (Legalizer)                      ║
# ╚══════════════════════════════════════════════════════════════╝

class TetrisLegalizer:
    """
    Tetris 风格合法化算法
    --------------------------------------------------
    将全局布局结果对齐到布局行, 消除所有单元重叠.
    1. 按 x 坐标排序 (从左到右处理)
    2. 对每个单元, 在所有行中寻找位移最小的合法位置
    3. 在行内 gap 中找到最近的空闲 x 坐标
    """

    def __init__(self, circuit: Circuit):
        self.ckt  = circuit
        self.cells = circuit.cells
        self.rows  = circuit.rows

    # ---------- 重叠统计 ----------
    def compute_overlap(self) -> Tuple[float, int]:
        movable = [c for c in self.cells.values() if not c.is_pad]
        total, cnt = 0.0, 0
        for i in range(len(movable)):
            for j in range(i + 1, len(movable)):
                a = movable[i].overlap_area(movable[j])
                if a > 0:
                    total += a
                    cnt += 1
        return total, cnt

    # ---------- 行内寻找合法 x ----------
    @staticmethod
    def _find_legal_x(occupied: List[Tuple[float, float]],
                      cell_w: float, target_x: float,
                      row_xs: float, row_xe: float,
                      site_w: float) -> Optional[float]:
        """在行的空隙中找到距 target_x 最近的合法 x"""
        if cell_w > (row_xe - row_xs):
            return None

        # 收集所有 gap
        gaps = []
        prev = row_xs
        for (a, b) in sorted(occupied):
            if prev < a:
                gaps.append((prev, a))
            prev = max(prev, b)
        if prev < row_xe:
            gaps.append((prev, row_xe))

        best_x, best_d = None, float('inf')
        for gs, ge in gaps:
            if (ge - gs) < cell_w - 1e-9:
                continue
            # 对齐到 site 栅格
            x_lo = math.ceil(gs / site_w) * site_w
            x_hi = ge - cell_w
            if x_lo > x_hi + 1e-9:
                continue
            lx = max(x_lo, min(target_x, x_hi))
            # 再次 snap
            lx = round(lx / site_w) * site_w
            lx = max(x_lo, min(lx, x_hi))
            d = abs(lx - target_x)
            if d < best_d:
                best_d, best_x = d, lx
        return best_x

    # ---------- 主合法化流程 ----------
    def legalize(self) -> float:
        print(f"\n{'='*60}")
        print(f"  Tetris 合法化 (Legalization)")
        print(f"{'='*60}")

        pre_ov, pre_cnt = self.compute_overlap()
        pre_hpwl = HPWLCalculator.total_hpwl(self.ckt.nets, self.cells)
        print(f"  合法化前 → 重叠面积={pre_ov:.1f}  重叠对={pre_cnt}  HPWL={pre_hpwl:.1f}")

        movable = [c for c in self.cells.values() if not c.is_pad and not c.fixed]
        movable.sort(key=lambda c: (c.x, c.y))

        # 每行已占用区间
        occ: Dict[int, List[Tuple[float, float]]] = {r.id: [] for r in self.rows}
        total_disp = 0.0
        failed = 0

        for cell in movable:
            ox, oy = cell.x, cell.y
            best_cost = float('inf')
            best_rid, best_x = -1, 0.0

            for row in self.rows:
                if cell.height > row.height + 1e-9:
                    continue
                lx = self._find_legal_x(occ[row.id], cell.width, ox,
                                         row.x_start, row.x_end, row.site_width)
                if lx is None:
                    continue
                cost = abs(lx - ox) + abs(row.y - oy)
                if cost < best_cost:
                    best_cost, best_rid, best_x = cost, row.id, lx

            if best_rid >= 0:
                cell.x = best_x
                cell.y = self.rows[best_rid].y
                cell.row_id = best_rid
                occ[best_rid].append((best_x, best_x + cell.width))
                occ[best_rid].sort()
                total_disp += best_cost
            else:
                failed += 1

        post_ov, post_cnt = self.compute_overlap()
        post_hpwl = HPWLCalculator.total_hpwl(self.ckt.nets, self.cells)
        hpwl_chg = (post_hpwl - pre_hpwl) / max(pre_hpwl, 1) * 100

        print(f"  合法化后 → 重叠面积={post_ov:.1f}  重叠对={post_cnt}  HPWL={post_hpwl:.1f}")
        print(f"  HPWL 变化 = {hpwl_chg:+.2f}%")
        print(f"  总位移 = {total_disp:.1f}   平均位移 = {total_disp/max(len(movable),1):.1f}")
        if failed:
            print(f"  ⚠  {failed} 个单元未能合法放置")
        print(f"{'='*60}\n")
        return total_disp


# ╔══════════════════════════════════════════════════════════════╗
# ║             六、可视化模块 (Visualizer)                      ║
# ╚══════════════════════════════════════════════════════════════╝

class PlacementVisualizer:
    """基于 Matplotlib 的多视图布局可视化"""

    def __init__(self, circuit: Circuit):
        self.ckt = circuit

    # ---------- 绘制布局 ----------
    def draw_placement(self, ax, title: str = "",
                       show_nets: bool = True,
                       highlight_overlap: bool = False,
                       show_labels: bool = False):
        W, H = self.ckt.chip_width, self.ckt.chip_height

        # 芯片边界
        ax.add_patch(patches.Rectangle((0, 0), W, H, lw=2,
                     ec='black', fc='#f5f5f0', zorder=0))

        # 行 (虚线)
        for row in self.ckt.rows:
            ax.add_patch(patches.Rectangle(
                (row.x_start, row.y), row.usable_width, row.height,
                lw=0.3, ec='#bbbbbb', fc='none', ls='--', zorder=1))

        # 检测重叠
        overlap_ids: Set[int] = set()
        if highlight_overlap:
            movable = [c for c in self.ckt.cells.values() if not c.is_pad]
            for i in range(len(movable)):
                for j in range(i + 1, len(movable)):
                    if movable[i].overlaps(movable[j]):
                        overlap_ids.update([movable[i].id, movable[j].id])

        # 线网
        if show_nets:
            self._draw_nets(ax)

        # 标准单元
        for c in self.ckt.cells.values():
            if c.is_pad:
                continue
            if c.id in overlap_ids:
                fc, ec, alpha, lw = '#ff4444', '#cc0000', 0.72, 1.2
            else:
                fc, ec, alpha, lw = '#4a90d9', '#2c5f8a', 0.55, 0.6
            ax.add_patch(patches.Rectangle(
                (c.x, c.y), c.width, c.height,
                lw=lw, ec=ec, fc=fc, alpha=alpha, zorder=3))
            if show_labels and c.width > W * 0.025:
                ax.text(c.cx, c.cy, c.name, ha='center', va='center',
                        fontsize=3.5, color='white', zorder=4)

        # IO Pad
        for c in self.ckt.cells.values():
            if c.is_pad:
                ax.add_patch(patches.Rectangle(
                    (c.x, c.y), c.width, c.height,
                    lw=0.8, ec='#228B22', fc='#90EE90', alpha=0.85, zorder=3))

        m = max(W, H) * 0.07
        ax.set_xlim(-m, W + m)
        ax.set_ylim(-m, H + m)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=11, fontweight='bold', pad=8)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.grid(True, alpha=0.15)

    def _draw_nets(self, ax, limit: int = 120):
        for net in self.ckt.nets[:limit]:
            pts = []
            for pin in net.pins:
                if pin.cell_id in self.ckt.cells:
                    c = self.ckt.cells[pin.cell_id]
                    pts.append((c.x + pin.x_offset, c.y + pin.y_offset))
            if len(pts) < 2:
                continue
            cx = np.mean([p[0] for p in pts])
            cy = np.mean([p[1] for p in pts])
            for px, py in pts:
                ax.plot([cx, px], [cy, py],
                        color='#ff8c00', alpha=0.12, lw=0.4, zorder=2)

    # ---------- 收敛曲线 ----------
    def draw_convergence(self, ax, costs, temps):
        iters = range(len(costs))
        c1, c2 = '#1976D2', '#E64A19'

        ax.plot(iters, costs, color=c1, lw=1.5, label='HPWL')
        ax.set_xlabel('Iteration')
        ax.set_ylabel('HPWL', color=c1)
        ax.tick_params(axis='y', labelcolor=c1)

        ax2 = ax.twinx()
        ax2.plot(iters, temps, color=c2, lw=1, alpha=0.5, ls='--', label='Temp')
        ax2.set_ylabel('Temperature', color=c2)
        ax2.tick_params(axis='y', labelcolor=c2)

        lines = ax.get_legend_handles_labels()
        lines2 = ax2.get_legend_handles_labels()
        ax.legend(lines[0] + lines2[0], lines[1] + lines2[1],
                  loc='upper right', fontsize=8)
        ax.set_title('SA Convergence', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.2)

    # ---------- 统计面板 ----------
    def draw_stats(self, ax, stats: dict):
        ax.axis('off')
        lines = [
            f"{'─'*38}",
            f"  Circuit :  {self.ckt.name}",
            f"  Die     :  {self.ckt.chip_width:.0f} × {self.ckt.chip_height:.0f}",
            f"  Cells   :  {stats['n_cells']}",
            f"  Nets    :  {stats['n_nets']}",
            f"  Rows    :  {len(self.ckt.rows)}",
            f"{'─'*38}",
            f"  Init  HPWL : {stats['hpwl_init']:>10.1f}",
            f"  SA    HPWL : {stats['hpwl_sa']:>10.1f}",
            f"  Legal HPWL : {stats['hpwl_legal']:>10.1f}",
            f"{'─'*38}",
            f"  SA improvement : {stats['sa_pct']:>+8.2f} %",
            f"  Overlap before : {stats['ov_pre']:>10.1f}",
            f"  Overlap after  : {stats['ov_post']:>10.1f}",
            f"  Displacement   : {stats['disp']:>10.1f}",
            f"{'─'*38}",
        ]
        ax.text(0.05, 0.95, '\n'.join(lines), transform=ax.transAxes,
                fontsize=9, va='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=0.6', fc='lightyellow', alpha=0.9))
        ax.set_title('Summary', fontsize=11, fontweight='bold')

    # ---------- 密度热力图 ----------
    def draw_density(self, ax, title="Cell Density", grid_n=25):
        W, H = self.ckt.chip_width, self.ckt.chip_height
        dx, dy = W / grid_n, H / grid_n
        density = np.zeros((grid_n, grid_n))

        for c in self.ckt.cells.values():
            if c.is_pad:
                continue
            gi = int(min(c.cx / dx, grid_n - 1))
            gj = int(min(c.cy / dy, grid_n - 1))
            density[gj, gi] += c.width * c.height

        im = ax.imshow(density, origin='lower', cmap='YlOrRd',
                       extent=[0, W, 0, H], aspect='auto', zorder=0)
        plt.colorbar(im, ax=ax, shrink=0.65, label='Area')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')

    # ---------- 综合大图 ----------
    def full_report(self, sa_placer,
                    pos_init, pos_sa, pos_legal,
                    stats, save_path=None):
        fig = plt.figure(figsize=(22, 14))
        fig.suptitle('DigiPlace  —  Digital IC Automatic Placement',
                     fontsize=15, fontweight='bold', y=0.99)

        # (1) 初始布局
        ax1 = fig.add_subplot(2, 3, 1)
        self._apply(pos_init)
        self.draw_placement(ax1,
            title=f"(1) Random Init\nHPWL = {stats['hpwl_init']:.0f}",
            show_nets=True, highlight_overlap=True)

        # (2) SA 优化后
        ax2 = fig.add_subplot(2, 3, 2)
        self._apply(pos_sa)
        self.draw_placement(ax2,
            title=f"(2) After SA\nHPWL = {stats['hpwl_sa']:.0f}  "
                  f"({stats['sa_pct']:+.1f}%)",
            show_nets=True, highlight_overlap=True)

        # (3) 合法化后
        ax3 = fig.add_subplot(2, 3, 3)
        self._apply(pos_legal)
        self.draw_placement(ax3,
            title=f"(3) After Legalization\nHPWL = {stats['hpwl_legal']:.0f}  "
                  f"Overlap = {stats['ov_post']:.0f}",
            show_nets=True, highlight_overlap=True)

        # (4) 收敛曲线
        ax4 = fig.add_subplot(2, 3, 4)
        self.draw_convergence(ax4, sa_placer.cost_history, sa_placer.temp_history)

        # (5) 密度图
        ax5 = fig.add_subplot(2, 3, 5)
        self._apply(pos_legal)
        self.draw_density(ax5, title="(5) Density Heatmap (Legal)")

        # (6) 统计
        ax6 = fig.add_subplot(2, 3, 6)
        self.draw_stats(ax6, stats)

        plt.tight_layout(rect=[0, 0, 1, 0.97])
        if save_path:
            plt.savefig(save_path, dpi=160, bbox_inches='tight')
            print(f"  ✔ 可视化结果已保存: {save_path}")
        plt.show()

    def _apply(self, pos: dict):
        for cid, (x, y) in pos.items():
            if cid in self.ckt.cells:
                self.ckt.cells[cid].x = x
                self.ckt.cells[cid].y = y


# ╔══════════════════════════════════════════════════════════════╗
# ║                   七、主布局引擎                             ║
# ╚══════════════════════════════════════════════════════════════╝

class PlacementEngine:
    """
    顶层引擎: 串联所有阶段
        Generate → SA Global → Legalize → Visualize
    """

    def __init__(self, cfg: dict = None):
        self.cfg = cfg or {}

    @staticmethod
    def _snap(circuit: Circuit) -> Dict[int, Tuple[float, float]]:
        return {cid: (c.x, c.y) for cid, c in circuit.cells.items()}

    def run(self):
        banner = """
  ╔════════════════════════════════════════════════════════╗
  ║          DigiPlace — 数字IC自动布局工具               ║
  ║  Simulated-Annealing Placement  +  Legalization       ║
  ╚════════════════════════════════════════════════════════╝"""
        print(banner)

        # -------- 0. 生成电路 --------
        ckt = BenchmarkGenerator.generate(
            num_cells   = self.cfg.get('num_cells', 200),
            num_nets    = self.cfg.get('num_nets', 280),
            num_pads    = self.cfg.get('num_pads', 20),
            avg_fanout  = self.cfg.get('avg_fanout', 4),
            utilization = self.cfg.get('utilization', 0.55),
            seed        = self.cfg.get('seed', 42),
        )

        stats = dict(n_cells=len(ckt.movable_cells()), n_nets=len(ckt.nets))

        # -------- 1. 随机初始布局 --------
        sa = SimulatedAnnealingPlacer(ckt, dict(
            cooling_rate = self.cfg.get('cooling_rate', 0.95),
            max_iter     = self.cfg.get('max_iter', 350),
            swap_prob    = self.cfg.get('swap_prob', 0.35),
            seed         = self.cfg.get('seed', 42),
            verbose      = True,
        ))
        sa.random_initial_placement()
        hpwl_init = HPWLCalculator.total_hpwl(ckt.nets, ckt.cells)
        stats['hpwl_init'] = hpwl_init
        pos_init = self._snap(ckt)

        # -------- 2. 模拟退火 --------
        hpwl_sa = sa.optimize()
        stats['hpwl_sa'] = hpwl_sa
        stats['sa_pct'] = (1 - hpwl_sa / max(hpwl_init, 1)) * 100
        pos_sa = self._snap(ckt)

        # -------- 3. 合法化 --------
        leg = TetrisLegalizer(ckt)
        ov_pre, _ = leg.compute_overlap()
        stats['ov_pre'] = ov_pre

        disp = leg.legalize()
        stats['disp'] = disp

        hpwl_legal = HPWLCalculator.total_hpwl(ckt.nets, ckt.cells)
        stats['hpwl_legal'] = hpwl_legal
        ov_post, _ = leg.compute_overlap()
        stats['ov_post'] = ov_post
        pos_legal = self._snap(ckt)

        # -------- 4. 可视化 --------
        print("  Generating visualization …")
        vis = PlacementVisualizer(ckt)
        vis.full_report(sa, pos_init, pos_sa, pos_legal, stats,
                        save_path='digiplace_result.png')

        # -------- 5. 汇总 --------
        print(f"\n  ╔═══════════════════════════════════════╗")
        print(f"  ║         Final Summary                 ║")
        print(f"  ╠═══════════════════════════════════════╣")
        for k, v in stats.items():
            vstr = f"{v:.2f}" if isinstance(v, float) else str(v)
            print(f"  ║  {k:<18s} = {vstr:>14s}  ║")
        print(f"  ╚═══════════════════════════════════════╝\n")
        return stats


# ╔══════════════════════════════════════════════════════════════╗
# ║                      八、入口                               ║
# ╚══════════════════════════════════════════════════════════════╝

def main():
    config = dict(
        # ---- 电路规模 ----
        num_cells   = 200,
        num_nets    = 280,
        num_pads    = 20,
        avg_fanout  = 4,
        utilization = 0.55,
        # ---- SA 超参 ----
        cooling_rate = 0.95,
        max_iter     = 350,
        swap_prob    = 0.35,
        seed         = 42,
    )
    engine = PlacementEngine(config)
    engine.run()


if __name__ == '__main__':
    main()