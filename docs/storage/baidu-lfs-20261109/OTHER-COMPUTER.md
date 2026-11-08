# 另一台电脑：Git取代码，百度网盘取当前资产

以下以Mac终端为例，在`game-ai-foundry`仓库根目录执行。需要Git、Git LFS、Python3.12+。两个仓库都应没有未提交的已跟踪文件修改；有修改先保留并处理，不用reset覆盖。此流程接收本次已发布快照，尚未改变后续push的存储后端。

## 1. 先跳过GitHub LFS，再拉代码

```bash
export GIT_LFS_SKIP_SMUDGE=1
git lfs install --local --skip-smudge --skip-repo
git -C projects/fishing-2d lfs install --local --skip-smudge --skip-repo
git pull --ff-only
git -C projects/fishing-2d pull --ff-only
```

前两条install只改各自仓库的本机LFS过滤器配置，保留已有hooks；`--skip-smudge`阻止clone/pull/checkout自动下载大文件。环境变量覆盖本次终端的命令，local配置负责后续终端；两个独立仓库都要配置。不要另跑`git lfs pull`，它会主动使用原LFS远端。

以上假设Foundry已跟踪`origin/codex/pure-workflow-toolkit`、游戏已跟踪`origin/main`。若另一台电脑用别的分支，先让Agent核对并将这次工具提交正常合入当前分支，不强行覆盖。拉取后应能看到此文件及`baidu_lfs_snapshot.py`的install子命令。

全新克隆时，必须在clone之前设环境变量：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --branch codex/pure-workflow-toolkit git@github.com:ccl6075316-afk/game-ai-foundry.git
cd game-ai-foundry
GIT_LFS_SKIP_SMUDGE=1 git clone git@github.com:ccl6075316-afk/fishing-2d.git projects/fishing-2d
git lfs install --local --skip-smudge --skip-repo
git -C projects/fishing-2d lfs install --local --skip-smudge --skip-repo
```

## 2. 本机安装、本人登录百度官方工具

另一台电脑的登录不会随Git同步。已有bdpan 3.8.9及有效登录可跳过安装/登录。

```bash
git clone https://github.com/baidu-netdisk/bdpan-storage.git work/bdpan-tools
bash work/bdpan-tools/skills/baidu-drive/scripts/install.sh
bash work/bdpan-tools/skills/baidu-drive/scripts/login.sh --continue-task
```

工具目录已存在时核对版本后复用，不重复clone。由本人确认安全须知、在百度官方页面授权并把码输入本机窗口；不把授权码或配置Token发到聊天、复制到另一台电脑或提交Git。安装后若当前终端找不到bdpan，按安装器提示刷新PATH或重开终端。

## 3. 从网盘恢复并回填

```bash
python3 resources/scripts/storage/baidu_lfs_snapshot.py restore --destination restored-lfs-20261109
python3 resources/scripts/storage/baidu_lfs_snapshot.py install --destination restored-lfs-20261109
python3 resources/scripts/storage/baidu_lfs_snapshot.py install --destination restored-lfs-20261109 --apply
```

restore下载55包并按清单重组到独立目录；install默认只预演，--apply才回填当前两个项目。全量预检要求：恢复证明和发布清单SHA一致；两个checkout的全部当前LFS路径/OID/尺寸与快照一致；无未提交的已跟踪修改；恢复源SHA正确；目标已经是正确资产，或是同一OID/尺寸的标准LFS指针。正确资产直接跳过，非匹配内容拒绝覆盖。任一路径冲突会在首次写入前停止；写入前还会复核目标，避免预检后被改动。

如果checkout新增/修改过LFS文件而快照未更新，install会拒绝，不能用旧快照覆盖新模型。restore目的目录已存在也拒绝覆盖；若该目录已成功完成，直接使用install；失败则让Agent核对现存报告/文件，不盲目删除或重复下载。下载包可复用，坏包保留待查。

写入后每个安装资产再次验SHA，报告在`work/restored-lfs-20261109/install.validation.json`。再检查两个仓库`git status --short`。本机现有Git LFS clean filter可能重建本地LFS缓存，这不等于从GitHub下载；本流程尚未去掉LFS索引/clean/pre-push机制。

## 边界与收尾

这是本次完整快照的接收流程，不是已经完成自动增量同步；未来修改资产后，不能假定普通git push会自动上传百度网盘。第二台物理电脑还未实测。当前Windows已通过全量云端往返和重组；新增回填用隔离测试覆盖指针替换、重复执行、损坏/路径越界、全量预检阻断后方冲突。

恢复完成后可由该电脑Agent根据install报告核对实际源、恢复副本与下载包，再按其平台的审核清单清暂存。Windows专用PowerShell清理入口不能直接当Mac通用删除命令使用。不要在回填验证之前删除唯一恢复副本。
