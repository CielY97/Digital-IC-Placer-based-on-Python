# sa_placer.py

import math
import random
from IP_DataStructures import Design
from IP_HPWL import HPWLCalculator

class SAPlacer:
    """
    基于模拟退火 (Simulated Annealing) 的全局布局器
    """
    def __init__(self, design: Design):
        self.design = design
        self.movable_cells = design.get_movable_cells()
        
        # 【核心优化】：建立反向映射表 (Reverse Mapping)
        # 为了实现“增量计算”，我们需要知道每个 Cell 连接了哪些 Net
        self.cell_to_nets = {c.name: set() for c in self.movable_cells}
        for net in design.nets.values():
            for cell in net.cells:
                if not cell.is_fixed:
                    self.cell_to_nets[cell.name].add(net)

    def _calc_partial_hpwl(self, cells: list) -> float:
        """
        计算只与传入的 cells 相关的那些线网的 HPWL 总和
        """
        affected_nets = set()
        for c in cells:
            # 把这个 cell 连接的所有线网加入到受影响集合中
            affected_nets.update(self.cell_to_nets[c.name])
        
        # 只计算受影响线网的 HPWL
        return sum(HPWLCalculator.calculate_net_hpwl(net) for net in affected_nets)

    def place(self, T0: float = 1000.0, T_end: float = 1.0, alpha: float = 0.95, inner_iter: int = 1000):
        """
        执行模拟退火布局
        :param T0: 初始温度 (Initial Temperature)
        :param T_end: 终止温度 (Final Temperature)
        :param alpha: 降温系数 (Cooling Rate)，通常在 0.85 ~ 0.99 之间
        :param inner_iter: 每个温度下的迭代次数
        """
        T = T0
        
        # 计算初始的全局 HPWL
        current_total_hpwl = HPWLCalculator.calculate_total_hpwl(self.design)
        print(f"--- SA 布局开始 ---")
        print(f"初始总线长 (HPWL): {current_total_hpwl:.2f}")

        # 外层循环：降温过程
        while T > T_end:
            accepted_moves = 0
            
            # 内层循环：在当前温度下疯狂尝试改变位置
            for _ in range(inner_iter):
                # 随机决定是“移动单个单元 (Translate)”还是“交换两个单元 (Swap)”
                move_type = random.choice(['translate', 'swap'])

                if move_type == 'translate':
                    # 1. 移动单个 Cell 到随机位置
                    cell = random.choice(self.movable_cells)
                    old_x, old_y = cell.x, cell.y
                    
                    # 移动前，相关线网的 HPWL
                    old_cost = self._calc_partial_hpwl([cell])
                    
                    # 施加微扰：给一个新的随机坐标（注意不要超出边界）
                    cell.x = random.uniform(0, self.design.w - cell.w)
                    cell.y = random.uniform(0, self.design.h - cell.h)
                    
                    # 移动后，相关线网的 HPWL
                    new_cost = self._calc_partial_hpwl([cell])
                    
                    delta_cost = new_cost - old_cost

                    # Metropolis 准则判断
                    if delta_cost < 0 or random.random() < math.exp(-delta_cost / T):
                        # 接受移动
                        current_total_hpwl += delta_cost
                        accepted_moves += 1
                    else:
                        # 拒绝移动，状态回退
                        cell.x, cell.y = old_x, old_y

                else:
                    # 2. 交换两个 Cell 的位置
                    # 如果可移动单元少于 2 个，直接跳过
                    if len(self.movable_cells) < 2: continue
                    
                    c1, c2 = random.sample(self.movable_cells, 2)
                    old_cost = self._calc_partial_hpwl([c1, c2])
                    
                    # 交换坐标
                    c1.x, c2.x = c2.x, c1.x
                    c1.y, c2.y = c2.y, c1.y
                    
                    new_cost = self._calc_partial_hpwl([c1, c2])
                    delta_cost = new_cost - old_cost

                    # Metropolis 准则判断
                    if delta_cost < 0 or random.random() < math.exp(-delta_cost / T):
                        # 接受交换
                        current_total_hpwl += delta_cost
                        accepted_moves += 1
                    else:
                        # 拒绝交换，状态回退
                        c1.x, c2.x = c2.x, c1.x
                        c1.y, c2.y = c2.y, c1.y

            # 降温
            T *= alpha
            
            # 每降温一次，重新计算一次全局 HPWL（消除浮点数加减积累的误差）
            current_total_hpwl = HPWLCalculator.calculate_total_hpwl(self.design)
            
            # 打印当前进度
            accept_rate = (accepted_moves / inner_iter) * 100
            print(f"温度: {T:6.1f} | HPWL: {current_total_hpwl:8.2f} | 接受率: {accept_rate:5.1f}%")

        print(f"--- SA 布局结束 ---")
        print(f"最终总线长 (HPWL): {current_total_hpwl:.2f}")