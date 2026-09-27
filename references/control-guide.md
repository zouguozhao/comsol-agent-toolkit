# 接入和操控指南

## 接口选择

Java API 是原生建模能力来源，MPh 是 Python 到 Java API 的桥，LiveLink 是 MATLAB
到 COMSOL 的桥，MCP 是 Agent 调用本地工具的协议。组合时按当前工作需要选择，
不要求同时启动所有服务。没有任意一层就绪时，不把另外一层的成功当作它的验证。

## MCP 工具

| 工具 | 必填参数 | 作用 |
| --- | --- | --- |
| `comsol_discover` | 无 | 发现安装；可选 root |
| `comsol_inspect_mph` | path | 只读归档元数据 |
| `comsol_status` | 无 | 当前 Server/Tag 状态 |
| `comsol_connect` | 无；实际应明确 host、port | 附着已有 Server；可选 model_tag |
| `comsol_bind_file` | path | 同机加载或复用，tag 可选 |
| `comsol_describe` | 无 | 参数、组件、研究、解标签与检查错误 |
| `comsol_set_parameters` | values | 参数表达式映射，写入并读回 |
| `comsol_save_model` | path | 新 MPH 检查点；覆盖需 overwrite=true |
| `comsol_compile_java` | source、work_dir | 独立目录编译单 Java 文件 |
| `comsol_run_batch` | input_file、work_dir | 独立任务；cores 默认 2，study 可选 |
| `comsol_job_status` | job_file | 查询同一任务和日志 |

MCP 实现支持 initialize、ping、tools/list、tools/call 和通知处理，协商
2024-11-05、2025-03-26、2025-06-18 协议版本。它没有 HTTP 监听、远端认证、资源订阅、
任务取消或多租户服务功能。不要把 stdio 服务直接当作公共网络服务。

## 共享 Server 与 Desktop

先确认已有 Server 的端口与活动模型。MPh `Client` 是进程级 JVM 单例，首次连接失败
而 JVM 已启动时，应重启接入进程；不能连续新建 Client 来尝试修复。

Python 文件操作限定为同机 Server，避免本地和远端文件路径语义混淆。远端服务器可以
按明确 Tag 连接和读改参数；跨主机加载、保存应交给已有的远端执行/路径映射层。

本工具包只附着已有 Server，不自动启动 Server。需要由工具创建和管理实时 Desktop
时，使用安装好的 sim-cli 与插件（这些依赖未包含在本包中）：

```powershell
uv run sim check comsol
uv run sim connect --solver comsol --ui-mode gui --driver-option visual_mode=shared-desktop
uv run sim inspect session.health
uv run sim inspect comsol.model.identity
```

用户已经打开了 Server 和与之连接的 Desktop 时，优先 attach-only：

```powershell
uv run sim connect --solver comsol --ui-mode no_gui --driver-option attach_only=true --driver-option port=<port>
uv run sim inspect session.health
```

用插件工作时在同一会话内操作已有句柄，不另开本工具的 MPh 连接抢占会话。需要
API 读写时按 tags、properties、selection 实体、读回结果的顺序确认，保存检查点。

要声称 Desktop 与 Agent 同步，应实测：`ui_capabilities.model_builder_live=true`、
`active_model_tag` 与目标一致、`live_model_binding.ok=true`。在普通 Desktop 直接打开
磁盘上的 MPH 通常是一个检查副本，不会自动随其他 Server 模型的 API 修改刷新。

启动一个明确归属的本地 Server 的原生命令形状如下；仅在用户任务需要启动时执行：

```powershell
& '<COMSOL_INSTALL>/bin/win64/comsolmphserver.exe' -port <port> -multi on -login auto -silent
& '<COMSOL_INSTALL>/bin/win64/comsol.exe' mphclient -host localhost -port <port>
```

端口能连接只说明有监听者，还要由 COMSOL API 成功握手、读取 Tag 才能证明接入。
退出时本包不清空模型，也不主动停止外部 Server；未用 `-multi on` 的 Server 可能
按自己的设置在断开时停止。长时间无响应时核对完整命令、PID 与任务文件，不按名称杀进程。

## 实时可见工作流与验收

需求记录（2026-09-27）：用户希望调用工具时实时看见 COMSOL 的模型树、几何、
网格和求解过程。这是可见工作流的验收目标，当前状态为要求已记录、实现及真实
GUI 验证待完成。

### 执行顺序

1. 发现 Windows COMSOL 安装、匹配的 Windows Python/MPh 和所需许可证；记录
   COMSOL 版本及采用的接入方式。不要使用 WSL Python 加载 Windows COMSOL JVM。
2. 优先附着用户已有的共享 Server/Desktop；需要新建时使用明确的 host/port，
   按上文接入步骤启动可见 Desktop，记录本次创建的 PID 与服务归属。
3. 核对 API 与 Desktop 连接的是同一个 Server、同一个模型 Tag；已有模型应复用，
   不另行加载同一路径的模型副本。外部插件的绑定字段需结合实际界面变化验收。
4. 在同一模型上修改一个可核验参数，确认读回正确并观察模型树或参数表更新。
5. 在共享模型上执行几何序列，确认 Desktop 图形窗口显示本次构建的几何；再执行
   网格序列，确认网格显示与模型的单元计数一致。按安装版本支持的方式选择节点、
   刷新或重绘，不能假定 API 返回后 GUI 必然自动更新。
6. 在共享模型上执行研究，运行期间观察 Desktop 的求解进度或持续更新的求解日志。
   求解结束后核对研究/解状态并保存新的 MPH 检查点。中间场的实时刷新需要另行
   验证，本要求不承诺每个时间步都自动显示结果场。
7. 保留步骤、模型身份、日志与 GUI 证据。求解报错时保留共享模型和错误信息，
   不重复启动独立 batch 来替代可见运行。

### 验收表

| 项目 | 通过条件 | 应保存的证据 |
| --- | --- | --- |
| 模型身份 | API 与 Desktop 操作同一 Server/Tag | host、port、Tag、原始文件与绑定核对记录 |
| 模型树 | API 修改后 Desktop 显示对应节点或参数变化 | 修改前后值、读回值及界面证据 |
| 几何 | 构建完成后可见本次几何 | 几何序列状态、尺寸核对与界面证据 |
| 网格 | 生成后可见本次网格 | 单元计数、网格状态与界面证据 |
| 求解过程 | 求解运行期间可见进度或更新的求解日志 | 运行期间证据、完成或失败状态及日志 |

无许可证的模拟对象测试只验证接口逻辑，不能把表中的项目记为 GUI 实测通过。
轻量实际验收应使用包含物理场与研究的最小案例；现有 `BlockSmoke.java` 只有几何
与网格，不能用来证明求解过程可见。工程模型仍按案例定义做独立物理/数值验证。

### 后续实现边界

工具包后续需要补充可见 Desktop 会话创建/附着、模型身份检查、共享模型的几何/
网格/研究执行、进度查询及 GUI 显示更新能力。这些是待实现能力，不是现有 MCP
工具名或可直接调用的参数。现有 `comsol_run_batch` 保留后台用途；移除
`CREATE_NO_WINDOW` 无法把 batch 转换为共享 Desktop 工作流。

## 批处理验收与续查

每个任务生成 `job.json`、stdout/stderr 日志、COMSOL batch 日志和独立 MPH 输出。
`state=finished` 表示启动器已返回；`process_ok=true` 只表示返回码为零。
仍须检查 batch 日志是否有求解错误、MPH 是否可读、预期节点与指标是否存在。
Java 自检的 `TOOLKIT_GEOMETRY_BUILT` 与 `TOOLKIT_MESH_ELEMENTS` 是执行证据；
它没有求解物理场。

等待结束不会停止批处理。CLI/MCP 返回 job_file 后，用 job-status 续查。机器关机、
工作进程被外部终止或许可证对话阻塞都可能使状态留在 starting/running；先核对进程
及日志后决定重启。没有有效 COMSOL 检查点时应称为“重新运行”，不能承诺继续原求解。

编译只包装单 Java 源文件；复杂多文件项目、额外 JAR 或特殊 JVM 参数使用 COMSOL
原生编译/执行工具。Java 中明确模型名称和工作目录，避免把源文件所在目录当作输出目录。
保存 Java 源码要用 `model.save(path, "java")`；仅把 batch 输出扩展名写成 `.java`
不会可靠转换 MPH 容器格式。

## MATLAB 可选链路

官方来源是 `matlab/matlab-mcp-server`，旧 `matlab-mcp-core-server` 地址当前会重定向。
社区 `WendyAi2005/codex-comsol-bridge` 提供组合工作流，它本身不属于官方桥接产品。
真实使用仍需 MATLAB、LiveLink for MATLAB、COMSOL 和所需许可证。

模板 `assets/comsol_agent_livelink.m` 需要 MATLAB R2019b+ 的 arguments 语法；若通过
官方 MATLAB MCP 使用，还须满足其当前 MATLAB 版本要求（此次 README 为 R2021a+）。
COMSOL/MATLAB 版本配对以安装版本的官方支持表为准。

在 MATLAB 中把 assets 加入路径后，调用：

```matlab
identity = comsol_agent_livelink('localhost', 2036, 'ExistingTag', '<COMSOL_INSTALL>/mli');
```

这是函数，不能用 `run('comsol_agent_livelink.m')` 代替传参调用。模板只连接并检查
指定模型；不吞掉连接异常，不加载第二份模型、不自动求解。已有 LiveLink 连接时
复用原会话的 `model`，不要重复 mphstart。真实验证应另做连接、参数写入读回、
新路径保存和需要的求解；本包没有把静态模板检查记为 LiveLink 实测通过。
