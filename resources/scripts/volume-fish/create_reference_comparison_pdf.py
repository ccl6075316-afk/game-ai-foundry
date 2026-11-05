"""Lossless-image PDF companion for the actual 24-fish model comparisons."""
import hashlib
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/fish-reference-compare-20261105'
PDF = ROOT / 'output/pdf/fish-model-reference-comparison-20261105.pdf'


def main():
    manifest = json.loads((OUT / 'comparison-manifest.json').read_text(encoding='utf8'))
    pairs = manifest['pairs']
    assert len(pairs) == 27 and len(manifest['entries']) == 24
    pdfmetrics.registerFont(TTFont('ReviewChinese', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
    PDF.parent.mkdir(exist_ok=True)
    width, height = landscape(A4)
    canvas = Canvas(str(PDF), pagesize=(width, height), pageCompression=1)
    canvas.setTitle('24鱼 - 当前模型与实际参考侧视、俯视对照')
    canvas.setAuthor('Game AI Foundry - local model review')
    total = 29

    def text(x, y, s, size=11, color='#243746'):
        canvas.setFillColor(colors.HexColor(color))
        canvas.setFont('ReviewChinese', size)
        canvas.drawString(x, y, s)

    def footer(number):
        text(28, 19, '2026-11-05  |  原文件未改形  |  仅供此次形体对照，不产生外观接受', 8, '#627482')
        text(width - 73, 19, f'{number} / {total}', 9, '#627482')

    def image_fit(path, x, y, w, h):
        image = ImageReader(str(path))
        iw, ih = image.getSize()
        scale = min(w / iw, h / ih)
        rw, rh = iw * scale, ih * scale
        canvas.drawImage(image, x + (w - rw) / 2, y + (h - rh) / 2,
                         width=rw, height=rh, mask='auto')

    canvas.bookmarkPage('contents')
    canvas.addOutlineEntry('24鱼对照目录', 'contents', level=0)
    text(28, height - 49, '24鱼 - 当前模型与实际参考', 25)
    text(29, height - 76, '侧视 / 俯视 / 完整轮廓叠加  |  13条成品 + 11条候选  |  27组三维对照', 13)
    text(29, height - 103, '本册为灰模合集。原纹理、逐鱼切换、原文件与来源记录见配套对照网页。', 11)
    text(29, height - 124, '蓝：我们独有的投影区域    橙：参考独有的投影区域    浅灰：共同区域', 11)
    text(29, height - 145, '完整网格长轴等长、等比缩放并居中；含全部鳍和原静息姿态，不是解剖测位配准。', 10, '#627482')
    page_map = {}
    for i, pair in enumerate(pairs):
        page_map.setdefault(pair['species'], []).append(i + 2)
    for column, category in enumerate(('accepted', 'candidate')):
        x = 29 + column * 408
        text(x, height - 181, '已接受成品（13条）' if category == 'accepted' else '本批候选（11条）', 15)
        rows = [e for e in manifest['entries'] if e['category'] == category]
        for i, row in enumerate(rows):
            y = height - 207 - i * 21
            pages = '、'.join(map(str, page_map[row['species']]))
            if row['species'] == 'red_seabream':
                pages += '；主参考29'
            text(x, y, row['label'], 11)
            text(x + 208, y, '第 ' + pages + ' 页', 10, '#526c7c')
            canvas.linkRect('', f'pair-{page_map[row["species"]][0] - 2}', (x, y - 3, x + 375, y + 14), relative=0, thickness=0)
    text(29, 89, '真鲷：第8页是后来比较的GiltheadBream；当时主参考只有斜视预览，原图单列第29页。', 10, '#875313')
    text(29, 67, '两模型的鳍姿、张口、画风和参考用途可能不同；本册展示差异，不宣称一致或自动判定合格。', 10, '#627482')
    footer(1)
    canvas.showPage()

    for i, pair in enumerate(pairs):
        row = next(e for e in manifest['entries'] if e['species'] == pair['species'])
        ref = next(r for r in row['references'] if r.get('pair_id') == pair['id'])
        page = i + 2
        canvas.bookmarkPage(f'pair-{i}')
        canvas.addOutlineEntry(row['label'] + ' / ' + ref['name'], f'pair-{i}', level=0)
        text(25, height - 29, row['label'] + ' - 灰模侧视 / 俯视对照', 15)
        image_fit(OUT / 'sheets' / (pair['id'] + '-grey.png'), 20, 55, width - 40, height - 102)
        text(27, 40, '同相机、同光照；原纹理另见网页。原Unity自定义shader未复刻，透明边缘保留原／已核材质alpha。', 8.5, '#627482')
        footer(page)
        canvas.showPage()

    row = next(e for e in manifest['entries'] if e['species'] == 'red_seabream')
    primary = row['references'][0]
    fallback = next(r for r in row['references'] if r.get('pair_id'))
    canvas.bookmarkPage('red-seabream-primary')
    canvas.addOutlineEntry('真鲷 - 当时主参考的四张历史斜视原图', 'red-seabream-primary', level=0)
    text(25, height - 29, '真鲷 - 当时主参考原图（无本地三维网格）', 18)
    text(25, height - 53, '历史原图为未标定斜视，不是正交侧／俯视；本页不做像素差或尺寸误差比较。', 10, '#875313')
    files = [(OUT / 'renders' / fallback['pair_id'] / 'ours-side-grey.png', '我们的当前模型 - 正交侧视'),
             (OUT / 'renders' / fallback['pair_id'] / 'ours-top-grey.png', '我们的当前模型 - 正交俯视')]
    names = ['主参考原图 - 近俯斜视', '主参考原图 - 侧上斜视', '主参考原图 - 前上斜视', '主参考原图 - 前下斜视']
    files += [(OUT / image['presentation_path'], label) for image, label in zip(primary['existing_side_top_images'], names)] if 'presentation_path' in primary['existing_side_top_images'][0] else [(OUT / 'historical-preview' / image['original_filename'], label) for image, label in zip(primary['existing_side_top_images'], names)]
    for i, (path, label) in enumerate(files):
        col, r = i % 3, i // 3
        x, y = 25 + col * 267, height - 286 - r * 215
        text(x, y + 192, label, 10)
        image_fit(path, x, y + 5, 256, 178)
    text(25, 49, '原模型：CC0 Red Seabream, Pagrus major。公开下载需要登录；本次保留历史原图，没有用近缘模型代替主参考。', 8.5, '#627482')
    canvas.linkURL(primary['source_model_url'], (25, 31, 450, 46), relative=0, thickness=0)
    text(25, 34, '原参考模型网页（点击可由你自行查看）', 9, '#126a91')
    footer(29)
    canvas.save()
    reader = PdfReader(str(PDF))
    assert len(reader.pages) == total
    digest = hashlib.sha256(PDF.read_bytes()).hexdigest()
    (OUT / 'pdf.validation.json').write_text(json.dumps({'ok': True, 'pdf': str(PDF), 'sha256': digest, 'pages': total, 'images_lossless_in_pdf': True, 'source_pair_sheets': 27, 'historical_preview_images': 4, 'visual_qa': 'pending rendered-page review'}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'ok': True, 'pdf': str(PDF), 'bytes': PDF.stat().st_size, 'pages': total}))


if __name__ == '__main__':
    main()
