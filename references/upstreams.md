# 上游调研与组合方案

核验日期：2026-09-06。采用 GitHub REST API 获取默认分支提交，再读取固定 SHA 的
`raw.githubusercontent.com` 原始文件。检索词包括 `comsol mcp`、`comsol agent`、
`comsol matlab livelink`，按更新时间取每组前 8 个结果，再逐一复核原有重点候选。
这是定向检索，不声称穷尽全部项目，也不把本地副本当作远端当前版本。

完整提交 SHA、已读文件和失败路径见 [来源清单](upstream-sources.json)。
表中许可证是当前证据摘要；如果将来复制源码，须再读取该提交的完整许可文件。

| 原始仓库与已核对提交 | 依据与定位 | 采用决定 |
| --- | --- | --- |
| [svd-ai-lab/sim-cli](https://github.com/svd-ai-lab/sim-cli/tree/b69c7be7119789f6de3538eac1db8d2cf7a30ef5) | README；提交发布 0.3.9；Apache-2.0 | 可选 Agent 会话与文件检查编排 |
| [svd-ai-lab/sim-plugin-comsol](https://github.com/svd-ai-lab/sim-plugin-comsol/tree/770999a377b08706e80be7a269c80a2f4f32aab8) | README、pyproject；0.1.14；mph>=1.2,<2.0；Apache-2.0 | 可选共享 Desktop、原生 API 检查；基础 batch 不依赖插件 |
| [MPh-py/MPh](https://github.com/MPh-py/MPh/tree/30e0cff361d680249bae5c29f7873a29f1639c5d) | client.py、model.py、pyproject；1.4.0；MIT | Python 实时接入首选，保留原生 Java API |
| [XiaoSe532/comsol-codex-mcp](https://github.com/XiaoSe532/comsol-codex-mcp/tree/ecf220a09b459ca0b7f6fd1d95dbed63ffee4f26) | README 与 tools.py；MIT | 参考 Java 编译、batch、日志与交付范围；没有捆绑其源码 |
| [WendyAi2005/codex-comsol-bridge](https://github.com/WendyAi2005/codex-comsol-bridge/tree/294dbd341705e012c025b1774c00b80106c6ebcb) | README；社区项目，MIT | 参考 MATLAB MCP → LiveLink → COMSOL 的组合 |
| [matlab/matlab-mcp-server](https://github.com/matlab/matlab-mcp-server/tree/2e44b0ac789f43083cc29f5dce9079244b081a4c) | 官方 README、LICENSE.md；自定义 MathWorks 许可 | MATLAB 可选入口；原 matlab-mcp-core-server 地址重定向到此仓库 |
| [Howard-Lai/COMSOL_MCP](https://github.com/Howard-Lai/COMSOL_MCP/tree/fcf01a874e97866d808a86c537c140456e4cd9d5) | README、BUGFIXES_2026-08-06.md；MIT | 保留 API 修复经验参考；已知仍有边界查询和材料占位等缺口 |
| [Twofruitsgrape/comsol-mcp](https://github.com/Twofruitsgrape/comsol-mcp/tree/66b74f7f68789005750d602561095647fb6808b2) | README；MIT | 共享 Server 的轻量示例参考；GUI 同步仍须按具体 Tag 实测 |
| [wjc9011/COMSOL_Multiphysics_MCP](https://github.com/wjc9011/COMSOL_Multiphysics_MCP/tree/99172f8f43c6753c2442c406cd5c6055ea8c5bef) | README，通用建模工具与扩展；MIT | 有价值的备选完整 MCP 工具集；当前包先保留较小的可追溯接口 |
| [joker-anyway/matlab-comsol-automation](https://github.com/joker-anyway/matlab-comsol-automation/tree/762568af0a1c17c214b43ae58e106ece83f2e67e) | README、SKILL；9 月新增，MIT | 参考已有模型预检、分阶段求解和保留基线的工作方式 |
| [fatdog-pro/Comsol-automatic-wwj](https://github.com/fatdog-pro/Comsol-automatic-wwj/tree/f588c86f56ef105d6eb335eac560752847ebf7a8) | 9 月 5 日提交的树只有 README.md | 文中声称的 server/scripts/LICENSE 未在该提交中提供；不作为可安装代码采用 |

## 为什么这样组合

原生 Java API 决定 COMSOL 能建立和修改哪些模型；固定 MCP 工具集只能覆盖它包装过的
部分。通用建模保留 Java 配方的通路，实时探索保留 MPh 的 `.java`，因此不需要为每种
物理场增加一整套同名 MCP 工具。实际可用接口仍取决于 COMSOL 版本与许可证。

确定的重复流程使用原生编译和 batch；需要实时询问模型形状、属性和选择时使用
MPh/插件；需要同一个 Model Builder 树时检查 shared-desktop 绑定；已有 MATLAB
工作流时才加入官方 MATLAB MCP 和 LiveLink。每条路径独立验收，再组合使用。

MPh 远端 1.4.0 的 `Client.load()` 返回 `mph.Model`，原生 Java 句柄在 `.java`；
`ModelUtil.model(tag)` 和 `ModelUtil.load(tag, path)` 返回 Java Model。
旧原型把两者放进同一成员后直接调用 `.param()`，存在接口混用问题。本包统一使用
原生 Java Model，并添加 Tag/文件对应检查。

本机 MPh 为 1.3.1；上游 1.4.0 的源码核对不等于本机已升级或运行验证。
插件说明中的旧 MPh 1.2.x 描述不应覆盖远端 pyproject 的实际兼容范围与本机检测。

GitHub API 对 MATLAB MCP 标注 `NOASSERTION`，实际 LICENSE.md 第三项限制与
MathWorks 产品/服务共同使用；不应将其标记为 MIT。fatdog 项目 README 提到 MIT 和
99 个工具，但该固定提交里没有这些实现及许可文件，也没有把外链附件当作已安装仓库。

## 后续更新方法

用户要求重新核验“最新”时，先更新仓库默认分支 SHA，再比较本包实际依赖的文件和
接口。保存新日期、提交、采用理由及测试结果。不可仅因为 pushed_at 改变就换掉已验证
后端；也不可只因星标、README 功能数量或更新时间认定兼容和可靠性。
