"""Package existing vector artwork and audit the actual submitted PDFs."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
import fitz

BASE = Path(__file__).resolve().parents[1] / 'figure_research'
SOURCE = BASE / 'complete_set'
DEST = BASE / 'submission_vectors'
STEMS = ['fig1_study_design', 'fig2_main_results', 'fig3_mechanism',
         'fig4_temporal_dissociation', 'fig5_scope_and_boundary',
         'fig7_modern_decoders', 'supp_t_sensitivity']


def main():
    report = []
    for stem in STEMS:
        for ext, folder in [('pdf', 'PDF'), ('svg', 'SVG')]:
            target = DEST / folder / f'{stem}.{ext}'
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / f'{stem}.{ext}', target)
        pdf = DEST / 'PDF' / f'{stem}.pdf'
        with fitz.open(pdf) as doc:
            assert len(doc) == 1, stem
            page = doc[0]
            assert abs(page.rect.width / 72 - 7.16) < .02, stem
            assert not page.get_images(full=True), f'Raster image in {stem}'
            assert len(page.get_text().strip()) > 100, stem
            fonts = []
            for font in page.get_fonts(full=True):
                embedded = bool(doc.extract_font(font[0])[3])
                assert embedded, f'Unembedded font in {stem}: {font[3]}'
                assert 'TimesNewRoman' in font[3].replace(' ', ''), f'Non-Times font in {stem}: {font[3]}'
                fonts.append({'name': font[3], 'embedded': embedded})
            report.append({'file': pdf.name, 'width_mm': round(page.rect.width/72*25.4, 2),
                           'height_mm': round(page.rect.height/72*25.4, 2),
                           'raster_images': 0, 'fonts': fonts,
                           'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()})
        root = ET.parse(DEST / 'SVG' / f'{stem}.svg').getroot()
        assert not any(e.tag.rsplit('}', 1)[-1] == 'image' for e in root.iter()), stem
    (DEST / 'vector_validation.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copyfile(SOURCE / '图集说明与替换图注.md', DEST / '图注与数据说明.md')
    (DEST / '使用说明.txt').write_text(
        '投稿矢量图文件包\n\n'
        'PDF/：6张正文图和1张补充图，每图一个独立矢量PDF，优先用于LaTeX和接受PDF图件的投稿系统。\n'
        'SVG/：对应的可编辑矢量副本，供修改和明确支持SVG的投稿系统使用。SVG字体显示依赖本机字体。\n'
        '图2已使用最新柱状分布版本；正文图号为1、2、3、4、5、7，沿用现有稿件，无图6。\n'
        '检查：所有PDF均单页、无嵌入位图、字体已嵌入；SVG无image位图节点。尺寸和校验值见vector_validation.json。\n'
        '7张图均按7.16英寸（181.86 mm）双栏宽度排版；当前复合图信息量较大，勿直接缩到3.5英寸单栏。\n'
        '当前英文稿将图3和图7用单栏命令引用；排版时需改为双栏figure*，或另做内容简化的单栏版本。\n'
        '图内正文文字使用Times New Roman；PDF嵌入字体，SVG文字保留为可编辑文本并依赖本机Times New Roman。\n'
        '图形颜色以RGB导出，矢量线条和文字无需按300/600 dpi重新采样，勿转成PNG后再封装为PDF。\n'
        '尚未指定目标期刊；本包不代表已通过某一期刊的专门格式审查。若系统要求EPS、TIFF、CMYK或指定尺寸，应按该刊规则另行导出。\n'
        '论文正文中的图文件和图注尚未替换。\n', encoding='utf-8')
    archive = BASE / '投稿矢量图_PDF_SVG.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(DEST.rglob('*')):
            if file.is_file():
                z.write(file, Path('submission_vectors') / file.relative_to(DEST))
    print(json.dumps({'archive': str(archive), 'figures': len(report),
                      'all_pdf_fonts_embedded': True, 'raster_images': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
