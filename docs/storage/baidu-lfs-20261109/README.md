# 当前 LFS 内容的百度网盘快照

2026-11-09 新增[自动传输方案](AUTO-TRANSFER.md)：本机两个仓库已启用Git LFS百度独立传输。此处仍是首次全量快照及手动恢复记录；新OID增量上传在自动传输目录。

用户于2026-11-09授权上传两个仓库当前使用LFS的全部内容。只保存当前文件，不补传旧提交中的历史版本。本轮不改Git filters、不重写历史、不删除GitHub LFS或本地LFS缓存。

**已完成并发布**：55/55包上传、下载与包SHA校验通过；从下载包流式重组4,816对象，全部原始LFS SHA通过，覆盖5,266路径。恢复清单上传后再次下载验SHA通过。唯一下载接口失败项0027已核对远端并单独补验成功，无重复上传；旧错误仍保留。快照暂存111文件、14,383,783,129字节已按专用入口删除，全部5,266当前源为保护项；不把释放本轮新增暂存称作项目永久减小14GB。

清单SHA-256：`9f0c70f93575736dea39d3a89687b25462898593a02e82f48901bfb6114883af`。网盘实际快照包7,189,811,200字节，加清单4,160,729字节；相对原始唯一内容仅增加必要的tar和索引开销。

`manifest.json`是路径、LFS SHA-256、原始字节数、分包位置的完整映射：Foundry 1,487路径，fishing-2d 3,779路径，跨仓库去重后4,816对象，共7,185,747,760字节。当前工作区每个路径都与LFS指针SHA实际比对过；不是只读Git清单。

云端目录为百度网盘“我的应用数据/bdpan/foundry-lfs-20261109-218c50d7”。小文件合并为55个不压缩USTAR包，包载荷不超过128MiB；大文件按最多32MiB分块，按清单可恢复原文件。包名为包SHA-256，内部成员名为原文件OID/偏移量；所有原始LFS OID保持不变。分包降低大量小文件的接口开销，不把分包当新历史保留策略。

运行入口 `resources/scripts/storage/baidu_lfs_snapshot.py`（Python3.12+；本机3.14）。使用官方bdpan 3.8.9；凭据只留在官方用户配置，不进入脚本、报告、Git或网盘快照。脚本不读取凭据配置，也不发送聊天原文遥测。

## 状态与验证

- `manifest.json`：冻结的当前源及包映射。
- `receipts/*.json`：逐包上传/下载耗时、哈希和完成标志；不保存原始CLI响应。
- `transfer.validation.json`：全包传输是否通过。
- `validation.json`：从所有下载包流式重组原文件，全部原始SHA匹配；当前工作区源再次核对。
- `publication.json`：最后发布的清单及其下载SHA复核结果。仅该文件ok=true且引用当前清单时可称快照发布完成。
- `cleanup-preflight.json` / `cleanup-execution.json`：本地暂存清理事实。未生成执行报告就不能说已删除。

阶段顺序：`prepare → transfer --workers 4 → verify → publish`。首次prepare已完成，不要重复生成；transfer允许按逐包回执恢复，失败包先检查错误和远端精确名称，避免默认自动重命名制造重复。遇到已存在但哈希不符的下载副本直接报错，不覆盖。

CLI可能进程exit=0但JSON `code`非零，必须同时检查；本轮包0027曾在上传完成后下载查询返回`errno=20013`，原始错误保留在逐包receipt。未知原因不归为内容损坏或权限变化，核对远端后只补验失败包。成功重试仍保留`previous_attempts`，不抹掉失败节点。清理已完成的快照不再重跑prepare/transfer；需要取回内容使用restore。

同机下载校验不是第二台物理电脑测试；未模拟断网恢复/限流。当前是可还原快照，尚未把开发工作流切换成自定义云端资产同步器，也未替代Git LFS的checkout/push机制。以后增量可按原OID复用已上传包中的内容；清单冲突必须在两台电脑相同基线下判断，不直接覆盖一方文件。

未来回收以当前清单和正在进行的工作引用为准；包内仍有被引用对象时不能整包删。如果要回收包内已不用的对象，需要重打仍在用的内容、验证并切换清单后，再清旧包。此工作尚未实现，不把本次快照脚本当成自动增量/回收系统。

## 在另一台电脑恢复到独立目录

完整步骤见[另一台电脑接收说明](OTHER-COMPUTER.md)，包含先禁用自动LFS下载、本人登录、恢复以及安全回填。`install`默认预演，显式`--apply`才替换当前checkout中完全匹配的LFS指针；本地修改或快照落后于当前LFS清单时拒绝执行。

先同步Foundry仓库，并在该电脑自行安装、登录官方bdpan；Mac须确认对应官方CLI可用，不能认为本次Windows测试证明Mac已配置。项目脚本可从PATH找到bdpan，Windows另支持默认安装位置。

```text
python resources/scripts/storage/baidu_lfs_snapshot.py restore --destination restored-lfs-20261109
```

该命令从已发布清单下载全部55包，验证包、成员及原文件SHA后，在全新的 `work/restored-lfs-20261109/foundry/` 与 `.../fishing-2d/` 恢复5,266个原路径。目的目录已经存在会拒绝覆盖。它不直接修改当前checkout，也不把文本LFS指针误当模型。恢复目录报告为`restore.validation.json`。网络和流式重组分别已由本轮全量往返验证；实体恢复路径写入用隔离小样本验证，第二台物理电脑仍需实测。

## 清理与知识同步

先预演 `resources/scripts/maintenance/clear_verified_baidu_staging.ps1 -Scope snapshot`，确认发布及源保护通过后再加`-Apply`。该入口只清本轮可重建暂存，保留云端当前包、正式源与LFS原配置。

登录试验的Windows换行问题已修复：Python文本stdin默认把LF扩成CRLF，Bash会把CR算入32位授权码。固定stdin newline=LF后，用户官方OAuth成功，三个合成文件往返通过。旧终端输入已停用；本机GUI授权码只经过内存/stdin，未写日志。67,117,056字节本地试验副本已按专用入口清理；云端三个合成样本仍保留，合计33,562,624字节。

清理方法补到项目skill的`references/command-rejection-recovery.md`；本机skill通过目录联接直接使用Foundry源。`codex-settings`只采集个人skill，跳过项目联接，避免复制出第二份生产规则。个人skill及配置同步另在该仓库记录。
