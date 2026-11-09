**最终结果：2026-11-10 真实GitHub推送成功；从远端浅克隆的普通git pull自动下载28/28对象，工作文件和LFS对象SHA/大小全部相同。测试机使用本机已有百度授权；第二台电脑仍须一次登录并运行配置脚本。**

# 成品资产的百度网盘 LFS 实测

本轮使用实际接受的鲫鱼、鲤鱼、草鱼源模型、GLB、必要供体及一张代表图，共28个对象、58,658,242字节。正常 Git push 走已配置的 baidu standalone transfer agent，GitHub 仍托管代码和LFS指针。

第一次推送有27/28对象完成上传及回读校验，草鱼 body-color 的46号分片目录创建返回百度 errno=20013，git push 返回1。随后 ls-remote 核对远端 main 仍为 fa3a70683d728bef563b5789377d0c18fe236313，未推进到新提交；没有跳过 hook 或改用 GitHub LFS。读取该分片目录显示不存在，第二次正常推送中28/28云端回读通过，但 GitHub 返回 GH008，远端仍未更新。按 GitHub 维护者对外部LFS的说明，两仓库补充受版本控制的 .lfsconfig；第三次正常推送成功，远端main核对为4bb8aea7eb385b68e8e528769eacffbda0e8e56d。最终结果以 download.validation.json 和 push.validation.json 为准。

下载验证使用本机隔离的稀疏Git检出：从真实GitHub进行depth=3、blob:none的浅克隆，LFS独立存储在新建空目录，并明确检查 LocalReferenceDirs 为空。检出停在旧提交，关闭跳过smudge后执行普通 git pull --ff-only origin main，再核对28个工作文件和28个LFS对象的大小、SHA及最终提交。这个测试不借用主仓库LFS对象，也不是手动脚本单独下载文件。最初共享Git对象的检出被发现会借用主仓库LFS缓存，不能作为云端下载证据，已弃用该次测试结论。当前远端克隆测试验证自动下载链路，不代替第二台物理电脑的首次登录和本地配置。

本轮鱼材质专项检查及清理详见游戏 plans/reviews/clean-pixel-three-20261110/HANDOFF.md。删除原材质实验1,888个文件、1,062,431,802字节，不删除云端旧对象。完整形态生产SOP未重跑，不能将本存储验收当成形态验收。

根因参考：https://github.com/git-lfs/git-lfs/issues/3231 。标准Git LFS配置文档：https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-config.adoc 。仓库声明使用保留的 https://baidu-lfs.invalid/foundry-lfs-objects-v1 作为外部代理命名空间标识；它不是可访问的HTTP服务，未安装代理应失败，避免误回退到GitHub。

最终下载耗时 92.38 秒；实测28个对象共58,658,242字节。标准Git LFS指针保留，代码与指针在GitHub，新二进制在百度网盘。第一次百度建目录错误靠正常重推恢复，GitHub GH008靠受版本控制的外部存储声明修复，均有实际失败与成功收据。
