# 独立打包验证记录

当前仓库已于 2026-09-21 按用户要求移除 `SHA256SUMS`，日常开发不再维护该清单。以下校验记录仅描述历史打包快照。

日期：2026-09-21。源：modeling 内 operator-performance-lab 原型；来源仓库 HEAD 为 b1e5bdca，但原型当时是未提交文件，本包是工作区快照，不能通过该 commit 还原原型。

## 交付内容

- modeling 同级的 operator-performance-lab 完整源码目录与 operator-performance-lab.zip。
- 根目录 README.md、AGENTS.md、ARCHITECTURE.md；.agent/ 下主记忆与两个专题；docs/ 下历史、提取设计/计划和本记录。
- SHA256SUMS 覆盖包内其余文件；目录和 ZIP 内容一致。不含 .git、缓存、依赖目录或无关仓库数据。

## 验证结果

- Python 3.9.6 构建成功，生成 index.html 为 221030 bytes。
- 八项单元测试通过；Node v26.8.2 的 JS 语法检查通过。
- 八个实现/测试文件与来源逐字节一致，重新构建页面没有改变任何 UI 或交互。
- ZIP 解压至新的临时目录后重跑构建、八项测试、JS 语法检查；校验清单全部匹配。
- 解压目录启动仅回环地址的临时 HTTP 服务，首页返回 200，内容与生成页面一致。
- 文档内部链接检查通过，文档没有依赖个人绝对路径。

本次为原样提取，没有新增 UI 行为，不重复全套浏览器交互验收；原版 PC 验证范围与下载/手机布局限制见 HISTORY.md。未进行真机、模拟器或业务后端测试。

## OpScope 命名与解压（2026-09-21）

从原 ZIP 提取并验证原始校验值后，独立目录命名为 opscope。页面标题与品牌、README、AGENTS 和记忆已同步 OpScope。重新生成 index.html 并更新 SHA256SUMS；原 ZIP 仍是命名前快照，因此本目录与原 ZIP 不再逐字节一致。八项测试、JS 语法和新校验值检查通过；原始打包记录中的文件大小与原样一致结论仅适用于上次快照。
