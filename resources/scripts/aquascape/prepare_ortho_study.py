"""Prepare explicit technical-view prompts, avoiding scenery/character templates."""
import argparse
import json
from pathlib import Path
import shutil


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    for kind in ['rock','wood']:
        project=a.root/f'projects/aquascape-{kind}-orthos-v3'
        name=f'{kind}_three_views'
        plan_path=project/f'plans/{name}.json'
        data=json.loads(plan_path.read_text(encoding='utf-8'))
        if kind=='rock':
            shape='A single connected long terraced rock, with higher shoulder on the left, a lower middle, a scooped notch at right and a diagonal crack across the right half. A roughly 38 cm long, 16 cm high and 20 cm deep irregular solid.'
            top='TOP shows only the winding outer footprint and terrace contours, like contours on an overhead MAP. No vertical facade is visible. The left shoulder is a closed patch seen from above, the right scoop is an inward contour. Imagine a CAD top viewport.'
            side='RIGHT is a compact irregular END profile about 20 cm wide and 16 cm tall. The long 38 cm facade cannot be seen from this direction. Show the rightmost scooped cross-section with the high left shoulder behind it.'
        else:
            shape='One connected forked root, about 55 cm long, 30 cm high and 22 cm deep: bulbous knotted crotch on left, long S-shaped horizontal trunk to the right, one short vertical upward fork, left broken root, and two downward roots whose feet spread in depth.'
            top='TOP is an overhead MAP of the horizontal S-shaped trunk and root FOOTPRINT. The vertical upward fork is seen END-ON as an oval stub/socket, not as a branch sticking up the page. The two downward roots foreshorten and their separate footprints are visible. The vertical height must disappear in this top view.'
            side='RIGHT is the actual narrow END PROFILE of the root. The 55 cm long trunk axis points STRAIGHT at the viewer so the long trunk is hidden behind its end face: an irregular broken OVAL cross-section is central, short vertical fork above it, crotch and root feet behind/below. Its width is about 22 cm, height 30 cm. There must not be a long horizontal stick in this panel.'
        prompt=f'''Create a BLACK PENCIL / GRAY CLAY ORTHOGRAPHIC ENGINEERING STUDY, NOT a colored illustration. Identify the exact connected object in the reference artwork and infer its physical 3D structure.
{shape}
One white sheet, exactly 3 panels in a horizontal row: FRONT at left, RIGHT in middle, TOP at right. Use small plain labels above. Same world scale throughout. Simplified gray mass and thin black silhouette/structure lines ONLY, no wood grain, no mineral texture, no painted lighting, no isometric sketch.
FRONT: strict orthographic ELEVATION. Camera exactly horizontal at mid-height. X is horizontal and Y is vertical. Horizontal upper surfaces become edges with NO visible area from camera tilt. No perspective.
{side}
{top}
The reference is an angled beauty illustration. Discard its camera completely. Output three actual CAD-style viewports of one coherent object. Align FRONT and TOP X extents; align FRONT and RIGHT height; RIGHT width equals TOP vertical depth. Show all silhouettes on white with margin. Spatial coherence is more important than rendering detail. No repeated broadside silhouettes. No scenery, no ground, no shadows, no colors, no extra views.'''
        old=project/f'output/{name}_raw.png'
        if old.exists():shutil.copy2(old,project/f'output/{name}_rejected-r1.png')
        data['plan']['prompt']=prompt
        data['plan']['negative_hints']=['No isometric or three-quarter camera in any panel.','No colored texture, no scenery, no shadows.','Do not copy the source camera into TOP or RIGHT.']
        data['plan']['prompt_source']='agent_manual_orthographic_repair'
        plan_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(plan_path)


if __name__=='__main__':main()
