# 083 行为试演从Turn恢复Swim：请求被seek清除

Normal mode；真实Godot smoke，2026-10-19。隔离预览UI自动试验，生产controller/motion/model未改。

## Phase1 evidence

projects/fish-083-friendly-ten/game/smoke.gd先逐鱼通过体态/行为运行与16s结束/重播检查，继而切Turn、开启行为后，21行断言snapshot.action==Swim失败。/tmp/083-smoke.log保留引擎回溯。已有切Turn断言20行通过。

FoundryFishMotion.gd:285-297 的seek清空_pending_action/_pending_restart；wrapper初始化先set_action(Swim,true)后seek0，Swim请求被清掉，当前Turn保留。source capture/audit从configure默认Swim开始，未触发该从Turn返回的缺陷。

## Phase2 pattern / Phase3 hypothesis

controller的公开step304-316消费pending restart，会先_action=selected再seek0。拟wrapper初始化仅把set_action后的seek0换step0；控制器、材质、配置、几何及捕获输入不变。已有smoke是稳定负例；独立reviewer核对Phase1/2/3，尚未修订。

Phase1/2/3 independent reviewer APPROVED；只把wrapper初始化的seek0改为step0，消费restart后内部seek。未改任何标准检查绑定的controller/motion/profile/shader，重跑同一实际Godot smoke。

Phase4 independent APPROVED。原完整smoke逐条10鱼体态/切鱼、16s结束、重播、Turn关闭行为、重新开启回Swim均true；日志无ERROR。canonical wrapper和隔离preview逐字一致，所有几何门绑定controller/motion/profile未改。报告 projects/fishing-2d/plans/reviews/083-friendly/083-ui-review.validation.json。终态SUCCESS，仅UI行为请求消费修复，不升级黑鲷几何失败。
