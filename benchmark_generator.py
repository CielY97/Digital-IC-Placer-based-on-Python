# benchmark_generator.py
import random
from IP_DataStructures import Design, Cell, Net, Row

class BenchmarkGenerator:
    """
    基准测试电路生成器：用于生成带有聚簇(Clustering)特征的随机网表
    """
    
    @staticmethod
    def generate_design(
        num_cells: int = 100, 
        num_nets: int = 120, 
        design_w: float = 100.0, 
        design_h: float = 100.0,
        cell_w: float = 2.0,
        cell_h: float = 10.0,
        num_clusters: int = 4
    ) -> Design:
        """
        生成一个包含 Row, Cell 和 Net 的完整 Design 对象
        """
        design = Design(width=design_w, height=design_h)

        # ---------------------------------------------------------
        # 1. 生成标准的摆放行 (Rows)
        # ---------------------------------------------------------
        # 根据设计的高度和单元的高度，计算能放下多少行
        num_rows = int(design_h // cell_h)
        for i in range(num_rows):
            # 行的起点 y 坐标依次是 0, 10, 20...
            row = Row(y=i * cell_h, height=cell_h, width=design_w)
            design.add_row(row)

        # ---------------------------------------------------------
        # 2. 生成单元 (Cells) 并分配到不同的“小团体(Clusters)”中
        # ---------------------------------------------------------
        clusters = {i: [] for i in range(num_clusters)}
        
        for i in range(num_cells):
            cell = Cell(name=f"C_{i}", width=cell_w, height=cell_h, is_fixed=False)
            
            # 初始状态：给每个 Cell 随机分配一个在画布内的 (x, y) 坐标
            # (注意要保证 Cell 不会超出画布边界)
            cell.x = random.uniform(0, design_w - cell_w)
            cell.y = random.uniform(0, design_h - cell_h)
            
            design.add_cell(cell)
            
            # 将 Cell 均分到各个 cluster 中
            cluster_id = i % num_clusters
            clusters[cluster_id].append(cell)

        # ---------------------------------------------------------
        # 3. 生成线网 (Nets) - 模拟真实电路的局部性
        # ---------------------------------------------------------
        for i in range(num_nets):
            net = Net(name=f"N_{i}")
            
            # 决定这个线网有几个引脚 (Pin Count)
            # 权重分布：70%是2-pin, 20%是3-pin, 10%是4-pin
            pin_count = random.choices([2, 3, 4], weights=[0.7, 0.2, 0.1])[0]
            
            # 决定这个线网是“内部网(Local)”还是“全局网(Global)”
            # 80% 的概率是在同一个小团体内部连线，20% 是跨团体连线
            is_local = random.random() < 0.8
            
            if is_local:
                # 随机挑一个小团体，从里面抽几个 Cell 连起来
                chosen_cluster_id = random.randint(0, num_clusters - 1)
                pool = clusters[chosen_cluster_id]
            else:
                # 从全芯片所有的 Cell 中随机抽
                pool = list(design.cells.values())
            
            # 如果池子里的 Cell 数量不够 pin_count，就按池子大小来
            actual_pin_count = min(pin_count, len(pool))
            
            # 随机无放回地抽取 Cell 添加到线网中
            chosen_cells = random.sample(pool, actual_pin_count)
            for cell in chosen_cells:
                net.add_cell(cell)
                
            design.add_net(net)

        return design

if __name__ == "__main__":
    # 测试生成器
    # 假设我们生成一个稍微大一点的电路：500个门，600条线，分5个大模块
    print("正在生成基准测试电路...")
    test_design = BenchmarkGenerator.generate_design(
        num_cells=500, 
        num_nets=600, 
        design_w=200.0, 
        design_h=200.0,
        num_clusters=5
    )
    
    print(test_design)
    
    # 验证一下生成的 Net 的引脚数量分布
    pin_counts = [len(net.cells) for net in test_design.nets.values()]
    count_2 = pin_counts.count(2)
    count_3 = pin_counts.count(3)
    count_4 = pin_counts.count(4)
    
    print("\n=== 线网引脚统计 ===")
    print(f"2-pin nets: {count_2} ({count_2/len(pin_counts)*100:.1f}%)")
    print(f"3-pin nets: {count_3} ({count_3/len(pin_counts)*100:.1f}%)")
    print(f"4-pin nets: {count_4} ({count_4/len(pin_counts)*100:.1f}%)")
    
    # 用第二步写的计算器算一下初始的乱序 HPWL
    from IP_HPWL import HPWLCalculator
    initial_hpwl = HPWLCalculator.calculate_total_hpwl(test_design)
    print(f"\n初始随机布局的总 HPWL: {initial_hpwl:.2f}")