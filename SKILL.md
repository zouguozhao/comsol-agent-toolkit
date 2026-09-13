---
name: comsol-agent-toolkit
description: "通过 Python/MCP、COMSOL Java batch 和可选 MPh/LiveLink 检查与操作 COMSOL 模型；也可按已核查文献制定激光及超声焊接方案，选择热源、热流或残余应力路线。"
---

# COMSOL Agent 工具包

把已核验的接入方法用于当前任务。先区分“工具可以调用”和“该物理模型已经验证”。
本 Skill 的脚本可直接运行；阅读或安装 Skill 不会自动注册 MCP，也不会启动 COMSOL。

## 选择入口

| 当前任务 | 入口 |
| --- | --- |
| 看已有 MPH 的版本、归档结构和结果条目 | `scripts/comsol_bridge.py inspect-mph <file>`；无需 COMSOL 许可 |
| 查安装位置 | `scripts/comsol_bridge.py discover`；可用 `--root <install>` |
| 执行已确定的任意物理场 Java 配方 | `compile` → `batch` → `job-status`；需要 COMSOL 和对应模块许可 |
| 查看现有 Server 模型、改参数、存检查点 | MCP 中的 connect、bind、describe、set、save；需要 Python MPh |
| 用户要求实时看到同一模型树 | 优先现有 `sim-cli`＋`sim-plugin-comsol` 的 shared-desktop；见接入指南 |
| 用户已有 MATLAB/LiveLink 工作流 | 使用 LiveLink 模板及官方 MATLAB MCP；见接入指南 |
| 制定激光/超声焊接方案或复用文献 | 先读 [焊接知识索引](references/welding/index.md)，再按目标选读；采用方程时查 [公式核查](references/welding/formula-audit.md) |

制定焊接方案时，区分原文工况、核查结果与工程建议。用用户材料、几何和分析目标
选择最小模型，明确校准/独立验证数据，并引用文献页码。论文参数不替代案例参数。
只做文献方案分析时无需启动 COMSOL，也无需读取与当前路线无关的全部文献。

操作命令、接口边界和共享 Desktop 接法见 [references/control-guide.md](references/control-guide.md)。
需要了解选型、更新依赖或用户要求“最新项目”时，读取
[references/upstreams.md](references/upstreams.md) 与
[references/upstream-sources.json](references/upstream-sources.json)，再查询原始仓库当前提交。
不能把固定日期的追溯清单当作永久最新版本。
向用户报告兼容性前，读取 [references/validation.md](references/validation.md)。

## 实际执行

1. 确定用户要检查、修改、建模、求解还是发布工具；保持该范围。使用模式下如有
   `0-caseDict/caseDict`，以它作为物理与数值参数来源。工具自检例子不是工程工况。
2. 先发现 COMSOL 与当前解释器。离线检查和批处理不依赖 MPh；没有 sim-cli
   也不代表 COMSOL 不可用。需要未知 feature/property 时，查询安装版本的官方文档
   或用现有模型的 Java API 查看 `tags()`、`properties()`、选择维度及实体。
3. 选实时路径时先核对 host、port、Tag 和原始文件。一个 Python 进程只启动一个
   MPh/JPype JVM；已有 `model` 句柄时复用它。Tag 与文件冲突必须查明，不能静默改绑。
   不能通过扫描相邻开放端口来认定它属于自己的 COMSOL Server。
4. 实时修改按几何、材料、物理、网格、研究分步核验；在需要下游更新时运行对应序列，
   保存到显式的新检查点。`set_parameters` 本身不会重建、求解或验证参数依赖。
5. 稳定配方用 Java 链式 API；示例是 `model.component("comp1").geom("geom1")`。
   不猜测不存在的 `Component`、`HeatTransfer` 等声明类型。用编译、日志、实际输出和
   所需数值指标判断执行结果。批处理 Java 可以执行任意代码，应按任务审查源文件。
6. 批处理返回 `job_file` 后一直查询同一任务。`starting/running`、工具等待超时和
   日志暂时不变都不表示求解器失败；先核对任务、PID、日志和输出，不能立即重复启动。
   工作者进程异常消失时状态可能停留在 running，需检查进程与日志后处理。
7. 区分四类证据：容器可读、进程正常退出、模型流程完成、物理/数值验证通过。
   `solution_data_present`、`process_ok` 和截图均不能单独证明解收敛或物理正确。
8. 输出相关文件路径、验证结果、限制和下一步。接入工具不替代网格与时间步独立性、
   守恒检查和实验对照。VibeFlow 案例按项目规则更新工作流记录。

## 模型与发布边界

- 文件锁只协调本工具的写入，无法阻止用户或其他软件保存。默认保存新文件；
  原文件覆盖必须有用户针对该目标的授权。
- `connected=true` 不代表 GUI 同步。共享 Desktop 必须绑定同一 Server 的活动 Tag，
  并检查 `model_builder_live`、`active_model_tag`、`live_model_binding.ok`。
- 不执行 `ModelUtil.clear()`，不按进程名批量终止 COMSOL。断开外部 Server 时尊重
  它原有的生命周期策略；希望 Server 保持运行须先核对 `-multi on`。
- 打包或安装使用 `scripts/package_skill.py` 的显式清单。完整脚本与引用文件一并保留。
  上传前确认目标仓库及可见性；不包含案例 MPH、结果、许可文件和用户配置。

## 自检

从工具包根目录执行 `python -m unittest discover -s tests -v`。
需要测试 COMSOL 时编译 `assets/BlockSmoke.java`，在独立目录运行并核对几何、网格计数
和新 MPH；这只是几何/网格及 Java 通道测试，不进行物理求解。
