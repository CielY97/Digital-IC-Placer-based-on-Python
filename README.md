# Digital-IC-Placer-based-on-Python
基于Python与模拟退火算法的数字IC布局器
本项目是一个基于Python实现的数字集成电路（Digital IC）宏观/标准单元布局（Placement）算法原型。本程序从零开始构建了布局器的完整工作流，核心采用**模拟退火算法（Simulated Annealing, SA）**进行全局优化，并以**半周长线长（HPWL）**作为主要评估指标，最终输出合法化（Legalized）的布局结果并提供可视化。

## 🌟 核心算法与物理原理

本项目的重点在于通过物理启发式算法解决复杂的组合优化问题（NP-Hard）。

### 1. 目标函数：半周长线长计算器 (HPWL Calculator)
在VLSI设计中，精确计算实际布线长度是非常困难且耗时的。因此，工业界广泛采用**半周长线长（Half-Parameter Wire Length, HPWL）**作为线长预估的标准度量。

对于任意一个线网（Net）$e$，假设它连接了多个引脚（Pins），这些引脚的坐标集合包围盒（Bounding Box）的左下角为 $(x_{min}, y_{min})$，右上角为 $(x_{max}, y_{max})$。该线网的HPWL定义为包围盒的半周长：

$$ HPWL(e) = (x_{max} - x_{min}) + (y_{max} - y_{min}) $$

整个芯片的总线长评估（Cost Function）即为所有线网的HPWL之和：

$$ Cost = \sum_{e \in E} HPWL(e) $$

> **算法意义：** HPWL 可以在 $O(N)$ 的时间复杂度内快速计算出线长的下界，使得模拟退火算法在成千上万次迭代中能够极快地评估当前布局的优劣。

### 2. 优化引擎：模拟退火算法 (Simulated Annealing)
模拟退火算法灵感来源于固体物理学中的退火过程：将固体加热至充分高的温度，再让其徐徐冷却。加热时，固体内部粒子随温度升高变为无序状，内能增大；缓慢冷却时粒子渐趋有序，在每个温度都达到平衡态，最后在常温时达到基态，内能减为最小。

在IC布局问题中，我们进行如下物理映射：
* **粒子状态** $\rightarrow$ 单元（Cell）在芯片上的物理位置
* **系统能量 ($E$)** $\rightarrow$ 系统的总线长代价（Total HPWL）
* **系统温度 ($T$)** $\rightarrow$ 控制算法接受较差解的概率参数

**Metropolis 准则（核心数学原理）：**
在每次位置扰动（例如随机交换两个Cell的位置）后，计算能量变化 $\Delta E = E_{new} - E_{old}$：
1. 若 $\Delta E < 0$（线长变短），则**100%接受**该新布局。
2. 若 $\Delta E > 0$（线长变长），则以概率 $P$ 接受该较差的布局：
   $$
   P = \exp\left(-\frac{\Delta E}{k \cdot T}\right)
   $$
   *(其中 $k$ 为常数，实际编程中通常融入 $T$ 中)*

> **物理意义：** 允许在高温阶段以较大增幅接受劣解，赋予算法**“跳出局部最优解（Local Optima）”**的能力。随着温度 $T$ 按照退火时间表（如 $T_{k+1} = \alpha T_k, \alpha \approx 0.95$）不断下降，接受劣解的概率趋近于0，算法最终收敛于全局最优或近似全局最优解。

---

## 🏗️ 项目结构与模块说明

代码全部集中在主 `.py` 文件中，主要包含以下8个核心组件：

1. **基础数据结构 (Data Structures)**：定义了 `Cell`（标准单元）、`Net`（线网）、`Pin`（引脚）等物理设计的底层对象。
2. **HPWL计算器 (HPWL Calculator)**：实现了上述的线长评估公式，是算法迭代的“标尺”。
3. **基准电路生成器 (Benchmark Generator)**：能够随机生成具有一定连通性特征的测试电路网表，方便在没有外部库输入的情况下测试算法。
4. **模拟退火基础布局器 (SA Placer)**：实现了 Global Placement。包含初始温度设定、降温策略（Cooling Schedule）、扰动生成（Swap/Move）及 Metropolis 接受准则。
5. **合法化器 (Legalizer)**：将退火后的连续坐标映射到离散的网格/行（Rows）上，并消除Cell之间的物理重叠（Overlap removal）。
6. **可视化模块 (Visualization)**：基于 `matplotlib` 实现，能够动态/静态绘制单元分布、连线走向以及包围盒，直观展示布局优化过程。
7. **主布局引擎 (Main Engine)**：统筹各个模块，管理从网表解析 $\rightarrow$ 全局布局 $\rightarrow$ 合法化 $\rightarrow$ 结果输出的全流程。
8. **入口 (Entry Point)**：`if __main__` 模块，提供一键运行的接口。

---

## 🚀 快速开始 (Quick Start)

### 依赖安装
本程序仅依赖 Python 基础科学计算库：
```bash
pip install numpy matplotlib
