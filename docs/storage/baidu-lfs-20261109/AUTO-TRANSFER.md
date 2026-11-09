# Git LFS 自动走百度网盘

2026-11-09 本机Windows已启用，隔离Git仓库实际验证普通`git push`上传新OID、普通`git pull`下载新OID、旧55包快照的OID按需取回，以及传输程序失败时阻止Git ref前进。`git-lfs`的独立传输接口由官方定义；本项目只实现连接百度官方`bdpan` CLI的小适配器，不部署LFS服务端。

入口：`resources/scripts/storage/baidu_lfs_agent.py`。新OID按原始SHA放在百度网盘`我的应用数据/bdpan/foundry-lfs-objects-v1/<OID前两位>/<OID>`；旧OID按已发布的`manifest.json`查到历史快照包，按需下载该包、取成员并验原始SHA。旧包只读，不为启用自动模式重传原7GB。新上传在返回Git LFS成功前还会从网盘下载一次并验SHA，失败则本次Git push失败。

## 当前电脑

`resources/scripts/storage/configure_baidu_lfs.py`默认预演，`--apply`配置Foundry和`projects/fishing-2d`两个独立Git仓库。它使用本机Python绝对路径，只改两仓库`.git/config`中LFS过滤器/独立传输设置；不改项目中的`.lfsconfig`，不保存凭据，也不覆盖pre-push hook。已在本机执行并核对两边`lfs.standalonetransferagent=baidu`。官方百度登录沿用已完成的本机授权。

```text
./.venv/Scripts/python.exe -B resources/scripts/storage/configure_baidu_lfs.py
./.venv/Scripts/python.exe -B resources/scripts/storage/configure_baidu_lfs.py --apply
```

之后日常按原来方式Git pull/push。Git只传代码和LFS指针，Git LFS通过独立传输代理把内容传到百度，不调用GitHub LFS API。GitHub仍托管Git代码；LFS指针继续由Git维护。若账号授权失效，需要本人重新运行百度官方登录流程。

## 第二台电脑首次设置

首次clone/pull工具代码时，仍需临时`GIT_LFS_SKIP_SMUDGE=1`跳过LFS下载，因为本机还没有适配器。同步Foundry当前工具提交与游戏仓库后，安装官方bdpan并本人登录，再以该机Python3.12+运行下列两步：

```text
python3 resources/scripts/storage/configure_baidu_lfs.py
python3 resources/scripts/storage/configure_baidu_lfs.py --apply
```

启用后新变化的LFS文件随普通Git pull自动下载。首次clone时已经留下的旧指针，可在两个仓库各执行一次`git lfs pull`，此时它会通过百度适配器，而非GitHub；当前快照一共7GB，旧包按需下载并缓存在`work/baidu-lfs-agent/packs/`。已有的手动`restore/install`仍可作为首次整体恢复的备选路线，实际不会主动替换适配器配置。后一台Mac尚未实体测试，需在那台电脑核对官方bdpan安装/登录及Git操作。

用户曾在另一台电脑设置`--skip-smudge`以免从GitHub下载。正式启用时配置脚本使用`git lfs install --local --force --skip-repo`把过滤器恢复到自动模式，再配置百度独立传输；本机默认Git LFS pre-push hook保留。配置前会拒绝已跟踪文件的未提交改动和非标准pre-push hook。新clone务必在配置前设置临时跳过LFS的环境变量，配置后正常运行。

## 验证与限制

本机实测：隔离本地裸Git仓库两个checkout，普通push产生新LFS指针并上传百度，普通pull取新内容后接收仓库干净；用已发布PDF的OID模拟旧包引用，普通pull按需从快照取回；把传输程序改为缺失文件后push失败，Git远端ref不前进。两次SHA记录见`agent-integration.validation.json`。本机正式仓库只完成本地配置与现有资产哈希核对，没有因测试而改任何鱼模型。第二台Mac尚未实测。

新对象目前逐OID单独存储，存储空间可用但很多小文件会增加请求数；当前所有旧对象保留在已验证的55包中。旧包缓存是可重建的运行时缓存，不能当正式资产；离线或部分下载时Git报错并可重试。当前测试覆盖小型新OID与11MB旧OID；未来新增大于已实测128MB的单文件、同时两机改同一模型、长期限流以及历史分支的缺失OID，仍需按实际改动验证。用户当前只需要当前版本，不以旧分支回退为保留全部历史的理由；不自动删除任何网盘正式包。

实验结束后隔离Git测试目录已自动清理；旧包运行时缓存按已发布包SHA经专用清理器预演、执行，删除1文件、132,659,200字节，见`agent-cache-cleanup-execution.json`。缓存是可重建的，首次大量拉取后可用`clear_verified_baidu_staging.ps1 -Scope agent`预演、`-Apply`清理；不会删正式源或云端包。Mac上不能直接用这个PowerShell入口，需按已校验的包SHA做平台对应清理。

禁用本机自动传输可删两仓库本地`.git/config`中的`lfs.standalonetransferagent`，但必须先确认新OID在另一处可获取。`git config --local --unset lfs.standalonetransferagent`仅切回默认LFS端点，并不会把已经上传到百度的新OID自动补到GitHub。不得把这个配置当作无损撤回。
