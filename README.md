# COMSOL Agent 工具包

用于把 Agent 的 COMSOL 接入、模型操作和批处理经验保存成可执行、可追溯的工具。
版本：`0.2.0`；来源复核日期：2026-09-06。

推荐保存方式是 **Skill＋代码仓库**。`SKILL.md` 告诉 Agent 如何选择接口和核验结果，
Python/MCP 与 Java/MATLAB 示例负责执行，GitHub 保存版本和分发历史。
当前目录可独立运行、安装或压缩分发；也可以直接作为个人 GitHub 仓库的根目录。
个人私有仓库：[zouguozhao/comsol-agent-toolkit](https://github.com/zouguozhao/comsol-agent-toolkit)。
后续完善实时接入验证和许可证选择后，再决定是否公开。

本项目是社区接入组合，不是 COMSOL、MathWorks 或 OpenAI 官方产品。
COMSOL 和 MATLAB 的程序、许可、模型与专有文档不随工具包分发。

## 可复用建模知识

- [激光与超声焊接知识索引](references/welding/index.md)：按熔池热流、热源校准、残余应力和超声机制选择方案；包含吕成（2024）与 Liu 等（2022）的证据和复用限制。
- [激光焊接复合高斯热源](references/laser-composite-gaussian.md)：守恒公式、可复制的COMSOL表达式、半模型功率检查与参数标定要点。

Codex 在本仓库工作时可从 [AGENTS.md](AGENTS.md) 进入；使用 Skill 时由
[SKILL.md](SKILL.md) 按需加载知识。领域方法保存在 `references/welding/`，与执行接口分开维护。

## 能力与选型

| 层次 | 实现与用途 | 验证边界 |
| --- | --- | --- |
| 基础检查 | 标准库发现 COMSOL、检查 MPH ZIP | 不启动 JVM；结果条目不证明收敛 |
| 可复现建模与计算 | 原生 Java API、comsolcompile、comsolbatch | 具体模型仍须做物理和数值验证 |
| 本地 Agent 工具 | 11 个 MCP stdio 工具，或直接 Python CLI | 最小 tools 协议；非完整通用 MCP 服务平台 |
| 实时模型操作 | 可选 MPh/JPype，统一原生 Java Model 句柄 | 当前版本尚未完成真实共享 Server 回归 |
| 同一模型树协作 | 外部 sim-cli＋sim-plugin-comsol | 按 Server/Tag 和 GUI 绑定状态验收 |
| MATLAB | 官方 MATLAB MCP＋LiveLink 模板 | 当前机器未发现 MATLAB；仅提供模板 |

详细来源与采用理由见 [上游调研](references/upstreams.md)，本机验证结果见
[验证记录](references/validation.md)。不随“最后更新时间”自动切换后端，也不自动升级依赖。

## 快速使用

以下命令从本目录执行。基础 CLI 和 MCP 握手仅需 Python 3.10+，不要求安装 Python MCP 包。
MPh 实时接口需要与 COMSOL 匹配的本机 Python、MPh 和 JPype；不要使用 WSL Python
直接加载 Windows COMSOL 的 JVM。

```powershell
python scripts/comsol_bridge.py discover
python scripts/comsol_bridge.py inspect-mph "<existing-model.mph>"
python -m unittest discover -s tests -v
```

显式指定 COMSOL 安装目录进行发现检查：

```powershell
python scripts/comsol_bridge.py discover --root "<COMSOL_INSTALL>"
```

`discover --root` 只影响本次检查；其他命令使用自动发现或启动器传入的进程级
`COMSOL_ROOT`。支持 `COMSOL_HOME`、`COMSOL_PATH` 和 `COMSOL_SEARCH_ROOTS`。

Java 自检示例：

```powershell
python scripts/comsol_bridge.py compile assets/BlockSmoke.java --work-dir "<scratch-directory>"
python scripts/comsol_bridge.py batch "<returned-class-file>" --work-dir "<scratch-directory>" --cores 2
python scripts/comsol_bridge.py job-status "<returned-job-file>"
```

编译会先复制源文件到独立构建目录。批处理创建独立任务目录，保存退出码、命令和日志，
输出目标始终与输入分开。观察等待上限为 60 秒，超出后返回任务路径继续查询。
默认计算等待只有 1 秒，返回 `running` 是正常状态。进程退出码为零后，仍需核对输出
MPH、日志和任务要求的指标。大型作业可直接使用 COMSOL 原生 batch/HPC 调度工具。

## 作为 Skill 安装

指定 Agent 已配置的 `skills` 父目录；安装器会创建其中的 `comsol-agent-toolkit/`：

```powershell
python scripts/package_skill.py --install "<agent-skills-directory>"
```

安装器只复制清单文件，拒绝覆盖同名目录。VibeFlow 使用其 Agent runtime 的 `skills`
目录；Codex 使用个人 skills 目录。刷新技能列表或新建会话后，可输入：

```text
$comsol-agent-toolkit 检查这个 MPH，并列出几何、物理和研究的后续核验步骤。
$comsol-agent-toolkit 把已经验证的 Java 建模程序编译并批处理执行，保留日志和新模型。
```

Skill 安装不注册 MCP，不安装 COMSOL/MATLAB，不改变系统环境变量。

## MCP 接入

通用客户端配置示例，路径请填写为实际绝对路径：

```json
{
  "mcpServers": {
    "comsol-agent-toolkit": {
      "command": "<absolute-python-executable>",
      "args": ["<absolute-toolkit-directory>/scripts/comsol_mcp.py"]
    }
  }
}
```

Codex 配置形状示例，供在用户已授权的配置位置登记：

```toml
[mcp_servers.comsol_agent_toolkit]
command = '<absolute-python-executable>'
args = ['<absolute-toolkit-directory>/scripts/comsol_mcp.py']
```

工具参数和实时连接步骤见 [操控指南](references/control-guide.md)。本次只提供配置内容，
并未自动修改任何客户端配置。对会话命令和长任务，按宿主客户端的工具超时设置运行。

## 打包与 GitHub 发布

```powershell
python scripts/package_skill.py
python scripts/package_skill.py --zip "<distribution-directory>/comsol-agent-toolkit-0.2.0.zip"
```

打包内容来自 `manifest.json`，附 SHA-256 文件清单。压缩包不包含运行时日志、生成的
`.class`、`.mph`、案例文件或机器配置。上游源码采用链接和固定 SHA 追溯，未把第三方
仓库直接捆绑进来。发布前仍应检查所选清单文件的内容是否适合目标仓库。

发布准备与许可证建议见 [发布说明](references/publishing.md)。每次更新均先核对仓库
目标、私有可见性及分发清单；本目录的脚本不会保存或访问 GitHub 凭据。

## 文件组织

```text
comsol-agent-toolkit/
  SKILL.md                  Agent 操作入口
  agents/openai.yaml        技能显示信息
  scripts/comsol_bridge.py  发现、归档、实时会话、编译和任务
  scripts/comsol_mcp.py     11 个 stdio 工具
  scripts/package_skill.py 清单、安装和压缩包
  assets/                  Java 自检与 MATLAB 附着模板
  references/              操作、选型、来源、验证、发布记录
  tests/                   无许可证回归测试
  manifest.json            显式分发文件清单
```
