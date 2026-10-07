#!/usr/bin/env python3
"""Build the original SVG reference library and its selection catalog (stdlib only)."""
from pathlib import Path
import json
from reference_pages_a import build_pages as part_a
from reference_pages_b import build_pages as part_b

ROOT=Path(__file__).resolve().parents[1]

def build():
    entries=sorted(part_a()+part_b(),key=lambda item:item[1].number)
    numbers=[p.number for _,p,_ in entries]
    if len(numbers)!=len(set(numbers)) or numbers!=list(range(1,38)):
        raise ValueError('Expected exactly 37 distinct reference page numbers')
    page_dir=ROOT/'assets/reference-library/pages';page_dir.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for slug,page,meta in entries:
        if '/' in slug or '..' in slug or not slug.startswith(f'{page.number:02}-'):
            raise ValueError('Invalid reference slug')
        for key in ['family','purpose','read_order','adapt','avoid']:
            if not meta.get(key):raise ValueError('Missing reference metadata: '+slug+' '+key)
        svg=page.finish();(page_dir/(slug+'.svg')).write_text(svg,encoding='utf-8')
        manifest.append(dict(id=page.number,slug=slug,title=page.title or {1:'多孔材料的结构与传输',3:'建立结构与性能之间的可检验联系',28:'感谢聆听'}.get(page.number,'研究主题开场'),svg='assets/reference-library/pages/'+slug+'.svg',preview='assets/reference-library/previews/'+slug+'.png',layout='assets/reference-library/layouts/'+slug+'.json',pptx_slide=page.number,**meta))
    (ROOT/'assets/reference-library/catalog.json').write_text(json.dumps({'identity':'Original synthetic teaching examples; not scientific results.','pptx':'assets/reference-library/科研汇报布局参考.pptx','entries':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 完整科研页面参考库','',
      '这里提供37幅独立的、内容充实的科研页面示例。它们演示信息关系、证据层级、图文比例和具体排版；不是37页固定模板，也不是未来报告必须包含的页面。所有科学图形及数值均为原创合成，仅用于讲解布局，不代表研究结果。','',
      '主要参考为[可编辑PPT](../assets/reference-library/科研汇报布局参考.pptx)。[使用说明](template-use.md)介绍有视觉与无视觉Agent的读取方式；下方PNG预览来自实际PPT导出，SVG是原创图形源文件。','',
      '## 怎么选与怎么看','',
      '先按当前页面需要表达的关系选择2–4幅最相关的示例，查看相关PPT页面或其全尺寸导出图；无视觉能力时读取对应的布局JSON，再读该页的用途、顺序和变形建议。联系表只用于定位，不能据缩略图判断字号和图件质量。可以混合多个示例，也可以设计新构图；实际科学内容比示例中的列数、颜色和装饰优先。','',
      '![37页联系表](../assets/reference-library/contact-sheet.png)','',
      '| 编号 | 关系与任务 | 完整参考页 |','|---|---|---|']
    for e in manifest:lines.append(f"| {e['id']:02} | {e['family']} · {e['purpose']} | [{e['title']}](#参考-{e['id']:02}) |")
    lines.extend(['','## 阅读与迁移边界','',
      '- **看丰富度**：观察主图、辅助证据、方法信息与结论怎样组合；不要用同一图标反复替代具体科学图件。','- **看变形能力**：图需要放大时让出面积，细节不足时收束版面，不强凑同样模块数。标题、框线、状态、结论带和结束页均按需要取舍。','- **看真实素材**：用于实际任务时替换为授权原图、数据图或科学示意，并按图件与证据指南记录来源；合成图不进入真实结果叙事。','- **看整体而不照抄**：图册包含浅色克制风格的多种组织方式；用户指定的字体、配色、比例、页数与语言优先。','',
      '每页有独立布局JSON、PPT导出PNG及SVG源图。可编辑PPT是主参考，JSON用于精确读取元素，PNG用于查看实际导出效果。不同演示软件的字体替代仍需在目标环境检查。完整选择信息也保存在 `assets/reference-library/catalog.json`（从技能根目录解析）。',''])
    for e in manifest:
        lines.extend([f"## 参考 {e['id']:02}",'',f"**{e['title']}**",'',f"![{e['title']}](../{e['preview']})",'',f"[查看PPT第{e['id']}页](../assets/reference-library/科研汇报布局参考.pptx) · [布局JSON](../{e['layout']}) · [导出PNG](../{e['preview']}) · [SVG源图](../{e['svg']})",'',f"- **用途**：{e['purpose']}",f"- **阅读顺序**：{e['read_order']}",'- **可变化**：'+'；'.join(t.rstrip('。；') for t in e['adapt']),'- **注意**：'+'；'.join(t.rstrip('。；') for t in e['avoid']),''])
    (ROOT/'references/gallery.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    items=build();print('Built '+str(len(items))+' original SVG reference pages and catalog.')
