# 验证记录

日期：2026-09-06；工具版本：0.2.0。验证环境为 Windows、Python 3.11.9、
COMSOL Multiphysics 6.4.0.293。本机 MPh 1.3.1；远端 MPh 1.4.0 仅完成源码核对。

| 验证项 | 实际结果 |
| --- | --- |
| 标准库回归测试 | `python -m unittest discover -s tests -v`：17 项通过 |
| 文件和身份边界 | 跨进程锁、Tag/路径冲突、同文件复用、拒绝隐式覆盖、旧 class 不误报通过 |
| MCP 进程协议 | 实际子进程完成 initialize、ping、tools/list、非法 JSON 恢复与通知处理 |
| MCP 实际工具调用 | 通过 stdio 完成 COMSOL 发现及新 MPH 的归档检查，3 条请求响应有效 |
| Java 编译 | `BlockSmoke.java` 经本机 comsolcompile 编译成功，returncode=0 |
| COMSOL batch | 独立任务正常退出，returncode=0；后台工作进程保存了日志和最终状态 |
| 参数化几何 | `ToolkitBlockSmoke` 模型、`L=10[mm]`、立方体几何创建完成 |
| 网格 | 613 个体单元；batch 日志报告最小单元质量 0.3228 |
| MPH 保存 | 新输出 `result_ToolkitBlockSmoke.mph`，145574 字节，13 个归档条目 |
| 归档检查 | 版本 `2092:COMSOL 6.4.0.293`，包含模型树、几何与 mesh1.mphbin |
| Skill 校验 | 官方 skill-creator quick_validate.py 返回 `Skill is valid!` |
| 分发清单 | 16 个真实文件，未包含 MPH、class、日志或机器绝对路径 |

自检没有定义物理场，也没有执行物理求解，因此 `solution_data_present=false`、
`solution_validated=false` 是预期结果。网格计数与质量只属于这个 10 mm 立方体自检，
不能推广为焊接网格质量或工程精度结论。

原始编译、batch 和输出证据保存在本次开发案例的
`UDF/toolkit-validation-20260906/compile-i6z_0ous/` 和
`UDF/toolkit-validation-20260906/batch-z05fvm8b/`，不随可分发包包含。
本地安装及压缩包完整性由项目中的交付记录另行记录。

## 修复与验证范围

- 统一 Java Model 句柄，避免 `mph.Model` 与原生对象混用；错误 Tag/文件绑定会显式失败。
- 编译先进入新目录，不把旧 class 当成本次编译成功；每个 batch 使用独立输出目录。
- 将首次任务分发发现的工作进程参数名不匹配修正为 `job_file`。确认旧尝试未启动
  求解器后重新进行自检；修正后的完整后台分发、COMSOL 执行和状态回传均通过。
- Windows 默认 GBK 导致外部 Skill 校验器读取中文 UTF-8 文件失败；使用
  `python -X utf8` 运行校验器后通过，没有改变系统编码设置。

上述实时模型相关测试使用模拟对象验证接口约束，不能解释为真实 MPh/Server 验证。
本版本未完成共享 Server 连接、Desktop 同步或 MATLAB LiveLink 的真实运行验证。
旧原型记录过 `Unable to start Jetty client container`；该历史问题没有在本轮
宣称解决或重新复现。需要这些功能时按操控指南做同机的连接、读改、保存与 GUI 验收。

批处理运行状态只记录本工具工作进程和 COMSOL 启动器的可观察结果；主机掉电、外部
终止工作进程或特殊子进程行为可能留下未完成状态，需核对进程、日志及模型证据。
安装 Skill 不等于 MCP 已注册；当前客户端的 MCP 配置只提供了示例，未自动修改。
