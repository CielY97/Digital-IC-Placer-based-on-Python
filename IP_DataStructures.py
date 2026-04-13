"""
from __future__ import annotations
from typing import List, Dict, Tuple
"""

class Cell:
    """
    用于表示芯片中的一个单元
    """
    def __init__(self, name: str, width: float, height: float, is_fixed: bool = False):
        self.name = name
        self.w = width
        self.h = height
        self.is_fixed = is_fixed #True for Macro,False for standard cell

        #单元左下角坐标
        self.x = 0.0
        self.y = 0.0

    @property
    def cx(self):
        """获取cell中心的x坐标,用于计算线长"""
        return self.x + self.w / 2
    
    @property
    def cy(self):
        """获取cell中心的y坐标,计算线长"""
        return self.y + self.h / 2
    
    def __repr__(self):
        return f"Cell({self.name}, x = {self.x:.1f}, y = {self.y:.1f}, w = {self.w}, h = {self.h})"
    

class Net:
    """
    Net用于连接多个cell
    """
    def __init__(self, name: str):
        self.name = name
        self.cells = [] #连接所有的cell列表

    def add_cell(self, cell: Cell):
        #将一个cell添加道该net中
        if cell not in self.cells:
            self.cells.append(cell)

    def __repr__(self):
        cell_names = [c.name for c in self.cells]
        return f"Net({self.name}, connected_to = {cell_names})"
    

class Row:
    """
    表示布局区域中的标准行
    便于后续合法化
    """
    def __init__(self, y: float, height: float, width: float, x_start: float = 0.0):
        self.y = y
        self.h = height
        self.w = width
        self.x = x_start

    def __repr__(self):
        return f"Row(y={self.y}, h={self.h}, w={self.w})"
      
        
class Design:
    """
    顶层数据结构
    包含所有信息
    """
    def __init__(self, width: float, height: float):
        self.w = width
        self.h = height

        self.cells = {}  # 用字典存储: {'cell_name': Cell_object} 快于列表
        self.nets = {}   # 用字典存储: {'net_name': Net_object} 快于列表
        self.rows = []   # 存储所有Row

    def add_cell(self, cell: Cell):
        self.cells[cell.name] = cell

    def add_net(self, net: Net):
        self.nets[net.name] = net

    def add_row(self, row: Row):
        self.rows.append(row)

    def get_movable_cells(self):
        #获取所有可移动的单元（后续模拟退火算法只需要移动这些）
        return [cell for cell in self.cells.values() if not cell.is_fixed]

    def __repr__(self):
        return (f"Design(w={self.w}, h={self.h}, "
                f"|Cells|={len(self.cells)}, |Nets|={len(self.nets)}, |Rows|={len(self.rows)})")
    
'''
test
'''
if __name__ == "__main__":
    # 1. 创建一个 100x100 的芯片画布
    my_design = Design(width=100.0, height=100.0)

    # 2. 创建几行 Row (假设每行高度为 10，一共 10 行)
    for i in range(10):
        my_design.add_row(Row(y=i*10.0, height=10.0, width=100.0))

    # 3. 创建几个 Cell
    # 一个固定的 Macro (宏单元)
    macro1 = Cell("Macro_0", width=20, height=20, is_fixed=True)
    macro1.x, macro1.y = 80, 80  # 把它放在右上角
    
    # 两个可移动的标准单元
    std_cell1 = Cell("Cell_1", width=5, height=10, is_fixed=False)
    std_cell2 = Cell("Cell_2", width=5, height=10, is_fixed=False)
    std_cell1.x, std_cell1.y = 10, 10
    std_cell2.x, std_cell2.y = 50, 50

    my_design.add_cell(macro1)
    my_design.add_cell(std_cell1)
    my_design.add_cell(std_cell2)

    # 4. 创建一条线网，把这三个 Cell 连起来
    net1 = Net("Net_A")
    net1.add_cell(macro1)
    net1.add_cell(std_cell1)
    net1.add_cell(std_cell2)
    my_design.add_net(net1)

    # 5. 打印查看结果
    print(my_design)
    print("Movable Cells:", my_design.get_movable_cells())
    print(net1)
    print(f"Center of {std_cell1.name} is at ({std_cell1.cx}, {std_cell1.cy})")

