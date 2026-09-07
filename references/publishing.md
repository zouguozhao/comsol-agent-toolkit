# 保存与发布建议

推荐用独立仓库保存完整 Skill 和脚本，以 `SKILL.md` 作为 Agent 入口、`README.md`
作为使用入口。单份 MD 可以保留思路，但不会安装可执行代码、依赖或 MCP 配置；
GitHub 是版本管理和分发位置，同样不能替代安装与实际验证。

当前仓库为 [zouguozhao/comsol-agent-toolkit](https://github.com/zouguozhao/comsol-agent-toolkit)，
按用户要求创建为私有。仓库描述：
“面向 Agent 的 COMSOL 接入工具：MPH 检查、Java batch、可选 MPh/LiveLink 与可追溯 Skill。”

当前目录是可审查的发布内容。使用 `manifest.json` 和 `package_skill.py` 生成分发包；
不要把所在焊接项目的根目录作为提交范围。无需上传本地安装路径、案例、求解结果、
日志、COMSOL/MATLAB 安装程序、许可文件或客户端用户配置。

用户已明确授权把此工具包上传到个人 GitHub 私有仓库；本次通过已登录的 GitHub
网页创建仓库并上传清单文件。后续更新沿用明确的目标和可见性，上传后核对远端文件
与提交结果。更改为公开仓库或增加协作者不属于本次上传范围。

## 许可证与依赖

本包没有捆绑第三方仓库源码，采用本地原型的整理实现和固定提交的外部引用。
目前未替作者选择或授予公开分发许可证。若以后公开，建议为原创部分选 MIT，
同时核对原创代码权属及引用情况；用户选择后再补 LICENSE。私有保存不要求现在选定。

上游 MPh 与若干社区项目使用 MIT，sim-cli/插件使用 Apache-2.0；实际分发它们的
源码或二进制时，要保留各自适用的许可证和声明。MathWorks MATLAB MCP 的许可证
是含 MathWorks 产品使用范围条件的自定义许可，不能统一改标 MIT。
GitHub API 的 `NOASSERTION` 或 null 不是许可结论，应读取仓库许可证原文。

依赖通过原始仓库链接和提交 SHA 追溯，详见来源清单。仓库只保存清单中的通用工具文件。
MPh 上游 1.4.0 与本机 1.3.1 分开记录；升级后重新执行与该接口相关的验证。
