from IP_DataStructures import Design
from IP_HPWL import HPWLCalculator

class Legalizer:
    """
    合法化器：将连续坐标的单元对齐到 Row，并消除同一 Row 内的物理重叠
    """
    def __init__(self, design: Design):
        self.design = design

    def legalize(self):
        print("--- 开始合法化 (Legalization) ---")
        
        # 1. 记录合法化前的 HPWL
        pre_legal_hpwl = HPWLCalculator.calculate_total_hpwl(self.design)
        
        # 准备一个字典，用于存放每一行分到了哪些 Cell
        # 格式: {row.y: [cell1, cell2, ...]}
        row_cells = {row.y: [] for row in self.design.rows}

        # ==========================================
        # 步骤 A：Row Assignment (Y轴对齐)
        # ==========================================
        for cell in self.design.get_movable_cells():
            # 找到离这个 cell 最近的 Row
            # key=lambda r: abs(cell.y - r.y) 的意思是：计算 cell.y 和 每个 row.y 的差值绝对值，取最小的那个 Row
            best_row = min(self.design.rows, key=lambda r: abs(cell.y - r.y))
            
            # 强制把 Cell 的 Y 坐标对齐到这个 Row 的底部
            cell.y = best_row.y
            row_cells[best_row.y].append(cell)

        # ==========================================
        # 步骤 B：1D Overlap Removal (X轴消除重叠)
        # ==========================================
        for row_y, cells_in_row in row_cells.items():
            if not cells_in_row:
                continue  # 如果这行没有分到 Cell，直接跳过

            # 按照 Cell 目前的 X 坐标从左到右排序
            # 这样我们在推开它们时，能尽量保持它们原本的左右相对顺序
            cells_in_row.sort(key=lambda c: c.x)

            # 记录当前行“下一个可以摆放家具的合法 X 坐标”
            next_available_x = 0.0

            for cell in cells_in_row:
                # 1. 边界保护：不能掉出芯片左边界
                if cell.x < 0:
                    cell.x = 0.0
                
                # 2. 消除重叠核心逻辑：
                # 如果当前 Cell 的左边界比 next_available_x 还要靠左，说明它和左边的 Cell 重叠了！
                # 我们必须把它强制向右推（Push Right）
                if cell.x < next_available_x:
                    cell.x = next_available_x
                
                # 3. 边界保护：不能掉出芯片右边界
                # 如果推完之后超出了右边界，我们就把它强制贴在右边界上
                # (注意：在极度拥挤的极端情况下，贴在右边界可能会导致微小的重叠，
                #  但工业界会有后续的详细调整，我们的原型在此处做简化处理)
                if cell.x + cell.w > self.design.w:
                    cell.x = self.design.w - cell.w

                # 更新下一个合法位置（当前 Cell 的 X 加上它的宽度）
                next_available_x = cell.x + cell.w

        # 2. 记录合法化后的 HPWL
        post_legal_hpwl = HPWLCalculator.calculate_total_hpwl(self.design)
        degradation = post_legal_hpwl - pre_legal_hpwl
        
        print("--- 合法化完成 ---")
        print(f"合法化前 HPWL: {pre_legal_hpwl:.2f}")
        print(f"合法化后 HPWL: {post_legal_hpwl:.2f}")
        print(f"线长损失 (Degradation): +{degradation:.2f} ({(degradation/pre_legal_hpwl)*100:.2f}%)")

if __name__ == "__main__":
    from benchmark_generator import BenchmarkGenerator
    from sa_placer import SAPlacer

    # 1. 生成基准电路
    print("1. 生成网表...")
    design = BenchmarkGenerator.generate_design(
        num_cells=200,   # 生成 200 个门
        num_nets=250, 
        design_w=100.0, 
        design_h=100.0,
        cell_w=2.0,      # 每个门宽 2.0
        cell_h=10.0      # 每个门高 10.0，恰好等于 1 个 Row 的高度
    )

    # 2. 全局布局 (SA)
    print("\n2. 开始全局布局...")
    placer = SAPlacer(design)
    # 为了演示快一点，迭代次数设为 500
    placer.place(T0=500.0, T_end=1.0, alpha=0.9, inner_iter=500)

    # 3. 合法化 (Legalization)
    print("\n3. 开始合法化...")
    legalizer = Legalizer(design)
    legalizer.legalize()

    # 4. 验证是否还有重叠（简单抽查某一行）
    print("\n4. 验证重叠状态 (抽查 Y=50.0 这一行):")
    row_50_cells = [c for c in design.cells.values() if c.y == 50.0]
    row_50_cells.sort(key=lambda c: c.x)
    for c in row_50_cells[:5]: # 只看前 5 个
        print(f"[{c.name}] x={c.x:.2f}, w={c.w}, 右边界={c.x + c.w:.2f}")