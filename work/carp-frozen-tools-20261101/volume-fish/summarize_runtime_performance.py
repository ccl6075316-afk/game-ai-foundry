"""Summarize bound read-only Godot inventory and matched static/animated runs."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    args=parser.parse_args();game=args.game.resolve();review=args.review.resolve()
    if not review.is_relative_to(game.parent/'plans'/'reviews'):
        raise ValueError('Review must be in the target project plans/reviews directory')
    inventory=read(review/'inventory.validation.json')
    run_paths=[review/name/'benchmark.validation.json' for name in
               ('black-seabream','hairtail','bluefin-tuna')]
    runs=[read(path) for path in run_paths]
    failures=[];bindings={};current_hashes={}
    for report in [inventory,*runs]:
        if report.get('ok') is not True or report.get('self_test') is not True or report.get('input_changes'):
            failures.append('Failed or changed-input source report: '+report.get('mode','unknown'))
        for resource,digest in report['input_bindings'].items():
            if resource in bindings and bindings[resource]!=digest:
                failures.append('Cross-run input version differs: '+resource)
            bindings[resource]=digest
            path=game/resource[6:] if resource.startswith('res://') else Path(resource)
            if resource not in current_hashes:
                current_hashes[resource]=sha(path) if path.is_file() else None
            if current_hashes[resource]!=digest:
                failures.append('Current input differs: '+resource)
    labels=json.loads(re.search(r'const LABELS := (\{[^\r\n]+\})',
        (game/'scripts/aquarium/VolumeFishExhibit.gd').read_text(encoding='utf-8-sig')).group(1))
    rows=[];parts=[]
    for fish in inventory['inventory']:
        raw=fish['raw_import']['totals'];final=fish['final']['totals']
        rows.append({'species':fish['species'],'name':labels[fish['species']].split('·')[0],
            'raw_import_triangles':raw['triangles'],'final_visible_triangles':final['visible_triangles'],
            'final_surfaces':final['visible_surfaces'],'bones':final['bones'],
            'exact_zero_area_triangles':final['exact_zero_area_triangles'],
            'coincident_triangles':final['coincident_triangles_within_surface'],
            'unused_vertices':final['unused_vertices'],'hidden_triangles':final['hidden_triangles'],
            'texture_image_data_bytes':final['texture_image_data_bytes']})
        for mesh in fish['final']['meshes']:
            parts.append({'species':fish['species'],'name':labels[fish['species']].split('·')[0],
                'node':mesh['node'],'triangles':sum(s['triangles'] for s in mesh['surfaces']),
                'surfaces':len(mesh['surfaces']),'lod_surfaces':sum(s['has_imported_lods'] for s in mesh['surfaces']),
                'visible':mesh['visible']})
    cases=[]
    for run in runs:
        for entry in run['benchmarks']:
            cases.append({'label':entry['label'],'count':entry['fish_count'],'animated':entry['animated'],
                'frame_ms_p50':entry['frame_ms']['p50'],'frame_ms_p95':entry['frame_ms']['p95'],
                'motion_step_ms_p50':entry['motion_step_ms']['p50'],
                'draw_calls_p50':entry['draw_calls']['p50'],
                'primitives_p50':entry['rendered_primitives']['p50']})
    for log in review.rglob('*.log'):
        if re.search(r'(^|\n)\s*(SCRIPT ERROR:|ERROR:)',log.read_text(encoding='utf8',errors='replace')):
            failures.append('Engine error in '+str(log))
    totals={key:sum(f['final']['totals'][key] for f in inventory['inventory']) for key in
        ('triangles','visible_triangles','exact_zero_area_triangles','near_zero_area_triangles',
         'coincident_triangles_within_surface','unused_vertices','hidden_triangles','visible_surfaces')}
    totals['exact_zero_area_percent']=100*totals['exact_zero_area_triangles']/totals['triangles']
    totals['coincident_percent']=100*totals['coincident_triangles_within_surface']/totals['triangles']
    with (review/'species.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    limitations=[
        'Read-only audit, no changes to fish geometry, materials, motion controllers, source art or acceptance.',
        'Counts use actual imported meshes and the final active appearance assembly, not only the raw GLB.',
        'Exact degenerate and coincident counts do not classify all unseen/interior faces; no pose-wide safe-deletion analysis was performed.',
        'Coincident triangles can intentionally carry two-sided/layered material semantics; do not delete from these counts alone.',
        'Texture image bytes are per-fish sums of unique texture objects, not measured VRAM or 50 independent texture copies.',
        'Benchmarks are 1280x720 Compatibility/OpenGL, RTX 5080, VSync off, 60 warmup and 180 measured frames per phase; no tank/water/shadows/AI/collisions.',
        'Actual motion controllers use a fixed 1/60 simulation step; placement is held in an all-visible grid. This is not a normal gameplay FPS guarantee.',
        'An existing separate whale-shark preview process (PID 40324) remained open. Other GPU workloads were not forcibly stopped.',
        'Static and animated cases differ in controller evaluation, bone updates and skinned rendering; their difference is not a pure polygon-cost measurement.',
        'Renderer GPU interval fields are retained raw and may include driver/queue idle; do not attribute the full interval to shader arithmetic.',
        'No safe reduction ratio or final LOD quality has been verified; optimization must preserve user-preferred shape/pixels and pass applicable gates.'
    ]
    text=['# 鱼模型性能审计：当前实际安装版本','',
        '本次为只读审计；没有修改现有鱼，也没有重新批准任何外观。', '',
        '当前组合适合近景验收和功能展示，但尚未形成面向大量鱼的性能成品。已实测的主要压力包含高密度静态部件、绘制批次，以及逐鱼逐骨骼动作计算。少量退化面不是主要解释。','',
        '## 唇带为什么独立','',
        '现有方法用浅凸带承载原画完整唇色色块与单独UV，保留闭合身体及口内结构，便于独立验证和修正。它不是生物结构必须拆成两个运行资源。完整模型可以在制作阶段一次导出；是否焊接拓扑、是否合并材质，须分别判断。合进一个GLB不会自动减少三角面或绘制批次。不能为了省一个节点取消真实口裂、浅凸和原画接续。','',
        '## 逐鱼实际统计','',
        '| 鱼种 | 原导入三角面 | 最终可见基础三角面 | 可见surface | 骨骼 | 精确退化面 | 重合候选 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        text.append('| {name} | {raw_import_triangles:,} | {final_visible_triangles:,} | {final_surfaces} | {bones} | {exact_zero_area_triangles} | {coincident_triangles} |'.format(**row))
    text.extend(['','28种最终组合共计 {:,} 基础三角面；精确零面积 {:,}（{:.3f}%），同surface几何重合候选 {:,}（{:.3f}%），未引用顶点 {}。'.format(
        totals['triangles'],totals['exact_zero_area_triangles'],totals['exact_zero_area_percent'],
        totals['coincident_triangles_within_surface'],totals['coincident_percent'],totals['unused_vertices']),
        '这些是全部部件统计，包含少量隐藏部件；不等于每帧实际提交/光栅化数量，也不证明拓扑/身体/鳍完整性通过。','',
        '## 显著的部件密度','', '| 鱼种 | 部件 | 三角面 | 带LOD的surface数 |','|---|---|---:|---:|'])
    for part in sorted((p for p in parts if p['visible']),key=lambda p:p['triangles'],reverse=True)[:15]:
        text.append(f"| {part['name']} | {part['node'].split('/')[-1]} | {part['triangles']:,} | {part['lod_surfaces']} |")
    text.extend(['','## 50条同种鱼：静止与实际游动控制对照','',
        '以下为中位数。60 FPS整帧预算约16.7ms。绘制批次为测试帧实测，包含全部可见surface；三角面统计与实际帧primitive计数分别保留。','',
        '| 测试 | 静止整帧ms | 游动整帧ms | 游动脚本ms | 游动帧P95 ms | 绘制批次 |','|---|---:|---:|---:|---:|---:|'])
    for run in runs:
        pair=[r for r in run['benchmarks'] if r['fish_count']==50]
        static=next(r for r in pair if not r['animated']);moving=next(r for r in pair if r['animated'])
        label=labels[moving['label'].rsplit('_',1)[0]].split('·')[0]
        text.append(f"| 50条{label} | {static['frame_ms']['p50']:.2f} | {moving['frame_ms']['p50']:.2f} | {moving['motion_step_ms']['p50']:.2f} | {moving['frame_ms']['p95']:.2f} | {moving['draw_calls']['p50']:.0f} |")
    text.extend(['','## 优先处理顺序','',
        '1. 先拆清进场加工与持续运行：固化完整成品可减少加载，但不会自动降低现有面数、surface和每帧动作开销。',
        '2. 根据实际画面尺寸建立完整鱼的近/中/远层级，优先评估高密度唇带、眼片、身体和密集鳍片；保留近景可切换的精细版本。现存部分鳍有LOD，不代表整鱼及附层有完整LOD。',
        '3. 优化逐骨骼路径求导/系数计算及临时字典与检查记录，制定远处低频更新、共享或批量动画方案。带鱼证明低面数也会被CPU动作计算限制。',
        '4. 合理合并材质/surface与固定部件，减少重复提交；需保持原生像素清晰度、透明/不透明归属和运动连接。蓝鳍测试50条达到1500绘制批次。',
        '5. 单独整理贴图/查找表资源与发布依赖；本轮未做内容级纹理去重、显存采样或原画降采样。',
        '6. 清理已确认退化面时局部验证；同位置三角面、隐藏部件和闭合体内部不能只凭统计直接删除。','',
        '## 范围与重放','',*['- '+line for line in limitations], '',
        '审计入口：`resources/scripts/volume-fish/audit_runtime_performance.gd`；使用Godot `--path <game> --rendering-method gl_compatibility --windowed --resolution 1280x720 --log-file <review/log> --script <该脚本绝对路径> -- --output=<绝对review目录> --mode=inventory`。',
        '性能对照使用 `--mode=benchmark --species=black_seabream|hairtail|pacific_bluefin_tuna --samples=180`，每种输出到不同子目录。汇总使用同目录 `summarize_runtime_performance.py --game <game> --review <review>`。',
        '', '本轮没有稠密采样、临时模型或导入副本；仅保留四份原始报告、必要日志、三张不同鱼种的50条布局证据及本汇总。'])
    (review/'performance-review.md').write_text('\n'.join(text)+'\n',encoding='utf8')
    artifacts={str(path.relative_to(review)):sha(path) for path in review.rglob('*') if path.is_file() and path.name!='validation-report.json'}
    tool=Path(__file__).with_name('audit_runtime_performance.gd')
    report={'schema_version':1,'command':'fish.performance-audit-summary','ok':not failures,
        'status':'done' if not failures else 'blocked','next_action':'human_review',
        'species_count':len(rows),'totals':totals,'species':rows,'parts':parts,'benchmarks':cases,
        'input_bindings_count':len(bindings),'all_input_versions_consistent':not failures,
        'checker_sha256':sha(tool),'summary_tool_sha256':sha(Path(__file__)),
        'artifacts':artifacts,'limits':limitations,'visual_check':'Operator inspected all three 50-fish grid captures; confirms visible population/layout only, not new fish visual acceptance.',
        'cleanup':{'temporary_models_created':0,'dense_arrays_or_frames_written':0,'deleted_files':0,
            'retained':'Only compact metrics/logs, three distinct captures and summary; no unrelated files removed.'},
        'failures':list(dict.fromkeys(failures))}
    (review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'ok':report['ok'],'species':len(rows),'input_bindings':len(bindings),
        'review':str(review/'performance-review.md'),'failures':report['failures']},ensure_ascii=False))
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
