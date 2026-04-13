from IP_DataStructures import Net, Design

class HPWLCalculator:
    """
    线长计算器，使用半周长包围盒 (Half-Perimeter WireLength) 算法
    """
    
    @staticmethod
    def calculate_net_hpwl(net: Net) -> float:
        """
        计算单个线网(Net)的 HPWL
        """
        # 如果线网没有连接 Cell，或者只连了 1 个 Cell，那就不需要走线，线长为 0
        if not net.cells or len(net.cells) < 2:
            return 0.0

        # 获取线网上所有 Cell 的中心点 X 和 Y 坐标
        x_coords = [cell.cx for cell in net.cells]
        y_coords = [cell.cy for cell in net.cells]

        # 找到包围盒的边界 (Bounding Box)
        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)

        # HPWL = 包围盒的宽度 (max_x - min_x) + 包围盒的高度 (max_y - min_y)
        hpwl = (max_x - min_x) + (max_y - min_y)
        
        return hpwl

    @staticmethod
    def calculate_total_hpwl(design: Design) -> float:
        """
        计算整个设计(Design)中所有线网的总 HPWL
        """
        total_hpwl = 0.0
        
        # 遍历设计中的每一条线网，累加它们的 HPWL
        for net in design.nets.values():
            total_hpwl += HPWLCalculator.calculate_net_hpwl(net)
            
        return total_hpwl
    

'''
Test
'''
if __name__ == "__main__":
    from IP_DataStructures import Design, Row, Cell, Net

    # 1. 准备测试数据 (跟第一步类似)
    my_design = Design(width=100.0, height=100.0)
    
    macro1 = Cell("Macro_0", width=20, height=20, is_fixed=True)
    std_cell1 = Cell("Cell_1", width=5, height=10, is_fixed=False)
    std_cell2 = Cell("Cell_2", width=5, height=10, is_fixed=False)
    
    # 手动设置位置
    # Macro中心点在 (90, 90) -> x=80, w=20
    macro1.x, macro1.y = 80, 80 
    
    # Cell1中心点在 (12.5, 15) -> x=10, w=5
    std_cell1.x, std_cell1.y = 10, 10
    
    # Cell2中心点在 (52.5, 55) -> x=50, w=5
    std_cell2.x, std_cell2.y = 50, 50

    my_design.add_cell(macro1)
    my_design.add_cell(std_cell1)
    my_design.add_cell(std_cell2)

    # 2. 连接第一条线网 (连接 3 个 Cell)
    net_a = Net("Net_A")
    net_a.add_cell(macro1)
    net_a.add_cell(std_cell1)
    net_a.add_cell(std_cell2)
    my_design.add_net(net_a)

    # 3. 连接第二条线网 (只连接 Cell1 和 Cell2)
    net_b = Net("Net_B")
    net_b.add_cell(std_cell1)
    net_b.add_cell(std_cell2)
    my_design.add_net(net_b)

    # 4. 计算并打印 HPWL
    hpwl_a = HPWLCalculator.calculate_net_hpwl(net_a)
    hpwl_b = HPWLCalculator.calculate_net_hpwl(net_b)
    total = HPWLCalculator.calculate_total_hpwl(my_design)

    print(f"Net_A HPWL: {hpwl_a}")
    print(f"Net_B HPWL: {hpwl_b}")
    print(f"Total Design HPWL: {total}")