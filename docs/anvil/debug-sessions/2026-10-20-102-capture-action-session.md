# 102审计采集动作标签

模式：Normal。证据：实际GPU capture.validation.json与控制器源代码。

## Phase1 根因
22鱼352帧中264帧请求Turn/Ascend/Dive，实际snapshot.action为Swim。控制器已ready、profile有四动作。采集端set_action只排队，随后seek清pending，未调用step消费。保留invalid-motion-labels.before.json，失效收据已撤下。静帧初始Swim未受此次错误影响，但同样修正调用契约。

## Phase2 模式
export_runtime_fin_roots.gd:109–111及VolumeFishMotionQA.gd:104–108先set_action、step(0)，再seek。既有控制器契约不变，修采集调用端。

## Phase3 失败检查
逐样本requested==snapshot.action；修正前264/352不匹配。独立audit_capture_review审查Phase1/2/3全部APPROVED。

## Phase4
单点补step(0)，对动作设置与每帧实际动作加断言。将重新GPU采集全部22鱼，并验证哈希、日志和动作快照。未改游戏资产/控制器。

实际重采：22鱼352帧，动作不匹配0，全部截图/模型/运行时/脚本哈希吻合；三组GPU日志无错误。独立audit_capture_review Phase4 APPROVED。headless首次因user日志目录不可写失败，改显式/tmp日志后解析成功；GPU用已授权后台open -g -j且无焦点激活。
