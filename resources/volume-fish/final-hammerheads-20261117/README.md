# 路氏双髻鲨与无沟双髻鲨

[发布清单](release.json)记录正式源、GLB、正式入口、SOP、游戏提交和百度云 LFS 回读。路氏尾鳍修前修后及两条正式四动作对比在游戏同名交接目录。

在 Foundry 根目录生成绑定已安装成品的回放清单，再启动一次 Godot。

```sh
python3 resources/volume-fish/final-hammerheads-20261117/replay/build_catalog.py \
  --game projects/fishing-2d/game --output work/final-hammerhead-replay
godot --path projects/fishing-2d/game \
  --script "$PWD/resources/volume-fish/final-hammerheads-20261117/replay/joint_feeding_viewer.gd" \
  -- --catalog="$PWD/work/final-hammerhead-replay/catalog.json" --background-preview
```

左侧可切换两条、两种猎物、整鱼或口部近景。播放时可切正面、侧面、俯视和腹视，也可拖动镜头。

尾鳍修复先用原色图和同光照画面分开判断取色和法线问题。路氏在现版尾柄实采两侧和背腹色，尾鳍两张图共局部修 25,027 个 RGB 纹素。尾柄与尾鳍共有外环按双方可见表面求法线，保留内部闭合面的原角色。检查时围绕接缝采样两侧的亮度跳变，同时逐三角角点核对位置、UV、骨指数、权重及全部不透明度。路氏与无沟的口环和捕食节奏逐鱼定义，复用前须按本鱼唇缘重新绑定。
