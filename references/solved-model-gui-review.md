# 已求解 MPH 的 GUI 检查与流向箭头出图

本流程适用于用户给出已有 `.mph`，要求在 COMSOL Desktop 检查模型树，并从其**已保存的解**输出流场图。它记录了 2026-09-27 的一次 COMSOL 6.4 实测：Desktop 成功打开 7075 叠焊流动模型；独立 Java 后处理读取同一 MPH，导出横截面速度图。该实测**没有**证实 Agent 与 Desktop 的共享实时模型绑定，也没有重新求解。

## 1. 先明确任务与案例定义

1. 读取案例的 `0-caseDict/caseDict`、目标 MPH、建模源码和求解日志。`caseDict` 是工况参数来源；MPH 是待检查的执行产物。若两者不一致，记录差异，不能把旧 `caseDict` 的参数写成当前 MPH 的参数。
2. 使用 `python scripts/comsol_bridge.py discover` 找 COMSOL；使用 `inspect-mph <path>` 做只读归档检查。归档可读只说明文件结构可读，不证明物理场已求解。
3. 记录 MPH 的绝对路径、大小和修改时间。若有多个同名/类似模型，使用明确文件路径，不从文件名猜研究类型或解时刻。

## 2. 用可见 Desktop 检查

Windows 命令形状：

```powershell
& '<COMSOL_INSTALL>\bin\win64\comsol.exe' -open '<MODEL.mph>'
```

启动后在 COMSOL Desktop 的模型开发器中检查组件、几何、网格、物理场、研究、解、结果图组；根据需要点击对应节点，观察实际图形窗口和设置。记录节点标签/Tag、研究类型、图像或截图，以及弹出的错误。不要仅凭窗口标题宣布模型正常。

**边界：**这一步打开的是磁盘 MPH 的 Desktop 副本。另一个进程通过 API 加载同一文件，两个进程的模型树不会自动实时同步。若目标是实时观察 Agent 对同一个模型的构建或求解，转到[共享 Server 验收](control-guide.md#实时可见工作流与验收)，逐项核对 Server、Tag 和界面变化。

## 3. 用 API 只读核对实际解

在独立目录用 COMSOL Java API 加载原始 MPH，打印或记录：

- 组件及物理接口 `model.component("comp1").physics().tags()`；
- 研究步骤 `model.study("std1").feature().tags()`；
- 数据集 `model.result().dataset().tags()` 与解时间 `model.sol("sol1").getPVals()`；
- 图需要的参数、变量、单位和所选时刻；
- 已有 Derived Values，尤其功率积分、最高温度、熔化区域和速度指标。

`comp1`、`std1`、`sol1`、`dset1` 只是案例示例，必须先从目标模型核对真实 Tag。只读加载可在一次后处理脚本中完成；批处理日志要保留。若 MPh 连接 Server 报 `Unable to start Jetty client container`，记录原始异常并核查 Server/许可/JVM；不要在同一已启动 JVM 的 Python 进程中反复创建 `Client`。可以继续使用 Desktop 检查和独立 Java 后处理，但必须明确共享实时绑定未验证。

## 4. 生成熔池流向图

对三维解创建 `CutPlane`，指定切面与位置，再建立 2D 绘图组：

1. `Surface`：速度模量，注明参考系及单位。例如移动参考系模型要看材料相对流动时，可用 `sqrt((u+v_adv)^2+v^2+w^2)`；先核对模型中 `u,v,w,v_adv` 的定义。
2. `Contour`：用模型自身的 `T_liq` 与 `T_sol` 标出液相/糊状区边界，绝不可套用另一工况的温度。
3. `ArrowSurface`：在切面内显示速度分量。例如 yz 面箭头 `(v,w)`；若在材料参考系下画包含 x 方向的切面，则 x 分量按该模型定义使用 `u+v_adv`。用 `planecoordsys=cutplane` 避免截面坐标与全局坐标混淆。
4. 仅在目标温度区域显示箭头，例如乘以 `(T>=T_sol)`。控制箭头位置和比例，避免覆盖流场。`arrowlength=normalized` 的箭头只能读方向，图注明确写出这一点。
5. 输出 PNG 到案例的 `D-post/figures/`，将脚本与日志放在 `D-post/`。若保存带新绘图节点的 MPH，必须用新文件名；原始 MPH 保持不变。

本次可运行的案例脚本保存在案例目录 `D-post/InspectMeltFlow.java`。其切面、视野、变量、标签和输出路径针对 7075 叠焊模型，复制到其他模型前必须逐项修改。Windows 执行形状如下：

```powershell
& '<COMSOL_INSTALL>\bin\win64\comsolcompile.exe' '<CASE_ROOT>\D-post\InspectMeltFlow.java'
& '<COMSOL_INSTALL>\bin\win64\comsolbatch.exe' -inputfile '<CASE_ROOT>\D-post\InspectMeltFlow.class' -batchlog '<CASE_ROOT>\D-post\logs\flow_review.log' -np 2
```

COMSOL 可能在 class 所在目录另外生成默认 MPH；不要把它误认为指定的图像产物。核查 COMSOL 进程退出码、日志末尾的成功标记、目标 PNG 存在且非空，并**目视检查**箭头是否遮挡、等温线是否正确、坐标/单位/色条是否可读。

## 5. 实测验收与限制

| 核查项 | 7075 案例实测 |
| --- | --- |
| GUI | COMSOL 6.4 Desktop 打开 `PointRing7075Lap_3D_flow_moving_steady.mph`，模型树可见研究和结果图组 |
| 物理与研究 | `ht`、`spf`；`time` 研究，0–0.4 s 共 21 个保存时刻 |
| 图像 | x=0 mm 的 yz 截面，取 0.4 s；速度底图和 `(v,w)` 流向箭头成功导出并目视检查 |
| 热量输入 | 光学功率 480/200 W、吸收率 0.65/0.20；末时刻积分吸收功率 312/40 W |
| 已知差异 | 原 `caseDict` 仍描述较早的仅传热工况；当前 MPH 的液相线为 908 K |
| 尚未验证 | Agent 与 Desktop 实时绑定、0.4 s 稳态充分性、网格收敛、实验标定 |

该模型末时刻最高温度约 2815.93 K，高于模型设定沸点 2740 K。图只呈现这个 MPH 已有数值解；最高温度、极端局部速度以及熔池尺寸均不能未经独立验证就作为可信物理预测。案例和模型路径仅用于说明，不随本库分发 MPH、图片、许可文件或机器配置。
