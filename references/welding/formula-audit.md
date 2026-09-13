# 文献公式核查与安全复用

定位：LV2024 为吕成 2024；LIU2022 为 Liu 等 2022，见[索引](index.md)。
下面的“修正/建议”由量纲、守恒与基本物理关系独立核查得到；不声称复原作者程序，也不代替求解器或实验验证。

## 1. 热源强度与能量密度

LIU2022，PDF p.5 Eq.7 把 $\eta P/(Av)$ 写为单位体积热源强度。对于功率 $P$、截面积 $A$ 和速度 $v$：

$$\left[\frac{\eta P}{Av}\right]=\frac{\mathrm{J}}{\mathrm{m}^3},\qquad[\dot q_v]=\frac{\mathrm{W}}{\mathrm{m}^3}$$

若激活段长度为 $\ell$，均匀移动体源的一种守恒构造为：

$$V_a=A\ell,\qquad\dot q_v=\frac{\eta P}{A\ell},\qquad\tau=\frac{\ell}{v},\qquad\dot q_v\tau=\frac{\eta P}{Av}$$

因此必须先给出移动激活体积或驻留时间，不能把能量密度直接填进 W/m³ 的热源节点。
若 $F$ 是左右对称截面的半宽，完整截面积是 $A=2\int F\mathrm{d}y$；半模型的源强与总功率另作一致处理。

更一般地，给定非负形状函数 $w$，可按完整热源支撑域归一化：

$$\dot q_v(\mathbf{x},t)=\frac{\eta P(t)w(\mathbf{x}-\mathbf{x}_c(t))}{\int_{\Omega_{\mathrm{src}}}w\mathrm{d}V}$$

以实测轮廓构造形状函数只是校准思路；轮廓边界不是已经证明的能量沉积分布。
工件边缘截获不足时，不应自动缩小归一化分母以强行保持整束功率。已有面源时先分配吸收功率，防止重复加热。

## 2. 高斯旋转体的定义域

LV2024，PDF p.3 Eq.8 的量纲可为 W/m³，但 $\log(H/z)$ 还需要明确正深度、对数底和支撑域。
仅在把原文 $Q$ 视为给定功率、$\log=\ln$、$0<z<H$ 且径向取完整平面的假设下，对印刷式积分得到：

$$\int_{0}^{H}\int_{\mathbb{R}^2}q\mathrm{d}A\mathrm{d}z=\frac{Q}{1-e^{-3}}\approx1.052396Q$$

若再加上径向截断 $r^2\le\ln(H/z)/C_s$，径向保留比例为 $1-e^{-3}$，上述积分才成为 $Q$。
这只是解释归一化因子所需的一种数学支撑域，不证明作者采用了该截断。
原文未提供完整实现；$z=0$、$z=H$ 附近的极限及从模型负坐标到正深度的映射均需处理。
优先采用已明确支撑域的[复合高斯形式](../laser-composite-gaussian.md)，或对选定的新形状重新积分。

## 3. 糊状区阻尼与反冲压力

LV2024，PDF p.2 Eq.6 印刷形式含 $(1-\beta^2)/(\beta^3-\varepsilon)$。
当 $\varepsilon=0.001$ 时在 $\beta=0.1$ 出现分母零点，且不能保证动量耗散。
采用右端体积力约定时，常用焓-多孔介质阻尼结构为：

$$\mathbf S_m=-C_m\frac{(1-f_l)^2}{f_l^3+\varepsilon}(\mathbf u-\mathbf u_s),\qquad C_m>0,\quad\varepsilon>0$$

实现要检查 $\mathbf S_m\cdot(\mathbf u-\mathbf u_s)\le0$，以及液体 $f_l\to1$ 时阻尼消失。
若移到方程左端，符号随之调整。$f_l$ 是金属内部的液相分数，不能与 VOF 金属体积分数混同。

LV2024，p.3 Eq.9 的反冲压力指数使用汽化潜热与气体常数。若潜热为 J/kg 而 $R_u$ 为 J/(mol·K)，须转换为摩尔潜热，或使用质量比气体常数。前一种写法的指数为：

$$\frac{L_v M(T-T_b)}{R_uTT_b}$$

其中 $M$ 为 kg/mol，温度均为 K。表1的 8.314 与 J/kg 潜热不能不经转换直接相除。

## 4. 声强、吸收热与时间尺度

LIU2022，PDF p.6 Eq.22 印刷为 $I=P_A/(2\rho c)$，按声压定义不能得到声强单位。
在线性平面行波假设下，应区分峰值与 RMS：

$$I=\frac{p_{\mathrm{peak}}^2}{2\rho c}=\frac{p_{\mathrm{rms}}^2}{\rho c}$$

Eq.20 的 $p_{\mathrm{peak}}=2\pi f\rho cA$ 也依赖同一行波/阻抗假设，不能仅凭振荡器额定振幅替代薄板接触位置的实际声场。
若 $\alpha_a$ 是声压振幅的吸收衰减系数（1/m），局部吸收热率为：

$$\dot q_{\mathrm{us}}=2\alpha_a I,\qquad E_{\mathrm{us}}=\int\dot q_{\mathrm{us}}\mathrm{d}t$$

原文 Eq.21 的 $Q=2\beta It$ 是恒定条件下的累积能量密度；热源节点应填热率。
若采用声强而非声压的衰减系数，需相应调整系数 2。发生器电功率、接触机械功率和工件吸收声功率分别核对，避免重复计热。

LIU2022 的 $f=34750$ Hz 给出周期 28.78 μs；1 ms 跨越 34.75 个周期。
“每周期 20 点”的初始建议对应 $\Delta t\le1.44$ μs，随后仍需收敛检查。
若采用周期平均或频域模型，应说明近似和向热/结构模型的映射；论文没有完整披露足以复现此环节的设置。

## 5. 辐射与热力本构

LIU2022，PDF p.6 Eq.11 后写出的 $\sigma=0.5$ 不能作为 Stefan–Boltzmann 常数。
SI 值为 $5.670374419\times10^{-8}$ W/(m²·K⁴)；使用 mm² 时数值需再乘 $10^{-6}$，辐射温度使用 K。

同页 Eqs.13–18 印刷的应变乘号、$T+T_0$ 及主应力乘积等不应直接实现。
常用小应变分解和 von Mises 主应力表达为：

$$\boldsymbol\varepsilon_e=\boldsymbol\varepsilon-\boldsymbol\varepsilon_p-\boldsymbol\varepsilon_{\mathrm{th}}$$

$$\sigma_{\mathrm{vm}}=\sqrt{\frac{(\sigma_1-\sigma_2)^2+(\sigma_2-\sigma_3)^2+(\sigma_3-\sigma_1)^2}{2}}$$

热应变应以明确无应力参考温度计算；温度相关膨胀系数还需区分切线与割线定义。
优先使用求解器中适合当前变形尺度的材料本构，核对高温软化、硬化、液态区处理及冷却后的卸载状态。
