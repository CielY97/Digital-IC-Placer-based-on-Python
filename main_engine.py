# main_engine.py

import os
import time
from benchmark_generator import BenchmarkGenerator
from sa_placer import SAPlacer
from legalizer import Legalizer
from IP_HPWL import HPWLCalculator
from visualization import Visualizer

class PlacementEngine:
    """
    主布局引擎：统筹管理整个布局的生命周期 (Generation -> SA -> Legalization -> Output)
    """
    def __init__(self, config: dict):
        self.config = config
        self.design = None
        
        # 创建输出文件夹，保持项目目录整洁
        self.output_dir = "output_images"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def run_flow(self):
        """
        执行完整的一键式布局 Flow
        """
        start_time = time.time()
        print(f"{'='*50}")
        print(f"🚀 启动数字 IC 布局引擎 (Digital IC Placement Engine)")
        print(f"{'='*50}\n")

        # ---------------------------------------------------------
        # Step 1: 读取配置并生成/加载网表
        # ---------------------------------------------------------
        print("[Step 1] 初始化与网表生成...")
        self.design = BenchmarkGenerator.generate_design(
            num_cells=self.config.get('num_cells', 300),
            num_nets=self.config.get('num_nets', 350),
            design_w=self.config.get('design_w', 150.0),
            design_h=self.config.get('design_h', 150.0),
            cell_w=self.config.get('cell_w', 3.0),
            cell_h=self.config.get('cell_h', 10.0),
            num_clusters=self.config.get('num_clusters', 4)
        )
        initial_hpwl = HPWLCalculator.calculate_total_hpwl(self.design)
        print(f"  -> 生成完成！当前设计包含 {len(self.design.cells)} 个单元, {len(self.design.nets)} 条线网.")
        print(f"  -> 初始随机状态的总线长 (HPWL): {initial_hpwl:.2f}")
        
        # 绘制初始状态
        Visualizer.plot_layout(
            self.design, 
            title=f"1. Initial Random Placement\n(HPWL: {initial_hpwl:.0f})", 
            save_path=os.path.join(self.output_dir, "1_initial_placement.png")
        )

        # ---------------------------------------------------------
        # Step 2: 全局布局 (Global Placement - SA)
        # ---------------------------------------------------------
        print("\n[Step 2] 开始全局布局 (Global Placement - SA)...")
        sa_start = time.time()
        placer = SAPlacer(self.design)
        placer.place(
            T0=self.config.get('sa_T0', 1000.0),
            T_end=self.config.get('sa_T_end', 1.0),
            alpha=self.config.get('sa_alpha', 0.9),
            inner_iter=self.config.get('sa_inner_iter', 2000)
        )
        sa_hpwl = HPWLCalculator.calculate_total_hpwl(self.design)
        sa_time = time.time() - sa_start
        print(f"  -> 全局布局完成！耗时: {sa_time:.2f} 秒.")
        print(f"  -> 退火后总线长 (HPWL): {sa_hpwl:.2f} (优化了 {((initial_hpwl-sa_hpwl)/initial_hpwl)*100:.1f}%)")
        
        # 绘制全局布局结果
        Visualizer.plot_layout(
            self.design, 
            title=f"2. After Global Placement (SA)\n(HPWL: {sa_hpwl:.0f})", 
            save_path=os.path.join(self.output_dir, "2_global_placement.png")
        )

        # ---------------------------------------------------------
        # Step 3: 合法化 (Legalization)
        # ---------------------------------------------------------
        print("\n[Step 3] 开始合法化 (Legalization)...")
        leg_start = time.time()
        legalizer = Legalizer(self.design)
        legalizer.legalize()
        leg_hpwl = HPWLCalculator.calculate_total_hpwl(self.design)
        leg_time = time.time() - leg_start
        print(f"  -> 合法化完成！耗时: {leg_time:.4f} 秒.")
        print(f"  -> 最终合法总线长 (HPWL): {leg_hpwl:.2f}")
        
        # 绘制合法化结果
        Visualizer.plot_layout(
            self.design, 
            title=f"3. After Legalization\n(HPWL: {leg_hpwl:.0f})", 
            save_path=os.path.join(self.output_dir, "3_legalized_placement.png")
        )

        # ---------------------------------------------------------
        # 总结
        # ---------------------------------------------------------
        total_time = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"✅ Flow 运行完毕！总耗时: {total_time:.2f} 秒")
        print(f"📁 可视化结果已保存至 '{self.output_dir}' 文件夹，请查看！")
        print(f"{'='*50}")