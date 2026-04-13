# visualization.py

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from IP_DataStructures import Design

class Visualizer:
    """
    布局可视化模块：使用 matplotlib 绘制芯片的 2D 俯视图
    """
    
    @staticmethod
    def plot_layout(design: Design, title: str = "Placement Layout", show_nets: bool = True, save_path: str = None):
        """
        绘制当前 Design 的布局状态
        :param design: Design 对象
        :param title: 图片标题（比如 "初始状态", "退火后", "合法化后"）
        :param show_nets: 是否绘制飞线 (Rat's nest)
        :param save_path: 如果提供路径，则保存为图片文件；否则直接弹出窗口显示
        """
        # 创建一块画布 (10x10 英寸)
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # 1. 绘制芯片边界 (Die Area)
        ax.set_xlim(0, design.w)
        ax.set_ylim(0, design.h)
        die_area = patches.Rectangle((0, 0), design.w, design.h, fill=False, edgecolor='black', linewidth=3)
        ax.add_patch(die_area)
        
        # 2. 绘制摆放行 (Rows) - 用浅灰色的虚线表示地板网格
        for row in design.rows:
            ax.axhline(y=row.y, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
            
        # 3. 绘制线网 (Nets) - 传说中的飞线 (Rat's Nest)
        if show_nets:
            for net in design.nets.values():
                if len(net.cells) < 2:
                    continue
                
                # 为了防止满屏乱线，我们采用“星型拓扑 (Star Topology)”画法：
                # 算出这个 Net 所有 Cell 的几何中心，然后把每个 Cell 连到中心点
                cx_sum = sum(c.cx for c in net.cells)
                cy_sum = sum(c.cy for c in net.cells)
                center_x = cx_sum / len(net.cells)
                center_y = cy_sum / len(net.cells)
                
                for cell in net.cells:
                    # 画一条极细、半透明的绿色线
                    ax.plot([cell.cx, center_x], [cell.cy, center_y], color='green', alpha=0.15, linewidth=0.5)

        # 4. 绘制单元 (Cells)
        for cell in design.cells.values():
            # 宏单元用红色，标准单元用天蓝色
            face_color = 'salmon' if cell.is_fixed else 'skyblue'
            
            # 使用矩形 Patch 画出 Cell 的真实大小
            rect = patches.Rectangle(
                (cell.x, cell.y), cell.w, cell.h, 
                linewidth=0.5, edgecolor='black', facecolor=face_color, alpha=0.8
            )
            ax.add_patch(rect)
            
        # 5. 设置图表属性
        ax.set_aspect('equal')  # 强制 X 轴和 Y 轴比例 1:1，防止芯片变形
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        
        # 6. 显示或保存
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图纸已保存至: {save_path}")
        else:
            plt.show()
            
        # 必须关闭 figure 释放内存，否则多次调用会导致程序崩溃
        plt.close(fig)